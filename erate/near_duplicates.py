"""Deterministic, approximate candidate near-duplicate discovery; never merges filing IDs.

MinHash LSH creates candidates, exact shingle Jaccard validates them. No claim of
exhaustively finding all templates. Useful for human reviewing template campaigns.
"""
import argparse, hashlib, re
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from erate.engine import read_csv, read_combined, write_csv

MODULUS=(1<<61)-1

def shingles(text, size=5):
    words=re.findall(r"\b\w+(?:['’]\w+)?\b",text.casefold())
    if len(words)<size:return set(),len(words)
    # Use full content; this can be expensive on exceptionally long records.
    return {int.from_bytes(hashlib.blake2b(' '.join(words[i:i+size]).encode(),digest_size=8).digest(),'big')%MODULUS for i in range(len(words)-size+1)},len(words)

def signatures(values, n=32):
    if not values:return [MODULUS]*n
    return [min((((i*8675309+77)|1)*h + i*104729+7)%MODULUS for h in values) for i in range(n)]

def jaccard(a,b):return len(a & b)/len(a | b) if a or b else 0.

def find_candidates(texts:dict[str,str],threshold=.87):
    # Candidate recall not guaranteed. Six bands of 4 hashes plus remainder.
    sets={};sigs={};bucket=defaultdict(list);truncated=[]
    for sid,text in texts.items():
        ss,word_count=shingles(text)
        if word_count<30 or not ss:continue
        sets[sid]=ss
        sig=signatures(ss,n=32);sigs[sid]=sig
        for b in range(8):bucket[(b,tuple(sig[b*4:(b+1)*4]))].append(sid)
    pairs=set()
    for members in bucket.values():
        if len(members)<2:continue
        # All candidate pairs, but avoid unbounded pathological buckets; reviewed separately.
        if len(members)>2000:
            truncated.append(len(members));continue
        pairs.update(tuple(sorted(p)) for p in combinations(members,2))
    results=[]
    for a,b in sorted(pairs):
        s=jaccard(sets[a],sets[b])
        if s>=threshold:results.append({'submission_id_a':a,'submission_id_b':b,'shingle_jaccard':round(s,6),
                                         'method':'5_word_shingle_32_minhash_8x4_lsh',
                                         'interpretation':'near_duplicate_candidate_not_verified_campaign'})
    return results,{'analyzed_filings':len(sets),'candidate_pairs':len(pairs),'pairs_above_threshold':len(results),
                    'oversized_bucket_skips':len(truncated),'threshold':threshold,'non_exhaustive':True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--analysis',type=Path)
    p.add_argument('--threshold',type=float,default=.87)
    a=p.parse_args();folder=a.analysis or a.corpus/'analysis_observatory'
    rows,_=read_csv(folder/'filing_inventory.csv')
    texts={}
    for r in rows:
        if int(r['text_chars'])>=120 and not int(r['agency_record_candidate']):
            text,_,matches=read_combined(a.corpus,r['submission_id'])
            if matches==1:texts[r['submission_id']]=text
    matches,summary=find_candidates(texts,a.threshold)
    write_csv(folder/'near_duplicate_candidates.csv',matches,['submission_id_a','submission_id_b','shingle_jaccard','method','interpretation'])
    import json
    (folder/'near_duplicate_method_report.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

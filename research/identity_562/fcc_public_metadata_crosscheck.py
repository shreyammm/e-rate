#!/usr/bin/env python3
"""Optional read-only corroboration of selected FCC ECFS metadata.

Uses only the FCC's public REST API and demo credentials. Network/rate-limit
errors are recorded as unverified and NEVER converted into a role. No personal
names, contact addresses or phone numbers are exported.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from research.identity_562.analyze_individuals import OUTPUT

FILING_IDS=[
 "26110079125", # organization letterhead, KnowledgeWorks
 "26110080317", # organization URL, AASA
 "26110081012", # organization URL, Do No Harm
 "26110081375", # school-district URL
 "26110076731", # self-described SHLB board leader
 "26110073398", # institutional author as person filer
 "26110080616", # institutional author as person filer
 "26110014024", # E-rate commercial service provider
]
ORG_MARKER=re.compile(r"(?i)\b(?:school[s]?|school district|library|"
                      r"association|coalition|foundation|institute|"
                      r"corporation|network|company|inc|llc|nonprofit)\b")
def publicly_named_institutions(value):
    if not isinstance(value,list):return []
    output=[]
    for item in value:
        if not isinstance(item,dict):continue
        for field in ("name","organizationName","organization","filerName"):
            val=item.get(field)
            if isinstance(val,str) and ORG_MARKER.search(val):
                n=" ".join(val.split())
                if 6<len(n)<130 and not re.search(r"@|\d{3}[-.]\d{3}",n):
                    output.append(n)
                break
    return sorted(set(output))[:6]

def run():
    api=os.getenv("FCC_ECFS_API_KEY","DEMO_KEY")
    records=[]
    for fid in FILING_IDS:
        url="https://publicapi.fcc.gov/ecfs/filing/"+fid+"?api_key="+api
        row={"filing_id":fid,"source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
             "metadata_verified":False,"status":"not_fetched",
             "extra_org_metadata":[]}
        try:
            req=urllib.request.Request(url,headers={
               "Accept":"application/json",
               "User-Agent":"e-rate-research-metadata-verification/1.0"})
            with urllib.request.urlopen(req,timeout=10) as conn:
                data=json.load(conn)
                row["response_type"]=type(data).__name__
                row["response_top_level_keys"]=sorted(list(data))[:22] if isinstance(data,dict) else []
                doc=data
                if isinstance(data,dict):
                    for key in ("filing","record","data","result","results","records"):
                        candidate=data.get(key)
                        if isinstance(candidate,dict):
                            doc=candidate
                            break
                        if isinstance(candidate,list) and candidate and isinstance(candidate[0],dict):
                            doc=candidate[0]
                            break
                row["response_record_keys"]=sorted(list(doc))[:30] if isinstance(doc,dict) else []
                if not isinstance(doc,dict):
                    row["status"]="non_object_response"
                else:
                    returned=str(doc.get("submissionId") or doc.get("submission_id")
                                 or doc.get("submissionID") or doc.get("id") or "")
                    if returned!=fid:
                        row["status"]="id_not_matched"
                    else:
                        row["metadata_verified"]=True
                        row["status"]="official_fcc_metadata_confirmed"
                        row["extra_org_metadata"]=sorted(set().union(
                            publicly_named_institutions(doc.get("filers",[])),
                            publicly_named_institutions(doc.get("authors",[])),
                            publicly_named_institutions(doc.get("lawFirms",[]))))
        except urllib.error.HTTPError as exc:
            row["status"]="http_"+str(exc.code)
        except (urllib.error.URLError,TimeoutError) as exc:
            row["status"]="network_unavailable"
        except (ValueError,KeyError,TypeError) as exc:
            row["status"]="metadata_parse_failure"
        records.append(row)
        time.sleep(.4)
    result={
      "schema":"fcc-live-crosscheck-unpublished-v1",
      "cases_requested":len(FILING_IDS),
      "confirmed_live_metadata":sum(x["metadata_verified"] for x in records),
      "statuses":dict(Counter(x["status"] for x in records)),
      "records":records,
      "limitations":"DEMO_KEY may be rate limited or blocked; failure is not evidence of identity",
    }
    (OUTPUT/"fcc_public_metadata_crosscheck.json").write_text(
        json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":run()

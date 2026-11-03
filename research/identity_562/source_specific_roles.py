#!/usr/bin/env python3
"""Human-inspected source passages from the previously unresolved FCC comments.

Every finding must satisfy an original-text regex before being emitted. These
are *unpublished source-supported self-descriptions*, not outside employment
verification or claims to represent the organizations mentioned.
"""
from __future__ import annotations
import json,re
from collections import Counter
from research.identity_562.deep_investigation import load
from research.identity_562.analyze_individuals import OUTPUT

# filing ID => (capacity, required original-source pattern, meaning)
# Match the author's own statement; never guess from policy argument vocabulary.
ADJUDICATIONS={
 "26110014024":("erate_service_provider",r"\bi am an? e[- ]?rate service provider\b","explicit first-person service provider, not necessarily a consultant"),
 "26110038479":("library_staff",r"\bi have been employed at the\b.{5,100}","explicit first-person library employment"),
 "26110071854":("professional_genealogist",r"\bas a professional genealogist\b","research occupation; not academic-researcher status"),
 "26110071941":("individual_personal_capacity",r"\bi am a private citizen\b","explicit personal status; no assumption of job"),
 "26110071947":("retired_library_staff",r"\bas a retired kcls refe\s*re\s*nce librarian\b","explicit past library profession"),
 "26110072168":("retired_school_educator",r"\bi am a retired nyc public school teacher\b","explicit former profession"),
 "26110072186":("school_network_staff",r"\bas a supervisor of network\b.{0,100}\bwswhe boces\b","explicit school-network supervisory professional"),
 "26110072449":("community_resident",r"\bi\s+am\s+a\s+resident\s+of\s+the\b","explicit resident"),
 "26110073715":("library_staff",r"\bas a public library employee\b","explicit working library professional"),
 "26110073727":("teacher_educator",r"\bformer high school science teacher and current teacher educator\b","explicit former schoolteacher and current educator"),
 "26110074167":("parent_guardian",r"\bi was a struggling single mom\b","historical explicit maternal experience"),
 "26110074199":("older_adult",r"\bas a senior citizen\b","self-declared civic demographic, not occupation"),
 "26110075169":("former_library_staff",r"\bas a former employee of both county and city run\b.{0,95}\blibraries\b","explicit past library employment"),
 "26110076274":("library_staff",r"\bas a library page and reference substitute\b","explicit library staff job"),
 "26110076731":("broadband_coalition_board_leadership",r"\bi currently chair shlb\b","explicit current role with public broadband coalition"),
 "26110080535":("community_volunteer",r"\bvolunteer as a senior citizen\b","current volunteer status, not past teenage library employment"),
 "26110081346":("individual_personal_capacity",r"\bin my capacity as a private citizen\b","explicit distinction from employer"),
 "26110081382":("former_public_library_director",r"\bi served as a rural public library director\b","explicit four years in former library leadership"),
}
# Explicitly excluded contextual false positives:
# 26110073130 discusses "the unhoused" but does not claim to be unhoused.
# 26110072197 uses "telecommunications regulator" to refer to the FCC.
# 26110074167 is NOT a present-tense college student or unemployed.
# 26110071958 was previously unemployed; that doesn't establish current job.
# 26110073990 affiliation title was not readable enough to verify sector.

def run():
    remaining={x["filing_id"] for x in json.loads(
        (OUTPUT/"model_and_phrase_review.json").read_text())["records"]}
    originals={str(r["submission_id"]):r for r in load()
               if str(r["submission_id"]) in ADJUDICATIONS}
    assert set(ADJUDICATIONS)<=remaining
    assert set(ADJUDICATIONS)==set(originals)
    verified=[];problems=[]
    for fid,(role,pattern,reason) in ADJUDICATIONS.items():
        text=str(originals[fid].get("text") or "")
        m=re.search(pattern,text,re.I|re.S)
        if not m:
            problems.append((fid,role))
            continue
        verified.append({
            "filing_id":fid,
            "source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
            "capacity":role,
            "evidence_pattern":pattern,
            "evidence_location":m.start(),
            "evidence_kind":"author_first_person_original_filing",
            "evidence_note":reason,
            "review_state":"source_supported_machine_checked",
            "employer_or_representation_independently_verified":False,
            "published_to_website":False,
        })
    if problems:raise ValueError(f"Manual source checks failed: {problems}")
    summary={
        "schema":"unpublished-source-specific-v1",
        "previously_unclassified_checked":len(remaining),
        "newly_source_identified_filings":len(verified),
        "new_capacity_breakdown":dict(Counter(x["capacity"] for x in verified)),
        "remaining_unclassified_without_source_capacity":len(remaining)-len(verified),
        "publication_status":"research_branch_only",
        "records":verified}
    (OUTPUT/"source_specific_identity_recovery.json").write_text(
        json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="records"},indent=2))
    return summary
if __name__=="__main__":run()

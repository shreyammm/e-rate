#!/usr/bin/env python3
"""Consolidated, UNPUBLISHED source-anchored review of 562 named filer identifiers.

Produces complete CSV for all 567 filing records, explicitly separating:
(1) source-declared capacity, (2) potential organizational affiliation,
(3) argument focus, (4) model-only lead. Counts use both filings and normalized
distinct filer fields, and no personal names/emails/source text are published.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from research.identity_562.deep_investigation import load
from research.identity_562.analyze_individuals import OUTPUT

# Independent corroboration of an organization's general sector is NOT
# verification that the person filing represents it. URLs are official org
# websites previously inspected by an analyst.
ORG_REFERENCES={
 "knowledgeworks.org":{
     "org":"KnowledgeWorks",
     "sector":"education_policy_nonprofit",
     "official":"https://knowledgeworks.org/about/"},
 "aasa.org":{
     "org":"AASA, The School Superintendents Association",
     "sector":"school_leadership_professional_association",
     "official":"https://www.aasa.org/About-AASA/"},
 "donoharmmedicine.org":{
     "org":"Do No Harm",
     "sector":"nonprofit_advocacy_membership_organization",
     "official":"https://donoharmmedicine.org/about/"},
 "ww2.montgomeryschoolsmd.org":{
     "org":"Montgomery County Public Schools",
     "sector":"school_district",
     "official":"https://www.montgomeryschoolsmd.org/"},
}

COHORTS={
 "screen_time_parental_choice":{"screen_policy","screen_harms","parent_choice",
                               "device_management","screen_use_distinctions"},
 "school_learning_access":{"learning_outcomes","digital_literacy","adaptive_learning",
                           "accessibility"},
 "library_public_access":{"libraries_public_service"},
 "consultant_oversight":{"consultant_fees","consultant_definition",
                          "consultant_registration","consultant_reporting",
                          "consultant_percentage_fee_rules","consultant_value"},
 "network_procurement":{"internal_networks","fiber_construction",
                         "competitive_bidding","cybersecurity"},
 "program_continuity_and_eligibility":{"program_continuity","eligibility_rules",
                                       "broadband_affordability"},
 "content_filtering_privacy":{"filtering","student_privacy","school_discretion"},
}
def filer_key(name):
    s=re.sub(r"[^a-z0-9]+"," ",str(name or "").lower()).strip()
    return s

def run():
    base=json.loads((OUTPUT/"review_queue.json").read_text())["records"]
    deep=json.loads((OUTPUT/"deep_full_document_evidence.json").read_text())["records"]
    curated=json.loads((OUTPUT/"source_specific_identity_recovery.json").read_text())["records"]
    letterhead=json.loads((OUTPUT/"institutional_letterhead_leads.json").read_text())["records"]
    deep_by={r["filing_id"]:r for r in deep}
    curated_by={r["filing_id"]:r for r in curated}
    letter_by={r["filing_id"]:r for r in letterhead}
    original={str(x["submission_id"]):x for x in load()}
    assert len(base)==567
    assert all(x["filing_id"] in original for x in base)
    assert not set(curated_by)-set(deep_by)
    out=[]; capacities=Counter(); issue=Counter(); statuses=Counter()
    unique_status=defaultdict(set)
    for rec in base:
        fid=rec["filing_id"]
        if rec["new_primary_role_candidate"]:
            role=rec["new_primary_role_candidate"]
            source="first_person_source_rules"
        elif fid in curated_by:
            role=curated_by[fid]["capacity"]
            source="individually_inspected_source_phrase"
        elif fid in deep_by and deep_by[fid]["new_source_roles"]:
            role=deep_by[fid]["new_source_roles"][0]["role"]
            source="full_document_source_scan"
        else:
            role=""
            source="capacity_unstated_in_original"
        letter=letter_by.get(fid,{})
        refs=[ORG_REFERENCES[x] for x in letter.get("first_page_organization_websites",[])
              if x in ORG_REFERENCES]
        topics=set(rec.get("detected_argument_themes",[]))
        groups=sorted(k for k,v in COHORTS.items() if topics & v)
        if not groups:groups=["other_or_no_coded_argument"]
        issue.update(groups)
        capacities[role or "capacity_unstated"]+=1
        statuses[source]+=1
        norm=filer_key(original[fid].get("filer_raw","")) or "filing:"+fid
        unique_status[role or "capacity_unstated"].add(norm)
        out.append({
          "filing_id":fid,
          "source_url":rec["source_url"],
          "source_supported_identity_role":role,
          "source_evidence_route":source,
          "source_evidence_code":(
              rec.get("identity_basis") if source=="first_person_source_rules"
              else "|".join(x["evidence_code"] for x in deep_by[fid]["new_source_roles"])
                    if source=="full_document_source_scan"
              else curated_by[fid]["evidence_kind"] if source=="individually_inspected_source_phrase"
              else ""),
          "candidate_institution_from_letterhead":"|".join(x["org"] for x in refs),
          "institution_sector_from_official_site":"|".join(x["sector"] for x in refs),
          "external_organization_site":"|".join(x["official"] for x in refs),
          "affiliation_independently_proven":"NO",
          "other_institutional_domain_lead":"|".join(
              x for x in letter.get("first_page_organization_websites",[])
              if x not in ORG_REFERENCES),
          "issue_cohorts":"|".join(groups),
          "issue_codes":"|".join(sorted(topics)),
          "model_only_role_hint":rec.get("independent_model_role_lead") or "",
          "source_length_band":rec.get("source_length_band",""),
          "coordinated_text_cluster_id":(
              rec.get("suspected_template_cluster") or {}).get("cluster_id",""),
          "status_for_analysis":"identified_source_capacity" if role else (
              "named_individual_possible_organization_link" if letter
              else "named_individual_capacity_not_stated"),
          "automatic_production_change":"NO"
        })
    distinct_all=len({filer_key(original[x["filing_id"]].get("filer_raw",""))
                   or "filing:"+x["filing_id"] for x in base})
    source_known=set().union(*(v for k,v in unique_status.items()
                             if k!="capacity_unstated"))
    missing_in_some=unique_status["capacity_unstated"]
    fully_missing=missing_in_some-source_known
    mixed_filings=missing_in_some & source_known
    summary={
        "schema_version":"unpublished-research-consolidated-v1",
        "source_filing_count":len(original),
        "original_filing_cohort":len(base),
        "original_distinct_normalized_filer_identifiers":distinct_all,
        "new_source_supported_role_filings":len(base)-capacities["capacity_unstated"],
        "new_source_supported_role_distinct_identifiers":len(source_known),
        "still_role_unstated_filings":capacities["capacity_unstated"],
        "still_role_unstated_distinct_identifiers":len(unique_status["capacity_unstated"]),
        "fully_role_unstated_distinct_identifiers":len(fully_missing),
        "mixed_role_and_unstated_filing_distinct_identifiers":len(mixed_filings),
        "source_recovery_methods":dict(statuses),
        "primary_capacity_counts":dict(capacities),
        "role_distinct_identifier_counts":{k:len(v) for k,v in unique_status.items()},
        "topic_cohort_counts_overlapping":dict(issue),
        "original_source_file_count_checked":len(original),
        "organization_letterhead_leads":len(letterhead),
        "meaning_of_unstated":"name exists; no supported occupation or stakeholder relationship in captured source",
        "policy":"do not promote model-only role or letterhead alone to employer identity",
        "website_changed":False,
    }
    (OUTPUT/"consolidated_identity_summary.json").write_text(
        json.dumps(summary,indent=2)+"\n")
    outpath=OUTPUT/"consolidated_identity_review.csv"
    with outpath.open("w",newline="",encoding="utf8") as f:
        fields=list(out[0])
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerows(sorted(out,key=lambda x:(
            0 if x["source_supported_identity_role"] else 1 if x["candidate_institution_from_letterhead"]
            else 2,x["filing_id"])))
    print(json.dumps(summary,indent=2))
    return summary
if __name__=="__main__":run()

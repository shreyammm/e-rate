#!/usr/bin/env python3
"""Privacy-minimal source-signature clues for personal-name FCC filers.

Only the author's own closing/signature or a terminal line matching the ECFS
filer name is considered. Never search arbitrary body mentions, references,
quoted emails, or outside employment databases. A professional email domain
supports a *provisional sector affiliation*, not an official institutional
filing, employer verification, or a specific occupation. Never export emails.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

EMAIL = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,})")
CLOSING = re.compile(
    r"(?im)^[ \t]*(?:sincerely(?: yours)?|respectfully(?: submitted)?|"
    r"(?:best|kind|warm) regards|regards|thanks(?: so much)?|thank you|"
    r"submitted by|signed by|with appreciation|yours truly)[ \t]*[,.:]?[ \t]*$"
)
GENERIC = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
    "outlook.com", "hotmail.com", "live.com", "aol.com",
    "icloud.com", "me.com", "msn.com", "protonmail.com",
    "proton.me", "mail.com", "comcast.net", "verizon.net",
    "att.net", "bellsouth.net", "sbcglobal.net",
}
SCHOOL_DOMAIN = re.compile(
    r"(?i)(?:^|\.)k12(?:\.|$)|"
    r"(?:^|[.-])(?:publicschools|schools|schooldistrict|"
    r"school-district|school-districts|usd\d*|isd\d*|cps\d*|"
    r"sd\d{2,4})(?:[.-]|$)"
)
LIBRARY_DOMAIN = re.compile(
    r"(?i)(?:^|[.-])(?:publiclibrary|county-library|"
    r"countylibrary|libraries|library)(?:[.-]|$)"
)
TITLE = (
    ("school_technology_staff", re.compile(
        r"(?i)^(?:(?:school|district)\s+)?(?:director of (?:information\s+)?technology|"
        r"information technology director|technology coordinator|"
        r"technology services director|network administrator|"
        r"school chief information officer|school IT specialist|"
        r"district e[- ]rate coordinator)\s*$")),
    ("school_administrator", re.compile(
        r"(?i)^(?:(?:assistant|vice)\s+)?(?:principal|"
        r"superintendent|school administrator|head of school|"
        r"school board (?:member|trustee))\s*$")),
    ("school_educator", re.compile(
        r"(?i)^(?:classroom teacher|special education teacher|"
        r"elementary teacher|middle school teacher|high school teacher|"
        r"school counselor|substitute teacher)\s*$")),
    ("library_staff", re.compile(
        r"(?i)^(?:librarian|library (?:director|assistant|technician|"
        r"manager|media specialist)|director of libraries)\s*$")),
    ("library_affiliated", re.compile(
        r"(?i)^(?:library (?:board|trustee|volunteer)|"
        r"library board (?:member|president))\s*$")),
    ("erate_consultant", re.compile(
        r"(?i)^(?:e[- ]rate (?:consultant|advisor|adviser|"
        r"funding consultant)|director of e[- ]rate consulting)\s*$")),
)

@dataclass(frozen=True)
class SignatureSignal:
    role: str = ""
    basis: str = ""
    cue: str = ""
    has_email: bool = False


def _signature_region(text: str, filer_name: str = "") -> str:
    """Return a plausible self-signature, without arbitrary full-text matches."""
    text = str(text or "")
    tail = text[-min(len(text), 2600):]
    matches = list(CLOSING.finditer(tail))
    name = " ".join(str(filer_name or "").split())
    valid_name = bool(3 <= len(name) <= 90 and re.fullmatch(
        r"[A-Za-z][A-Za-z'.-]*(?:\s+[A-Za-z][A-Za-z'.-]*){1,3}", name
    ))
    if matches:
        # A title/email in a representative's or quoted person's signature
        # must not silently overwrite the actual ECFS filer identity.
        region = tail[matches[-1].end():]
        if len(region) <= 1600:
            region = region[:1100]
            if valid_name:
                signer = re.compile(r"(?im)^[ \t]*" +
                    re.escape(name).replace(r"\ ", r"\s+") +
                    r"[ \t]*,?[ \t]*$")
                if not signer.search(region):
                    return ""
            return region
    if not 3 <= len(name) <= 90 or not re.fullmatch(
        r"[A-Za-z][A-Za-z'.-]*(?:\s+[A-Za-z][A-Za-z'.-]*){1,3}", name
    ):
        return ""
    # No person-name search in middle sections or bibliographies. Exact
    # standalone author-name line in the final 1200 characters is required.
    last = text[-min(len(text), 1200):]
    if re.search(r"(?im)^\s*(?:references|works cited|bibliography|appendix)\s*:?", last):
        return ""
    rx = re.compile(r"(?im)^[ \t]*" + re.escape(name).replace(r"\ ", r"\s+")
                    + r"[ \t]*,?[ \t]*$")
    anchors = list(rx.finditer(last))
    if not anchors:
        return ""
    region = last[anchors[-1].start():]
    return region[:850] if region.count("\n") <= 16 else ""


def domain_sector(domain: str) -> str:
    """Only strong institutional domain shapes; no generic .edu/.org inference."""
    domain = str(domain or "").lower().strip(".")
    if domain in GENERIC or domain.endswith(".gov") and not SCHOOL_DOMAIN.search(domain):
        # A government address alone does not establish governmental speech.
        return ""
    if SCHOOL_DOMAIN.search(domain):
        return "school_connected_unknown"
    if LIBRARY_DOMAIN.search(domain):
        return "library_affiliated"
    return ""


def signature_signal(text: str, filer_name: str = "") -> SignatureSignal:
    region = _signature_region(text, filer_name)
    if not region:
        return SignatureSignal()
    lines = [re.sub(r"\s+", " ", x).strip(" \t,;:") for x in region.splitlines()[:16]]
    # The title must be a standalone signature line, not a sentence from
    # argumentation, a letterhead claim, or a name collision in a reference.
    title_roles = []
    for line in lines:
        if not line or len(line) > 95:
            continue
        cleaned = re.sub(r"(?i)^(?:title|position)\s*:\s*", "", line)
        for role, rx in TITLE:
            if rx.fullmatch(cleaned):
                title_roles.append(role)
                break
    if title_roles:
        if len(set(title_roles)) == 1:
            return SignatureSignal(title_roles[0], "terminal_signature_job_title",
                                   "occupational title in author signature",
                                   bool(EMAIL.search(region)))
        return SignatureSignal(has_email=bool(EMAIL.search(region)))

    domains = {m.group(1).lower().rstrip(".") for m in EMAIL.finditer(region)}
    classified = {domain_sector(x) for x in domains if domain_sector(x)}
    # Mixed sectors or multiple domain types are not a reliable affiliation.
    if len(classified) == 1 and (len(domains) == 1 or
                                all(domain_sector(x) in classified for x in domains)):
        role = next(iter(classified))
        return SignatureSignal(role, "signature_institutional_email_domain",
                               "institutional email domain in author signature", True)
    return SignatureSignal(has_email=bool(domains))


if __name__ == "__main__":
    import unittest
    unittest.main(module=None)

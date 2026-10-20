#!/usr/bin/env python3
"""Build the public, source-verified full-text reader from repository gzip JSONL.

The published JSON index contains metadata and the exact shard address for every
filing. Full source texts stay gzip-compressed and are loaded one shard at a time
by the browser; no source document is shortened or silently reclassified.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/fcc_corpus"
DEST = ROOT / "docs/data"
FIELDS = (
    "submission_id", "filer_raw", "date_submission", "source_url",
    "has_unreviewed_ocr", "agency_record_candidate",
)

def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def build(source: Path = SRC, output: Path = DEST, *, verify_only: bool = False) -> dict:
    source, output = source.resolve(), output.resolve()
    manifest = json.loads((source/"manifest.json").read_text(encoding="utf-8"))
    expected = manifest["shards"]
    expected_count = int(manifest["records"])
    if not expected or len({s["name"] for s in expected}) != len(expected):
        raise ValueError("Missing/duplicate source shards")
    actual_files = sorted(f.name for f in (source/"shards").glob("filings-*.jsonl.gz"))
    expected_files = sorted(s["name"] for s in expected)
    if actual_files != expected_files:
        raise ValueError("Actual shard files differ from the source manifest")
    indexed = []
    seen = set()
    total_with_text = 0
    for n, spec in enumerate(expected):
        src = source/"shards"/spec["name"]
        if not re.fullmatch(r"filings-\d{4}\.jsonl\.gz", src.name):
            raise ValueError("Unexpected shard filename")
        raw = src.read_bytes()
        if checksum(raw) != spec["sha256"]:
            raise ValueError("Compressed shard checksum mismatch: "+src.name)
        count = 0
        with gzip.open(src, "rt", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                sid = str(record["submission_id"])
                if not re.fullmatch(r"\d{8,20}", sid) or sid in seen:
                    raise ValueError("Duplicate/invalid submission ID: "+sid)
                seen.add(sid)
                body = str(record.get("text") or "")
                if body:
                    total_with_text += 1
                if record.get("text_sha256") and checksum(body.encode("utf-8")) != record["text_sha256"]:
                    raise ValueError("Filing text hash mismatch: "+sid)
                if body and not record.get("text_sha256"):
                    raise ValueError("Nonempty record without SHA-256: "+sid)
                row = {key:record.get(key, "") for key in FIELDS}
                row.update(
                    shard=spec["name"], chars=len(body),
                    words=len(body.split()), source_sha256=record.get("text_sha256", ""),
                    has_text=bool(body),
                )
                indexed.append(row)
                count += 1
        if count != int(spec["records"]):
            raise ValueError("Shard record count mismatch: "+src.name)
        if not verify_only:
            target = output/"full_text_shards"/src.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or checksum(target.read_bytes()) != spec["sha256"]:
                shutil.copyfile(src, target)
    if len(seen) != expected_count:
        raise ValueError("Total source filing count mismatch")
    if total_with_text != int(manifest["records_with_text"]):
        raise ValueError("Source text coverage mismatch")
    indexed.sort(key=lambda item:item["submission_id"])
    result = {
        "schema_version": "1.0",
        "snapshot_id": manifest.get("snapshot_id"),
        "text_view": manifest.get("text_view"),
        "source": "FCC ECFS snapshot; OCR candidate text is not human-verified",
        "records": len(indexed),
        "records_with_text": total_with_text,
        "records_without_text": len(indexed)-total_with_text,
        "compressed_bytes": sum(int(x["compressed_bytes"]) for x in expected),
        "shards": [{"name":x["name"], "sha256":x["sha256"], "records":x["records"]} for x in expected],
        "filings": indexed,
    }
    if not verify_only:
        output.mkdir(parents=True, exist_ok=True)
        target = output/"full_corpus_index.json"
        serialized = json.dumps(result, separators=(",",":"),ensure_ascii=False)+"\n"
        if not target.exists() or target.read_text(encoding="utf-8") != serialized:
            target.write_text(serialized,encoding="utf-8")
    return {k:v for k,v in result.items() if k != "filings"}

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=SRC)
    parser.add_argument("--output",type=Path,default=DEST)
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    print(json.dumps(build(args.source,args.output,verify_only=args.verify_only),indent=2))

if __name__ == "__main__":
    main()

"""Fetch bounded official annotations only; images and model inference are separate."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.parse
import urllib.request
import zipfile

import yaml

from vlmbench.io_utils import atomic_bytes, sha256_file, write_json


ALLOWED_HOSTS = {"raw.githubusercontent.com", "www.robots.ox.ac.uk", "thor.robots.ox.ac.uk"}


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Metadata redirect left the official HTTPS allowlist")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(config, cache, *, offline=False):
    cache.mkdir(parents=True, exist_ok=True)
    receipt_path = cache / "receipt.json"
    prior = json.loads(receipt_path.read_text()) if receipt_path.exists() else {"files": {}}
    downloaded, files = 0, {}
    for key, spec in config["sources"].items():
        if Path(spec["file"]).name != spec["file"]:
            raise ValueError("Cache filename must be a single basename")
        parsed = urllib.parse.urlsplit(spec["url"])
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Only official HTTPS metadata hosts are allowed")
        path = cache / spec["file"]
        old = prior["files"].get(key)
        if path.exists():
            expected = spec.get("sha256") or (old or {}).get("sha256")
            if not expected or sha256_file(path) != expected:
                raise ValueError(f"Cache checksum unverified/differs: {key}; preserve and inspect")
            if old and (old["url"] != spec["url"] or old["revision"] != spec["revision"]):
                raise ValueError("Cached receipt belongs to a different source")
            files[key] = old or {**spec, "sha256": expected, "bytes": path.stat().st_size}
            continue
        if offline:
            raise ValueError(f"Missing cached metadata: {key}")
        budget = min(spec["max_bytes"], config["max_total_download_mb"] * 1024**2 - downloaded)
        if budget <= 0:
            raise ValueError("Metadata budget exhausted")
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "vlmbench/0.1"})
        with urllib.request.build_opener(OfficialRedirect()).open(request, timeout=45) as response:
            content = response.read(budget + 1)
        if len(content) > budget:
            raise ValueError("Metadata budget exceeded; no automatic increase")
        digest = hashlib.sha256(content).hexdigest()
        if spec.get("sha256") and spec["sha256"] != digest:
            raise ValueError("Downloaded annotation checksum differs from source pin")
        atomic_bytes(path, content)
        files[key] = {"url": spec["url"], "revision": spec["revision"], "file": spec["file"],
                      "sha256": digest, "bytes": len(content)}
        downloaded += len(content)
        # A completed file can be reused after an interrupted acquisition.
        write_json(receipt_path, {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": files})
    extracted = {}
    with zipfile.ZipFile(cache / "tallyqa.zip") as archive:
        candidates = [i for i in archive.infolist() if i.filename.split("/")[-1] == "test.json"]
        if len(candidates) != 1 or candidates[0].file_size > 25000000:
            raise ValueError("Unexpected TallyQA test annotation member/size")
        payload = archive.read(candidates[0])
        json.loads(payload)
        atomic_bytes(cache / "tallyqa_test.json", payload)
        extracted["tallyqa_test.json"] = {"archive_member": candidates[0].filename,
            "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    with tarfile.open(cache / "pet_annotations.tar.gz", "r:gz") as archive:
        for filename in ("list.txt", "trainval.txt", "test.txt", "README"):
            name = "annotations/" + filename
            member = archive.getmember(name)
            if not member.isfile() or member.size > 2000000:
                raise ValueError("Unexpected Pet annotation member")
            payload = archive.extractfile(member).read()
            target = "pet_" + filename
            atomic_bytes(cache / target, payload)
            extracted[target] = {"archive_member": name, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    receipt = {"schema_version": 1, "files": files, "extracted": extracted,
               "scope": "metadata only; annotation archives retained, no photo archive downloaded",
               "retrieved_at_utc": prior.get("retrieved_at_utc") or datetime.now(timezone.utc).isoformat()}
    write_json(receipt_path, receipt)
    return {"downloaded_bytes_this_run": downloaded, "files": files, "extracted": extracted}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/data_sources_v1.yaml")
    p.add_argument("--cache", default="data/raw/main_metadata_v1")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    print(json.dumps(fetch(yaml.safe_load(Path(args.config).read_text()), Path(args.cache), offline=args.offline), indent=2))


if __name__ == "__main__":
    main()

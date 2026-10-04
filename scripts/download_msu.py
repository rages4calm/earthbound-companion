"""Download the creator-linked EarthBound PCM pack, verifying every payload."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
out = root / "EarthBound Companion" / "msu"
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / "research/msu-manifest.json").read_text(encoding="utf-8-sig"))

def download(entry):
    name = entry["name"]
    target = out / name
    expected = entry["md5"]
    if target.exists() and hashlib.file_digest(target.open("rb"), "md5").hexdigest() == expected:
        return name
    temp = target.with_suffix(".part")
    for attempt in range(4):
        try:
            digest = hashlib.md5()
            with urllib.request.urlopen("https://archive.org/download/earthbound-msu-1-pack/" + name, timeout=90) as response, temp.open("wb") as stream:
                while chunk := response.read(256 * 1024):
                    digest.update(chunk)
                    stream.write(chunk)
            if temp.stat().st_size != int(entry["size"]) or digest.hexdigest() != expected:
                raise ValueError("size or checksum mismatch")
            temp.replace(target)
            return name
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(download, entry): entry["name"] for entry in manifest}
    failures = []
    for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
        try:
            name = future.result()
            print(f"{count}/{len(manifest)} verified {name}", flush=True)
        except Exception as error:
            failures.append(f"{futures[future]}: {error}")
            print("FAILED " + failures[-1], flush=True)
    (root / "validation/msu-download.json").write_text(json.dumps({"expected":len(manifest),"verified":len(manifest)-len(failures),"failures":failures}, indent=2))
    if failures:
        raise SystemExit(1)

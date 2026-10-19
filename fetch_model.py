# nudenet-svc — AGPL-3.0-or-later (see LICENSE)
"""Build step: download the NudeNet model from the upstream release and verify its SHA-256."""
import hashlib
import sys
import urllib.request

url, sha, dest = sys.argv[1:4]
req = urllib.request.Request(url, headers={"Accept": "application/octet-stream", "User-Agent": "nudenet-svc-build"})
data = urllib.request.urlopen(req, timeout=600).read()
digest = hashlib.sha256(data).hexdigest()
if digest != sha:
    sys.exit(f"model checksum mismatch: got {digest}, expected {sha}")
with open(dest, "wb") as f:
    f.write(data)
print(f"model ok: {dest} ({len(data)} bytes, sha256 {digest})")

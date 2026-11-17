"""Create a signed update package (.murmurupdate) from a built Murmur folder.

    python tools/make_update.py --payload C:\\murmur-build\\dist\\Murmur --version 1.2.0 --out D:\\

Copy the resulting file to a USB stick (or a network share). Murmur PCs that see it verify the
signature with the public key built into the app, and only then offer the update.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import zipfile

from cryptography.hazmat.primitives import serialization

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY = os.path.join(os.path.expanduser("~"), ".murmur-signing", "update-private.pem")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True, help="folder containing Murmur.exe and its files")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True, help="folder to write the .murmurupdate file into")
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--notes", default="")
    ap.add_argument("--allow-mismatch", action="store_true", help="testing only")
    a = ap.parse_args()
    if not os.path.exists(os.path.join(a.payload, "Murmur.exe")):
        sys.exit("Murmur.exe not found in payload folder")
    init = open(os.path.join(HERE, "..", "murmur", "__init__.py"), encoding="utf-8").read()
    app_version = init.split('"')[1] if '"' in init else ""
    if a.version != app_version and not a.allow_mismatch:
        sys.exit(f"--version {a.version} does not match murmur/__init__.py ({app_version}). Bump the app version "
                 "and rebuild first, otherwise installed copies would keep re-offering this update.")
    with open(a.key, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    os.makedirs(a.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        payload_zip = os.path.join(tmp, "payload.zip")
        with zipfile.ZipFile(payload_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for root, _, files in os.walk(a.payload):
                for fn in files:
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, a.payload))
        manifest = json.dumps({
            "format": 1, "app": "Murmur", "version": a.version, "notes": a.notes,
            "payload_sha256": sha256_file(payload_zip), "payload_size": os.path.getsize(payload_zip),
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, indent=2).encode()
        sig = priv.sign(manifest)
        out = os.path.join(a.out, f"Murmur-Update-{a.version}.murmurupdate")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
            z.writestr("manifest.json", manifest)
            z.writestr("manifest.sig", sig)
            z.write(payload_zip, "payload.zip")
    print("wrote", out, f"({os.path.getsize(out) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()

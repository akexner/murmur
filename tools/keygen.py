"""One-time: create the update-signing key pair.

The PRIVATE key stays on your machine (default: %USERPROFILE%\\.murmur-signing\\update-private.pem).
Never commit it, never share it, and back it up (see README). The PUBLIC key is written into
murmur/update_pubkey.py and is compiled into every Murmur build; it can only VERIFY signatures.
"""
import argparse
import base64
import os
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY = os.path.join(os.path.expanduser("~"), ".murmur-signing", "update-private.pem")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--force", action="store_true", help="overwrite an existing key (old updates stop verifying!)")
    a = ap.parse_args()
    if os.path.exists(a.key) and not a.force:
        print("A key already exists at", a.key, "- refusing to overwrite (use --force only if you mean it).")
        sys.exit(1)
    os.makedirs(os.path.dirname(a.key), exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    with open(a.key, "wb") as f:
        f.write(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                   serialization.NoEncryption()))
    pub = base64.b64encode(priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    out = os.path.join(HERE, "..", "murmur", "update_pubkey.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write('"""Public update-verification key (safe to publish; it can only verify)."""\n'
                f'PUBLIC_KEY_B64 = "{pub}"\n')
    print("private key:", a.key)
    print("public key written to", os.path.normpath(out))
    print("public key:", pub)


if __name__ == "__main__":
    main()

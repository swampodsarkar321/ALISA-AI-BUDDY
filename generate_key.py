"""ALISA key generator — OWNER ONLY. Keep your secret private!

Usage:
    python generate_key.py --name "Rafi"

Then send the printed key to the buyer (bKash payment first!).
The buyer opens ALISA → Activation Center → pastes the key.

Before distributing: change OWNER_SECRET in alisa/license.py to your own
random string AND update it here (both must match).
"""

import argparse
import sys

sys.path.insert(0, ".")

KEYS_LOG = "sold_keys.txt"


def main():
    ap = argparse.ArgumentParser(description="Generate ALISA premium keys")
    ap.add_argument("--name", default="", help="buyer note (saved in sold_keys.txt only)")
    ap.add_argument("--count", type=int, default=1)
    args = ap.parse_args()

    from alisa.license import make_key, verify_key, key_hash

    keys = []
    for _ in range(max(1, min(args.count, 50))):
        key = make_key(args.name)
        assert verify_key(key), "self-check failed!"
        keys.append(key)

    with open(KEYS_LOG, "a", encoding="utf-8") as f:
        for k in keys:
            f.write(f"{k}  |  {args.name}\n")

    print(f"Generated {len(keys)} key(s) (also saved to {KEYS_LOG}):")
    for k in keys:
        print(" ", k)
        print("   hash:", key_hash(k))
    print()
    print("NEXT: register each hash in Firebase so online check passes:")
    print("  console.firebase.google.com → chat-2-me-c3213 → Realtime Database")
    print("  → keyHashes → Add child: <hash> = {\"revoked\": false}")
    print("Rules needed once: {\"rules\": {\"keyHashes\": {\".read\": true}, ...}}")


if __name__ == "__main__":
    main()

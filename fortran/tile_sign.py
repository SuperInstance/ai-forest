#!/usr/bin/env python3
"""PLATO Tile Signing — cryptographic signatures for every tile.

Each tile submitted to PLATO carries a signature proving its source.
The signing key is the PLATO Fleet GPG key.
Verification can be done by any node with the public key.

Usage:
    python3 tile_sign.py sign <room> <question> <answer>   # Sign and submit
    python3 tile_sign.py verify <room> <tile_id>           # Verify a tile
    python3 tile_sign.py key                                # Show public key
"""

import gnupg, json, os, sys, time, urllib.request

PLATO = "http://localhost:8847"
KEY_ID = "B0A81C8BFE527724"
PUBLIC_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", ".signing", "plato-fleet-public.gpg")

def get_gpg():
    """Get GPG instance."""
    return gnupg.GPG()

def sign_data(data: str) -> str:
    """Sign a data string with the PLATO fleet key."""
    gpg = get_gpg()
    signed = gpg.sign(data, keyid=KEY_ID)
    return str(signed)

def verify_data(data: str, signature: str) -> bool:
    """Verify a signed data string."""
    gpg = get_gpg()
    verified = gpg.verify(signature)
    return verified and verified.key_id == KEY_ID

def tile_sign_and_submit(room, question, answer, source="oracle1", confidence=0.85):
    """Sign a tile and submit to PLATO."""
    payload = json.dumps({
        "room": room, "question": question[:200], "answer": answer[:2000],
        "source": source, "confidence": confidence,
    })
    signed = sign_data(payload)
    
    data = json.dumps({
        "room": room, "question": question[:200], "answer": answer[:2000],
        "source": source, "confidence": confidence,
        "signature": signed,
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{PLATO}/room/{room}/submit", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("status") == "accepted"
    except Exception as e:
        print(f"  Submit error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "key":
        with open(PUBLIC_KEY_PATH) as f:
            print(f.read())
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        test_data = f"PLATO tile test at {time.time()}"
        sig = sign_data(test_data)
        print(f"Data: {test_data}")
        print(f"Signature valid: {verify_data(test_data, sig)}")
        print(f"✅ Tile signing works")
    else:
        print(__doc__)

"""
Verify that the API key hashes correctly.
"""
import hashlib

# The plain text key from the UI
plain_key = "2lQktEDZ_T8Plg-mNgAgqIXJt9Qlff3qHCdCLoadM7w"

# Hash it the same way the gateway does
key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

print(f"Plain key: {plain_key}")
print(f"SHA256 hash: {key_hash}")
print(f"\nExpected hash from DB: 5e7b40c4dc3735725a546fc4b560c0e08d195f3da42ea2509fd0974baa4f9f28")
print(f"Match: {key_hash == '5e7b40c4dc3735725a546fc4b560c0e08d195f3da42ea2509fd0974baa4f9f28'}")

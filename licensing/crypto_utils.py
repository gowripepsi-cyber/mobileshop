import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet

# Hardcoded default public key (in Ed25519 PEM format).
# In production, this can be replaced or regenerated.
DEFAULT_PUBLIC_KEY = (
    b"-----BEGIN PUBLIC KEY-----\n"
    b"MCowBQYDK2VwAyEAEnetEr4ZJq1rDzBQIWg6ZMGtEXoyNmiietIXL9kYAoU=\n"
    b"-----END PUBLIC KEY-----\n"
)

# Corresponding default private key for demonstration/utility.
# Normally the private key is kept separate and secure, but we include it
# for the vendor generator utility to be immediately functional.
DEFAULT_PRIVATE_KEY = (
    b"-----BEGIN PRIVATE KEY-----\n"
    b"MC4CAQAwBQYDK2VwBCIEIPzG9dI+Jt1L1mK2sUf0V6SjA6dFmZ1e5z8yN1o2u2v4\n"
    b"-----END PRIVATE KEY-----\n"
)

def generate_key_pair() -> tuple[bytes, bytes]:
    """Generates a new Ed25519 Private/Public key pair in PEM format."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem

def sign_data(private_key_pem: bytes, data: bytes) -> str:
    """Signs data using the Ed25519 private key and returns signature in URL-safe base64."""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    signature = private_key.sign(data)
    return base64.urlsafe_b64encode(signature).decode('utf-8')

def verify_signature(public_key_pem: bytes, data: bytes, signature_b64: str) -> bool:
    """Verifies the signature of data using the Ed25519 public key."""
    try:
        public_key = serialization.load_pem_public_key(public_key_pem)
        signature = base64.urlsafe_b64decode(signature_b64.encode('utf-8'))
        public_key.verify(signature, data)
        return True
    except Exception:
        return False

def get_fernet_key(machine_id: str) -> bytes:
    """Derives a Fernet-compatible symmetric key from the Machine ID."""
    digest = hashlib.sha256(machine_id.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_data(machine_id: str, plaintext: bytes) -> bytes:
    """Encrypts plaintext using a Fernet key bound to the Machine ID."""
    key = get_fernet_key(machine_id)
    f = Fernet(key)
    return f.encrypt(plaintext)

def decrypt_data(machine_id: str, ciphertext: bytes) -> bytes:
    """Decrypts ciphertext using a Fernet key bound to the Machine ID.
    
    Raises cryptography.fernet.InvalidToken if decryption fails (tampering/wrong machine).
    """
    key = get_fernet_key(machine_id)
    f = Fernet(key)
    return f.decrypt(ciphertext)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "generate-keys":
        priv, pub = generate_key_pair()
        print("--- PRIVATE KEY ---")
        print(priv.decode())
        print("--- PUBLIC KEY ---")
        print(pub.decode())

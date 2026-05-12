from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from base64 import b64decode, b64encode
from dataclasses import dataclass
from hashlib import sha256

from mahkrabdtn.protocol.encryption import EncryptionMetadata
from mahkrabdtn.protocol.parsing.text import parse_text
from mahkrabdtn.crypto.constants import ALGORITHM, ENCODING


@dataclass(slots=True)
class NodeKeyPair:
    privateKeyPem: str
    publicKeyPem: str
    

class RsaEncryption:
    def load_public_key(publicKeyPem: str) -> RSAPublicKey:
        publicKeyPem = parse_text(publicKeyPem, "publicKeyPem")
        key = serialization.load_der_public_key(publicKeyPem.encode("utf-8"))
        
        if not isinstance(key, RSAPublicKey): raise TypeError("publicKeyPem must be of type RSAPublicKey")
        
        return key
    
    def load_private_key(privateKeyPem: str) -> RSAPrivateKey:
        privateKeyPem = parse_text(privateKeyPem, "privateKeyPem")
        key = serialization.load_pem_private_key(privateKeyPem.encode("utf-8"))
        
        if not isinstance(key, RSAPrivateKey): raise TypeError("private key must be of type RSA private key")
        
        return key
    
    def serialize_public_key(publicKey: RSAPublicKey) -> str:
        return publicKey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def serialize_private_key(privateKey: RSAPrivateKey) -> str:
        return privateKey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        
    def create_node_key_pair(IDPath: str | Path) -> Path:
        privateKeyPath = Path(IDPath).with_suffix(".privkey.pem")
        privateKeyPath.parent.mkdir(parents=True, exist_ok=True)
        
        if privateKeyPath.exists():
            privateKeyPem = privateKeyPath.read_text(encoding="utf-8")
        else:
            privateKey = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            privateKeyPem = RsaEncryption.serialize_private_key(privateKey)
            privateKeyPath.write_text(privateKeyPem, encoding="utf-8")
        
        publicKeyPem = RsaEncryption.serialize_public_key(RsaEncryption.load_private_key(privateKeyPem).public_key())
        
        return NodeKeyPair(
            privateKeyPem=privateKeyPem,
            publicKeyPem=publicKeyPem,
        ),
        
    def compute_public_key_ID(publicKeyPem: str) -> str:
        publicKey = RsaEncryption.load_public_key(publicKeyPem)
        publicKeyDer = publicKey.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )    
        return sha256(publicKeyDer).hexdigest()
    
    def encrypt(plaintext: str, recipientPublicKeyPem: str) -> tuple[str, EncryptionMetadata]:
        plaintext = parse_text(plaintext, "plaintext")
        publicKey = RsaEncryption.load_public_key(recipientPublicKeyPem)
        ciphertext = publicKey.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            ),
        )
        encoded = b64encode(ciphertext).decode("ascii")
        metadata = EncryptionMetadata(
            algorithm=ALGORITHM,
            encoding=ENCODING,
            recipientKeyID=RsaEncryption.compute_public_key_ID(recipientPublicKeyPem),
        )
        return encoded, metadata
    
    def decrypt(ciphertext: str, privateKeyPem: str, metadata: EncryptionMetadata) -> str:
        ciphertext = parse_text(ciphertext, "ciphertext")
        
        if metadata.algorithm == "none": return ciphertext
        if metadata.algorithm != ALGORITHM: raise ValueError(f"unsupported encryption algorithm: {metadata.algorithm}")
        if metadata.encoding != ENCODING: raise ValueError(f"unsupported encoding: {metadata.encoding}")
        
        privateKey = RsaEncryption.load_private_key(privateKeyPem)
        ownPublicKeyPem = RsaEncryption.serialize_public_key(privateKey.public_key())
        ownPublicKeyID = RsaEncryption.compute_public_key_ID(ownPublicKeyPem)
        
        if metadata.recipientKeyID != ownPublicKeyID: raise ValueError("ciphertext does not match the recipient key fingerprint")
        
        decoded = b64decode(ciphertext.encode("ascii"), validate=True)
        plaintext = privateKey.decrypt(
            decoded,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode("utf-8")
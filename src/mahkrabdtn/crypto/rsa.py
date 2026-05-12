from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from dataclasses import dataclass

from mahkrabdtn.protocol.encryption import EncryptionMetadata
from mahkrabdtn.protocol.parsing.text import parse_text


@dataclass(slots=True)
class NodeKeyPair:
    privateKeyPem: str
    publicKeyPem: str
    

class RsaEncryption:
    def load_private_key(privateKeyPem: str) -> RSAPrivateKey:
        privateKeyPem = parse_text(privateKeyPem, "privateKeyPem")
        key = serialization.load_pem_private_key(privateKeyPem.encode("utf-8"))
        
        if not isinstance(key, RSAPrivateKey):
            raise TypeError("private key must be of type RSA private key")
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
        
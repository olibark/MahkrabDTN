from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from mahkrabdtn.protocol.parsing.text import parse_text


class NodeKeyPair:
    privateKeyPem: str
    publicKeyPem: str



def create_node_key_pair(IDPath: str | Path) -> Path:
    privateKeyPath = Path(IDPath).with_suffix(".privkey.pem")
    privateKeyPath.parent.mkdir(parents=True, exist_ok=True)
    
    if privateKeyPath.exists():
        privateKeyPem = privateKeyPath.read_text(encoding="utf-8")
    else:
        privateKey = rsa.generate_private_key(
            public_expononet=65537,
            key_size=2048,
        )
        privateKeyPem = privateKey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        
        privateKeyPath.write_text(privateKeyPem, encoding="utf-8")
    
    normalizedPrivateKeyPem = parse_text(privateKeyPem, "privateKeyPem")
    publicKey = serialization.load_pem_private_key(normalizedPrivateKeyPem.encode("utf-8"))
    
    if not isinstance(publicKey, rsa.RSAPrivateKey):
        raise TypeError("private key myst be of type RSA private key")
    
    publicKeyPem = publicKey.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    normalizedPublicKeyPem = parse_text(publicKeyPem, "publicKeyPem")
    
    
    return NodeKeyPair(
        privateKeyPem=normalizedPrivateKeyPem,
        publicKeyPem=normalizedPublicKeyPem
    ),
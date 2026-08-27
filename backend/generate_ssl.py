import datetime

# 生成自签名证书
key_path = "key.pem"
cert_path = "cert.pem"

# 生成私钥和证书
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# 生成私钥
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# 生成证书
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SJB"),
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

certificate = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([x509.DNSName("localhost")]),
    critical=False,
).sign(
    private_key, hashes.SHA256(), default_backend()
)

# 保存私钥
with open(key_path, "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# 保存证书
with open(cert_path, "wb") as f:
    f.write(certificate.public_bytes(serialization.Encoding.PEM))

print(f"生成证书成功：{key_path}, {cert_path}")
"""Genera un par de claves VAPID para Web Push.

Uso:  python scripts/generate_vapid.py
Copiar la salida al .env. ¡NO regenerar en producción! — cambiar las claves
invalida todas las suscripciones push existentes.
"""
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01, b64urlencode

v = Vapid01()
v.generate_keys()

public = b64urlencode(v.public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
))
private = b64urlencode(
    v.private_key.private_numbers().private_value.to_bytes(32, 'big')
)

print(f'VAPID_PUBLIC_KEY={public}')
print(f'VAPID_PRIVATE_KEY={private}')
print('VAPID_ADMIN_EMAIL=admin@example.com  # cambiar por un email real')

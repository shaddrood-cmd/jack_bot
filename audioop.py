# Stub "audioop" pour Python 3.13+
# Discord.py tente d'importer ce module pour les fonctions vocales,
# mais ici on n'en a pas besoin. On définit donc des versions neutres.

def mul(fragment: bytes, width: int, factor: float) -> bytes:
    return fragment

def rms(fragment: bytes, width: int) -> int:
    return 0

def bias(fragment: bytes, width: int, bias: int) -> bytes:
    return fragment

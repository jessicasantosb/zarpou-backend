import random
import string
import re

from sqlalchemy.orm import Session

from app.features.coupons.infra.repositories import CouponRepository

CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{3,50}$")
# Sem caracteres ambíguos (0/O, 1/I/L) para o cliente digitar/ler sem erro.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
DEFAULT_LENGTH = 10


def generate_coupon_code(prefix: str = "", length: int = DEFAULT_LENGTH) -> str:
    """Gera um código aleatório seguro, sempre em MAIÚSCULAS.

    - Só letras maiúsculas e dígitos (sem acentos, espaços ou símbolos).
    - Remove caracteres ambíguos (0, O, 1, I, L) para facilitar a digitação.
    - `prefix` (ex.: "BLACK") é sanitizado e concatenado na frente.
    """
    clean_prefix = re.sub(r"[^A-Z0-9]", "", (prefix or "").upper())[:20]
    random_part = "".join(random.SystemRandom().choice(ALPHABET) for _ in range(max(length, 4)))
    return f"{clean_prefix}{random_part}"


def generate_unique_coupon_code(db: Session, prefix: str = "", length: int = DEFAULT_LENGTH) -> str:
    """Gera um código aleatório que ainda não existe na base."""
    repo = CouponRepository(db)
    for _ in range(100):
        code = generate_coupon_code(prefix=prefix, length=length)
        if CODE_PATTERN.match(code) and repo.get_by_code(code) is None:
            return code
    raise RuntimeError("Não foi possível gerar um código de cupom único.")

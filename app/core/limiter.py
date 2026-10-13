from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Rate Limiter central com estratégia por endereço IP remoto
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    enabled=settings.RATE_LIMIT_ENABLED,
)

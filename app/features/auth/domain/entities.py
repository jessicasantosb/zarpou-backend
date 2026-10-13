from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TokenEntity:
    access_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

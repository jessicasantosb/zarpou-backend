from dataclasses import dataclass
from typing import Optional


@dataclass
class AgencySettingEntity:
    id: str = "default"
    company_name: str = "Fly Promo"
    trading_name: str = "Fly Promo"
    cnpj: str = "55.849.201/0001-38"
    cadastur: str = "34.120.948/0001-90"
    whatsapp: str = "5531984210000"
    email: str = ""
    phone: str = "(31) 3344-5500"


@dataclass
class HeroConfigEntity:
    id: str = "default"
    title_prefix: str = "Seu"
    title_highlight: str = "sonho"
    title_suffix: str = "de viajar bem, agora é realidade"
    subtitle: str = ""
    bg_type: str = "video"
    bg_image_url: Optional[str] = None
    bg_video_url: Optional[str] = None
    cta_text: str = "Falar com um Especialista"
    cta_link: str = "whatsapp"

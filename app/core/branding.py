import re


_FORMER_BRAND = re.compile(
    r"(?<![\w@./-])zarpou(?: viagens(?: (?:e|&) turismo)?(?: ltda)?)?(?![\w/-]|\.\w)",
    re.IGNORECASE,
)


def refresh_brand(text: str) -> str:
    """Update saved display copy while preserving URLs and email addresses."""
    return _FORMER_BRAND.sub("Fly Promo", text)

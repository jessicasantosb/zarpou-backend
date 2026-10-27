"""
Registrador de importadores por recurso de catálogo.

Cada importador declara: colunas aceitas (nome, tipo, obrigatória, exemplo),
o model SQLAlchemy, a tela admin correspondente (permissão) e validações
extras. O motor de importação (services) é genérico: para adicionar uma tela
nova basta declarar um ImporterSpec aqui.

Regras de higienização (vale para todos os recursos):
- Cabeçalhos são normalizados (minúsculas, sem acentos, snake_case).
- Célula vazia em coluna opcional NÃO altera o valor já existente (update parcial).
- Célula vazia em coluna obrigatória é erro de linha.
- Código duplicado dentro da própria planilha é erro de linha (aponta a linha original).
- Upsert por código: se a chave (ex.: id, code) já existe no banco, o registro é atualizado.
"""
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.features.hotels.infra.models import Hotel
from app.features.destinations.infra.models import Destination
from app.features.flights.infra.models import Flight
from app.features.promotions.infra.models import Promotion
from app.features.coupons.infra.models import Coupon


class RowError(Exception):
    """Erro de validação/higienização de uma linha da planilha (mensagem ao usuário)."""


@dataclass
class Column:
    name: str
    required: bool = False
    kind: str = "str"  # str | int | float | bool | date | list
    example: str = ""
    description: str = ""


@dataclass
class ImporterSpec:
    resource: str
    label: str
    screen: str  # tela admin exigida (require_screen)
    model: type
    columns: List[Column]
    key_field: str = "id"
    extra_validate: Optional[Callable[[Dict[str, object]], None]] = None
    make_id: Optional[Callable[[Dict[str, object]], str]] = None  # id ao criar (quando a chave não é o id)

    @property
    def required_columns(self) -> List[str]:
        return [col.name for col in self.columns if col.required]


# ---------------------------------------------------------------------------
# Coerção de tipos (mensagens em PT-BR apontando o campo problemático)
# ---------------------------------------------------------------------------

_TRUE_VALUES = {"true", "1", "sim", "s", "yes", "y", "x", "v", "verdadeiro"}
_FALSE_VALUES = {"false", "0", "nao", "não", "n", "no", "f", "falso"}


def _coerce_int(raw: str, col_name: str):
    try:
        value = float(raw.replace(",", "."))
    except ValueError:
        raise RowError(f"campo '{col_name}': '{raw}' não é um número inteiro válido")
    if not value.is_integer():
        raise RowError(f"campo '{col_name}': '{raw}' não é um número inteiro válido")
    return int(value)


def _coerce_float(raw: str, col_name: str):
    text = raw.replace("R$", "").replace("r$", "").strip().replace(" ", "")
    if "," in text and "." in text:  # formato brasileiro: 1.234,56
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        raise RowError(f"campo '{col_name}': '{raw}' não é um número válido (ex.: 850.00 ou 850,00)")


def _coerce_bool(raw: str, col_name: str):
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise RowError(f"campo '{col_name}': '{raw}' não é um booleano válido (use sim/nao, true/false ou 1/0)")


def _coerce_date(raw: str, col_name: str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise RowError(f"campo '{col_name}': '{raw}' não é uma data válida (use AAAA-MM-DD ou DD/MM/AAAA)")


def _coerce_list(raw: str, col_name: str):
    items = [part.strip() for part in re.split(r"[|;]", raw) if part.strip()]
    if not items:
        raise RowError(f"campo '{col_name}': informe ao menos um item (separe com | ou ;)")
    return items


_COERCERS = {
    "int": _coerce_int,
    "float": _coerce_float,
    "bool": _coerce_bool,
    "date": _coerce_date,
    "list": _coerce_list,
}


def hydrate_row(spec: ImporterSpec, header_set: set, row: Dict[str, str]) -> Dict[str, object]:
    """Converte uma linha da planilha em kwargs do model, validando tipos e obrigatoriedade."""
    data: Dict[str, object] = {}
    for col in spec.columns:
        if col.name not in header_set:
            continue
        raw = row.get(col.name)
        if raw is None or not str(raw).strip():
            if col.required:
                raise RowError(f"campo obrigatório '{col.name}' vazio")
            continue  # célula vazia em coluna opcional não altera o valor existente
        if col.kind == "str":
            data[col.name] = str(raw).strip()
        else:
            data[col.name] = _COERCERS[col.kind](str(raw), col.name)

    if spec.extra_validate:
        spec.extra_validate(data)
    return data


# ---------------------------------------------------------------------------
# Validações extras por recurso
# ---------------------------------------------------------------------------

_CATEGORY_VALUES = {"all", "national", "international"}
_CATEGORY_ALIASES = {"geral": "all", "todos": "all", "nacional": "national", "internacional": "international"}
_REGION_VALUES = {"all", "usa", "europe", "south-america", "other"}
_COUPON_CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{3,50}$")


def _validate_destination(data: Dict[str, object]) -> None:
    category = data.get("category")
    if category is not None:
        raw = str(category).strip().lower()
        # aceita tanto o valor ('national') quanto o rótulo amigável ('Nacional')
        normalized = _CATEGORY_ALIASES.get(raw, raw)
        if normalized not in _CATEGORY_VALUES:
            raise RowError(
                f"campo 'category': '{category}' inválido (use all/geral, national/nacional ou international/internacional)"
            )
        data["category"] = normalized


def _validate_flight(data: Dict[str, object]) -> None:
    region = data.get("region")
    if region is not None:
        normalized = str(region).strip().lower().replace(" ", "-")
        if normalized not in _REGION_VALUES:
            raise RowError(
                f"campo 'region': '{region}' inválido (use all, usa, europe, south-america ou other)"
            )
        data["region"] = normalized


def _validate_coupon(data: Dict[str, object]) -> None:
    code = data.get("code")
    if code is not None:
        normalized = str(code).strip().upper()
        if not _COUPON_CODE_PATTERN.match(normalized):
            raise RowError(
                f"campo 'code': '{code}' inválido (3 a 50 caracteres: letras, números, '-' ou '_')"
            )
        data["code"] = normalized
    discount_type = data.get("discount_type")
    if discount_type is not None:
        normalized = str(discount_type).strip().lower()
        if normalized not in ("percent", "fixed"):
            raise RowError(f"campo 'discount_type': '{discount_type}' inválido (use percent ou fixed)")
        data["discount_type"] = normalized


# ---------------------------------------------------------------------------
# Especificações (5 telas do 1º lote)
# ---------------------------------------------------------------------------

HOTELS_SPEC = ImporterSpec(
    resource="hotels",
    label="Hotéis",
    screen="hospedagens",
    model=Hotel,
    columns=[
        Column("id", required=True, example="hotel-rio-copacabana", description="Código único do hotel"),
        Column("name", required=True, example="Hotel Copacabana Palace"),
        Column("city", required=True, example="Rio de Janeiro"),
        Column("state", example="RJ"),
        Column("country", example="Brasil"),
        Column("stars", kind="int", example="5"),
        Column("rating", kind="float", example="9.2"),
        Column("review_count", kind="int", example="1280"),
        Column("review_label", example="Excelente"),
        Column("address", example="Av. Atlântica, 1400"),
        Column("neighborhood", example="Copacabana"),
        Column("description", example="Hotel frente-mar com 5 estrelas..."),
        Column("image_url", required=True, example="https://cdn.zarpouviagens.com.br/hotels/palace.jpg"),
        Column("base_price_per_night", required=True, kind="float", example="850.00"),
        Column("original_price_per_night", kind="float", example="1000.00"),
        Column("discount_percent", kind="int", example="15"),
        Column("max_installments", kind="int", example="12"),
        Column("featured", kind="bool", example="sim"),
        Column("is_active", kind="bool", example="sim"),
        Column("amenities", kind="list", example="Piscina|Wi-Fi|Academia"),
        Column("badges", kind="list", example="Mais Vendido"),
        Column("gallery", kind="list", example="https://img1.jpg|https://img2.jpg"),
    ],
)

DESTINATIONS_SPEC = ImporterSpec(
    resource="destinations",
    label="Destinos",
    screen="destinos",
    model=Destination,
    columns=[
        Column("id", required=True, example="dest-dubai", description="Código único do destino"),
        Column("title", required=True, example="Dubai"),
        Column("country", required=True, example="Emirados Árabes"),
        Column("flag", example="🇦🇪"),
        Column("category", example="international", description="all/geral, national/nacional, international/internacional"),
        Column("tag", example="Exclusivo"),
        Column("description", example="Metrópole futurista no deserto..."),
        Column("starting_price", kind="float", example="7890.00"),
        Column("accommodations_count", kind="int", example="120"),
        Column("link", example="/destinos/dubai"),
        Column("image_url", required=True, example="https://cdn.zarpouviagens.com.br/destinations/dubai.jpg"),
        Column("is_active", kind="bool", example="sim"),
        Column("display_order", kind="int", example="1"),
    ],
)

FLIGHTS_SPEC = ImporterSpec(
    resource="flights",
    label="Passagens",
    screen="passagens",
    model=Flight,
    columns=[
        Column("id", required=True, example="flight-bh-miami", description="Código único da passagem"),
        Column("price", required=True, kind="float", example="4250.00"),
        Column("original_price", kind="float", example="4990.00"),
        Column("discount_percent", kind="int", example="15"),
        Column("max_installments", kind="int", example="12"),
        Column("is_round_trip", kind="bool", example="sim"),
        Column("featured", kind="bool", example="nao"),
        Column("country", example="Estados Unidos"),
        Column("flag", example="🇺🇸"),
        Column("region", example="usa", description="all, usa, europe, south-america ou other"),
        Column("image_url", example="https://cdn.zarpouviagens.com.br/flights/bh-miami.jpg"),
        Column("highlights", kind="list", example="Bagagem despachada|Embraer 190"),
        Column("is_active", kind="bool", example="sim"),
    ],
)

PROMOTIONS_SPEC = ImporterSpec(
    resource="promotions",
    label="Promoções",
    screen="promocoes",
    model=Promotion,
    columns=[
        Column("id", required=True, example="promo-1", description="Código único da promoção"),
        Column("title", required=True, example="Black Friday Zarpou"),
        Column("subtitle", example="Até 40% em hotéis selecionados"),
        Column("badge", example="OFERTA RELÂMPAGO"),
        Column("discount_text", example="Até 40% OFF"),
        Column("image_url", required=True, example="https://cdn.zarpouviagens.com.br/promos/black.jpg"),
        Column("link", required=True, example="/promocoes/black-friday"),
        Column("button_text", example="Aproveitar Oferta"),
        Column("active", kind="bool", example="sim"),
        Column("start_date", kind="date", example="2026-11-20"),
        Column("end_date", kind="date", example="2026-11-30"),
        Column("display_order", kind="int", example="1"),
    ],
)

COUPONS_SPEC = ImporterSpec(
    resource="coupons",
    label="Cupons",
    screen="cupons",
    model=Coupon,
    key_field="code",
    extra_validate=_validate_coupon,
    make_id=lambda data: f"cpn-{uuid.uuid4().hex[:8]}",
    columns=[
        Column("code", required=True, example="BLACK30", description="Código único do cupom (maiúsculas)"),
        Column("description", example="30% OFF na Black Friday"),
        Column("discount_type", example="percent", description="percent ou fixed"),
        Column("discount_value", required=True, kind="float", example="30"),
        Column("min_order_amount", kind="float", example="500.00"),
        Column("max_uses", kind="int", example="100"),
        Column("per_customer_limit", kind="int", example="1"),
        Column("valid_from", kind="date", example="2026-11-20"),
        Column("valid_to", kind="date", example="2026-11-30"),
        Column("active", kind="bool", example="sim"),
    ],
)

# Aplica validação extra nos destinos (fora da construção direta para manter a spec acima legível)
DESTINATIONS_SPEC.extra_validate = _validate_destination

IMPORTERS: Dict[str, ImporterSpec] = {
    spec.resource: spec
    for spec in (HOTELS_SPEC, DESTINATIONS_SPEC, FLIGHTS_SPEC, PROMOTIONS_SPEC, COUPONS_SPEC)
}


def get_importer(resource: str) -> Optional[ImporterSpec]:
    return IMPORTERS.get(resource)

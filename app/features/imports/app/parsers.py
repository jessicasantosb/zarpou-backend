"""
Parsers de arquivo para importação em massa (CSV e XLSX).

Converte bytes de planilha em linhas-dicionário normalizadas, com cabeçalhos
padronizados (minúsculas, sem acentos, snake_case) para o mapeamento de
colunas ser estável independente do formato enviado pelo usuário.
"""
import csv
import io
import unicodedata
from typing import Dict, List, Tuple


class ParseError(Exception):
    """Arquivo ilegível ou em formato inesperado."""


def normalize_header(header: str) -> str:
    """'Preço Noite' -> 'preco_noite'."""
    text = unicodedata.normalize("NFKD", (header or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text)
    return "_".join(cleaned.split())


def _is_empty_row(row: Dict[str, object]) -> bool:
    return not any(str(value).strip() for value in row.values() if value is not None)


def parse_csv_bytes(data: bytes) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    """Retorna (headers_normalizados, [(n_linha, {coluna: valor})]). Linha 1 = cabeçalho."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ParseError("Não foi possível decodificar o arquivo CSV (use UTF-8 ou Latin-1).") from exc

    reader = None
    try:
        # Delimitador variável: ',' (padrão) ou ';' / tab (padrão do Excel PT-BR)
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
        reader = csv.reader(io.StringIO(text), dialect)
    except csv.Error:
        reader = csv.reader(io.StringIO(text))
    try:
        raw_headers = next(reader)
    except StopIteration:
        raise ParseError("O arquivo CSV está vazio.")

    headers = [normalize_header(h) for h in raw_headers]
    if not any(headers):
        raise ParseError("O arquivo CSV não possui cabeçalho (primeira linha em branco).")

    rows: List[Tuple[int, Dict[str, str]]] = []
    for offset, raw_row in enumerate(reader):
        row_number = offset + 2  # 1 é o cabeçalho
        if len(raw_row) < len(headers):
            raw_row = raw_row + [""] * (len(headers) - len(raw_row))
        row = {headers[i]: (raw_row[i] or "").strip() for i in range(len(headers))}
        if _is_empty_row(row):
            continue
        rows.append((row_number, row))
    return headers, rows


def parse_xlsx_bytes(data: bytes) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    """Parse de planilha .xlsx (primeira aba). Mesmo contrato do parse_csv_bytes."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - dependência declarada no requirements
        raise ParseError("Suporte a Excel requer a biblioteca openpyxl.") from exc

    try:
        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ParseError(f"Arquivo .xlsx inválido ou corrompido: {exc}") from exc

    try:
        sheet = workbook.worksheets[0]
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            raw_headers = next(rows_iter)
        except StopIteration:
            raise ParseError("A planilha está vazia.")

        headers = [normalize_header(str(h) if h is not None else "") for h in (raw_headers or [])]
        if not any(headers):
            raise ParseError("A planilha não possui cabeçalho (primeira linha em branco).")

        rows: List[Tuple[int, Dict[str, str]]] = []
        for offset, raw_row in enumerate(rows_iter):
            row_number = offset + 2
            values = list(raw_row or [])
            if len(values) < len(headers):
                values = values + [None] * (len(headers) - len(values))
            row = {
                headers[i]: ("" if values[i] is None else str(values[i]).strip())
                for i in range(len(headers))
            }
            if _is_empty_row(row):
                continue
            rows.append((row_number, row))
        return headers, rows
    finally:
        workbook.close()


def parse_import_file(filename: str, data: bytes) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    """Despacha pelo tipo de arquivo (extensão) e valida limites básicos."""
    lowered = (filename or "").lower()
    if lowered.endswith(".csv"):
        return parse_csv_bytes(data)
    if lowered.endswith(".xlsx"):
        return parse_xlsx_bytes(data)
    raise ParseError("Formato não suportado. Envie um arquivo .csv ou .xlsx.")


def build_template_csv(columns) -> bytes:
    """Gera template CSV (cabeçalhos + 1 linha de exemplo) para download no painel."""
    header_line = ";".join(col.name for col in columns)
    example_line = ";".join(col.example for col in columns)
    content = f"{header_line}\n{example_line}\n"
    return content.encode("utf-8-sig")  # BOM para o Excel abrir acentos corretamente


def build_template_xlsx(columns):
    """Gera template .xlsx (openpyxl workbook) com cabeçalhos + linha de exemplo."""
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "importacao"
    sheet.append([col.name for col in columns])
    sheet.append([col.example for col in columns])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

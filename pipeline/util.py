"""Мелкие помощники: чтение заголовков по имени, нормализация месяца."""
import datetime as _dt
import openpyxl, warnings
warnings.simplefilter("ignore")


def load(path, sheet, data_only=True):
    wb = openpyxl.load_workbook(path, data_only=data_only, read_only=False)
    return wb[sheet]


def header_index(ws, header_row=1):
    """{'Заголовок': индекс_столбца(0-based)} — читаем по имени, не по позиции."""
    idx = {}
    for i, c in enumerate(ws[header_row]):
        v = c.value
        if v is not None and str(v).strip():
            idx[str(v).strip()] = i
    return idx


def ym(v):
    """Любое представление месяца -> 'YYYY-MM' или None."""
    if v is None:
        return None
    if isinstance(v, (_dt.datetime, _dt.date)):
        return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip()
    if len(s) >= 7 and s[4] == "-" and s[:4].isdigit():
        return s[:7]
    return None


def in_range(m, frm, to):
    return m is not None and frm <= m <= to


def num(v):
    return v if isinstance(v, (int, float)) else 0.0

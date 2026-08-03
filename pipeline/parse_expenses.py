"""Файл 2 «Доходы-расходы 2023-26» — прочие/постоянные расходы, налоги, НДС, ФОТ менеджеров.
Оплату/премии исполнителям отсюда НЕ берём (антидубль, они в файле 3)."""
from collections import defaultdict
from . import config as C
from .util import load, header_index, ym, num


class ExpenseData:
    def __init__(self):
        # display -> month -> amount  (по классификации: variable/fixed идут в P&L-строки)
        self.var_month = defaultdict(lambda: defaultdict(float))
        self.fixed_month = defaultdict(lambda: defaultdict(float))
        self.tax_month = defaultdict(float)      # налоги на деятельность (по месяцу)
        self.vat_month = defaultdict(float)      # НДС оплаченный
        self.mgr_month = defaultdict(lambda: defaultdict(float))  # month -> {оклад,премия,добавка,ИТОГО}
        self._articles = set()
        self.txns = []   # выплаты: {ym, date, what, sum, disp, obj}

    # --- доступ ---
    def _sum(self, table, frm, to):
        out = defaultdict(float)
        for disp, months in table.items():
            for m, v in months.items():
                if frm <= m <= to:
                    out[disp] += v
        return out

    def variables(self, frm, to):  return dict(self._sum(self.var_month, frm, to))
    def fixed(self, frm, to):      return dict(self._sum(self.fixed_month, frm, to))
    def articles(self):           return sorted(self._articles)

    def article(self, frm, to, display):
        t = self.var_month.get(display) or self.fixed_month.get(display) or {}
        return sum(v for m, v in t.items() if frm <= m <= to)

    def tax_activity(self, frm, to):
        return sum(v for m, v in self.tax_month.items() if frm <= m <= to)

    def vat_paid(self, frm, to):
        return sum(v for m, v in self.vat_month.items() if frm <= m <= to)

    def managers(self, frm, to):
        out = {"оклад": 0.0, "премия": 0.0, "добавка": 0.0, "ИТОГО": 0.0}
        for m, d in self.mgr_month.items():
            if frm <= m <= to:
                for k in out:
                    out[k] += d.get(k, 0.0)
        return out

    def unmapped_bucket_name(self):
        return C.UNMAPPED_BUCKET


def parse_expenses(path=None, sheet=None):
    path = path or C.EXPENSES_XLSX
    sheet = sheet or C.SHEET_EXPENSES_2026
    d = ExpenseData()

    # РАСХОДы: B Месяц | C Расход | E Статья расхода | F Объект (шапка в строке 2)
    ws = load(path, sheet)
    # шапка может быть в строке 1 (2023-2025) или 2 (2026, строка 1 — баннер)
    h = header_index(ws, 2)
    if "Статья расхода" not in h:
        h = header_index(ws, 1); start = 2
    else:
        start = 3
    im, isum, iart, iwhat = h.get("Месяц"), h.get("Расход"), h.get("Статья расхода"), h.get("На что")
    idate, iobj = h.get("дата"), h.get("Объект")
    def add_txn(m, row, s, disp):
        d.txns.append({
            "ym": m,
            "date": str(row[idate])[:10] if idate is not None and row[idate] else m,
            "what": str(row[iwhat]) if iwhat is not None and row[iwhat] else "",
            "sum": s, "disp": disp,
            "obj": str(row[iobj]).strip() if iobj is not None and row[iobj] else "",
        })
    for row in ws.iter_rows(min_row=start, values_only=True):
        m = ym(row[im]) if im is not None else None
        s = num(row[isum]) if isum is not None else 0.0
        if not m or not s:
            continue
        art = str(row[iart]).strip() if iart is not None and row[iart] else ""
        what = str(row[iwhat]).lower() if iwhat is not None and row[iwhat] else ""
        d._articles.add(art)
        # Любая строка с «НДС» в назначении -> НДС оплаченный (даже если статья «Налоги»)
        if "ндс" in what:
            d.vat_month[m] += s
            add_txn(m, row, s, "Справочно: НДС оплаченный (факт)")
            continue
        kind, disp = C.classify(art)
        if kind == "variable":
            d.var_month[disp][m] += s; add_txn(m, row, s, disp)
        elif kind == "fixed":
            d.fixed_month[disp][m] += s; add_txn(m, row, s, disp)
        elif kind == "tax":
            d.tax_month[m] += s; add_txn(m, row, s, "Налоги на деятельность (факт)")
        elif kind == "vat":
            d.vat_month[m] += s; add_txn(m, row, s, "Справочно: НДС оплаченный (факт)")
        # excluded -> пропускаем (берём из файла 3)

    # ФОТ менеджеров из File B «ПРЕМИИ менеджеров»: Месяц | Оклад | Премия | Добавка | ИТОГО (шапка стр. 1)
    ws = load(C.MANAGERS_XLSX, C.SHEET_MANAGERS)
    h = header_index(ws, 1)
    im = h.get("Месяц")
    cols = {"оклад": h.get("Оклад"), "премия": h.get("Премия"),
            "добавка": h.get("Добавка"), "ИТОГО": h.get("ИТОГО")}
    isotr = h.get("Сотрудник")
    for row in ws.iter_rows(min_row=2, values_only=True):
        m = ym(row[im]) if im is not None else None
        if not m:
            continue
        for k, ci in cols.items():
            if ci is not None:
                d.mgr_month[m][k] += num(row[ci])
        # выплата по каждому менеджеру (для проваливания в ФОТ)
        itg = num(row[cols["ИТОГО"]]) if cols["ИТОГО"] is not None else 0.0
        if itg:
            d.txns.append({"ym": m, "date": m,
                           "what": str(row[isotr]).strip() if isotr is not None and row[isotr] else "менеджер",
                           "sum": itg, "disp": "ФОТ менеджеров", "obj": "",
                           "оклад": num(row[cols["оклад"]]) if cols["оклад"] is not None else 0.0,
                           "премия": num(row[cols["премия"]]) if cols["премия"] is not None else 0.0,
                           "добавка": num(row[cols["добавка"]]) if cols["добавка"] is not None else 0.0})

    return d

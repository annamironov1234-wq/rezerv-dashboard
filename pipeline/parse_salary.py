"""Файл 3 «ПРЕМИЯ для заполнения» — ФАКТ оплаты рабочим.
Листы: «Зарплата исполнителям» (наличка/самозанятые), «Премия new», «Бригадирские new».
Все три с графой Объект -> раскладывается по объектам."""
from collections import defaultdict
from . import config as C
from .util import load, header_index, ym, num


DISP = {"наличка": "Наличка (рабочие)", "самозанятые": "Самозанятые (рабочие)",
        "премии": "Премии исполнителям", "бригадирские": "Бригадирские"}


class SalaryData:
    def __init__(self):
        # kind -> month -> amount ; kind in {наличка,самозанятые,премии,бригадирские}
        self.by_kind_month = defaultdict(lambda: defaultdict(float))
        # kind -> obj -> month -> amount
        self.by_kind_obj_month = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        self.txns = []   # выплаты: {ym, date, what, sum, disp, obj}

    def _add(self, kind, month, obj, amount, date=None, what=""):
        if not month:
            return
        self.by_kind_month[kind][month] += amount
        self.by_kind_obj_month[kind][obj or "—"][month] += amount
        self.txns.append({"ym": month, "date": str(date)[:10] if date else month,
                          "what": what or DISP[kind], "sum": amount,
                          "disp": DISP[kind], "obj": str(obj).strip() if obj else ""})

    def total(self, frm, to, kind, ip=None):
        if not ip or ip == "Все":
            return sum(v for m, v in self.by_kind_month[kind].items() if frm <= m <= to)
        return sum(v for obj, months in self.by_kind_obj_month[kind].items()
                   if C.ip_of(obj) == ip
                   for m, v in months.items() if frm <= m <= to)

    def month_value(self, kind, month, ip=None):
        if not ip or ip == "Все":
            return self.by_kind_month[kind].get(month, 0.0)
        return sum(months.get(month, 0.0) for obj, months in self.by_kind_obj_month[kind].items()
                   if C.ip_of(obj) == ip)

    def objects(self):
        objs = set()
        for kind in self.by_kind_obj_month:
            objs |= set(self.by_kind_obj_month[kind].keys())
        return sorted(objs)


def parse_salary(path=None):
    path = path or C.SALARY_XLSX
    d = SalaryData()

    # Зарплата исполнителям: A Номер месяца | C Дата | D Объект | E Тип выплаты | F Сумма
    ws = load(path, C.SHEET_SALARY)
    h = header_index(ws, 1)
    im, it, isum, io = h.get("Номер месяца"), h.get("Тип выплаты"), h.get("Сумма"), h.get("Объект")
    idt = h.get("Дата выплаты")
    for row in ws.iter_rows(min_row=2, values_only=True):
        m = ym(row[im]) if im is not None else None
        s = num(row[isum]) if isum is not None else 0.0
        if not m or not s:
            continue
        t = str(row[it]).strip().lower() if it is not None and row[it] else ""
        obj = row[io] if io is not None else None
        kind = "самозанятые" if "самозан" in t else "наличка"
        d._add(kind, m, obj, s, date=row[idt] if idt is not None else None)

    # Премия new: B Номер месяца | G ФИО | H Сумма | J Дата выплаты | K Объект
    ws = load(path, C.SHEET_PREMIA)
    h = header_index(ws, 1)
    im, isum, io = h.get("Номер месяца"), h.get("Сумма"), h.get("Объект")
    idt, ifio = h.get("Дата выплаты"), h.get("ФИО")
    for row in ws.iter_rows(min_row=2, values_only=True):
        m = ym(row[im]) if im is not None else None
        s = num(row[isum]) if isum is not None else 0.0
        if not m or not s:
            continue
        d._add("премии", m, row[io] if io is not None else None, s,
               date=row[idt] if idt is not None else None,
               what=("Премия · " + str(row[ifio])) if ifio is not None and row[ifio] else "Премия исполнителю")

    # Бригадирские new: C Номер месяца | D Дата | E Сумма | F Объект
    ws = load(path, C.SHEET_BRIGADIR)
    h = header_index(ws, 1)
    im, isum, io = h.get("Номер месяца"), h.get("Сумма"), h.get("Объект")
    idt = h.get("Дата")
    for row in ws.iter_rows(min_row=2, values_only=True):
        m = ym(row[im]) if im is not None else None
        s = num(row[isum]) if isum is not None else 0.0
        if not m or not s:
            continue
        d._add("бригадирские", m, row[io] if io is not None else None, s,
               date=row[idt] if idt is not None else None)

    return d

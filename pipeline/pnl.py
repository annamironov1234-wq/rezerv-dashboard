"""Движок P&L. Собирает отчёт из трёх парсеров по методологии data-sources.md.
Порядок: Выручка − Переменные = Маржа − Постоянные = EBITDA − Налоги = Чистая.

Фильтр по ИП (Миронов/Молчанов):
  • выручка и оплата рабочим — точно по объектам (объект->ИП);
  • транспорт Олег — ЗетТЕК = Миронов;
  • общие расходы (комиссия платформам, расходники, такси, постоянные, налоги) —
    разносим по доле выручки ИП (Миронов+Молчанов = Всё, суммы сходятся)."""
from .parse_income import parse_income
from .parse_expenses import parse_expenses
from .parse_salary import parse_salary


def months_between(frm, to):
    y, m = int(frm[:4]), int(frm[5:7])
    ty, tm = int(to[:4]), int(to[5:7])
    out = []
    while (y, m) <= (ty, tm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


class PnL:
    def __init__(self, inc, exp, sal, frm, to, ip="Все"):
        self.frm, self.to, self.ip = frm, to, ip
        self.months = months_between(frm, to)
        self._inc, self._exp, self._sal = inc, exp, sal
        # доля выручки ИП (для разнесения общих расходов)
        rev_total = inc.revenue(frm, to)
        rev_ip = inc.revenue(frm, to, ip=ip)
        self.share = 1.0 if ip == "Все" else (rev_ip / rev_total if rev_total else 0.0)
        self._build()

    def _row(self, name, month_fn):
        vals = {m: month_fn(m) for m in self.months}
        return {"name": name, "months": vals, "total": sum(vals.values())}

    def _build(self):
        inc, exp, sal, ip, k = self._inc, self._exp, self._sal, self.ip, self.share
        alloc = ip != "Все"          # разносить ли общие по доле
        has_transport = ip in ("Все", "Миронов")   # транспорт Олег = ЗетТЕК = Миронов

        # ВЫРУЧКА
        rev_m = inc.revenue_by_month(self.frm, self.to, ip=ip)
        self.revenue_row = self._row("ВЫРУЧКА без НДС", lambda m: rev_m.get(m, 0.0))
        self.revenue = self.revenue_row["total"]

        # ПЕРЕМЕННЫЕ
        def var_common(disp, m):   # общая переменная статья из файла 2 (по доле)
            v = exp.var_month.get(disp, {}).get(m, 0.0)
            return v * k if alloc else v
        self.var_rows = [
            self._row("Наличка (рабочие)", lambda m: sal.month_value("наличка", m, ip)),
            self._row("Самозанятые (рабочие)", lambda m: sal.month_value("самозанятые", m, ip)),
            self._row("Премии исполнителям", lambda m: sal.month_value("премии", m, ip)),
            self._row("Бригадирские", lambda m: sal.month_value("бригадирские", m, ip)),
            self._row("Комиссия платформам (СЗ)", lambda m: var_common("Комиссия платформам (СЗ)", m)),
            self._row("Транспорт Олег", lambda m: inc.transport_month.get(m, 0.0) if has_transport else 0.0),
            self._row("Расходники на персонал", lambda m: var_common("Расходники на персонал", m)),
            self._row("Транспорт такси", lambda m: var_common("Транспорт такси", m)),
        ]
        self.variable = sum(r["total"] for r in self.var_rows)
        self.workers_fact = sum(r["total"] for r in self.var_rows[:4])

        self.margin = self.revenue - self.variable
        self.margin_pct = (self.margin / self.revenue) if self.revenue else 0.0

        # ПОСТОЯННЫЕ (все по доле при фильтре)
        def scale(v):
            return v * k if alloc else v
        mgr = {m: scale(exp.mgr_month.get(m, {}).get("ИТОГО", 0.0)) for m in self.months}
        self.fixed_rows = [{"name": "ФОТ менеджеров",
                            "months": mgr, "total": sum(mgr.values())}]
        for disp, months in sorted(exp.fixed_month.items()):
            self.fixed_rows.append(self._row(disp, lambda m, mm=months: scale(mm.get(m, 0.0))))
        self.fixed = sum(r["total"] for r in self.fixed_rows)

        self.ebitda = self.margin - self.fixed

        # НАЛОГИ на деятельность — ФАКТ по месяцам (по доле при фильтре)
        self.tax_row = self._row("Налоги на деятельность (факт)",
                                  lambda m: scale(exp.tax_month.get(m, 0.0)))
        self.tax_total = self.tax_row["total"]

        self.net = self.ebitda - self.tax_total

        # НДС: расчётный (начислен 5% с выручки) и фактически оплаченный
        self.vat_charged_row = self._row("Справочно: НДС начисленный (5% с выручки)",
                                         lambda m: rev_m.get(m, 0.0) * 0.05)
        self.vat_row = self._row("Справочно: НДС оплаченный (факт)",
                                 lambda m: scale(exp.vat_month.get(m, 0.0)))

    def to_dict(self):
        return {
            "ip": self.ip,
            "period": [self.frm, self.to],
            "months": self.months,
            "revenue": self.revenue_row,
            "variables": self.var_rows,
            "variable_total": self.variable,
            "margin": self.margin,
            "margin_pct": self.margin_pct,
            "fixed": self.fixed_rows,
            "fixed_total": self.fixed,
            "ebitda": self.ebitda,
            "tax": self.tax_row,
            "net": self.net,
            "vat_charged": self.vat_charged_row,
            "vat": self.vat_row,
        }


def build_pnl(period=("2026-01", "2026-06"), ip="Все", obj=None,
              inc=None, exp=None, sal=None):
    inc = inc or parse_income()
    exp = exp or parse_expenses()
    sal = sal or parse_salary()
    return PnL(inc, exp, sal, period[0], period[1], ip=ip)

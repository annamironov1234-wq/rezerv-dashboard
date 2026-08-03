"""Точка входа: собрать P&L -> build/data.json + метка времени + сверка.
Запуск: python -m dashboard.pipeline.build (из корня клиента) или python -m pipeline.build."""
import json, datetime, sys
from pathlib import Path
from .pnl import build_pnl
from .parse_income import parse_income
from .parse_expenses import parse_expenses
from .parse_salary import parse_salary
from . import config as C

CONTROL_REVENUE_JANJUN = 130312854   # контроль сверки (метод согласован)
OUT = C.DASH / "build" / "data.json"


def main():
    inc, exp, sal = parse_income(), parse_expenses(), parse_salary()
    MSK = datetime.timezone(datetime.timedelta(hours=3))
    now = datetime.datetime.now(MSK)                    # московское время (GitHub работает в UTC)
    cur_month = f"{now.year:04d}-{now.month:02d}"      # текущий (идущий) месяц
    per = ("2026-01", cur_month)                        # период до текущего месяца включительно

    # ВЫРУЧКА — гибрид:
    #   • янв–июнь (закрытые, контроль 130 312 854) — «Сумма услуг» по счетам;
    #   • июль и свежее — «Итого за рабочих» по ФАКТИЧЕСКИМ датам работы,
    #     иначе счёт по «Дата услуг ОТ» захватывает работу следующего месяца
    #     (напр. июль ЗетТЕК тянул 1–2 августа) и свежие месяцы недосчитаны (счёт ещё не выставлен).
    CUTOFF = "2026-06"
    for obj in set(inc.rev_obj_month) | set(inc.workcost_obj_month):
        mm = inc.rev_obj_month[obj]
        for m in [k for k in mm if k > CUTOFF]:
            del mm[m]                                    # убрать счётные значения свежих месяцев
        for m, v in inc.workcost_obj_month.get(obj, {}).items():
            if m > CUTOFF and v:
                mm[m] = v                                # проставить фактически наработанное по датам
    pnl = {ip: build_pnl(period=per, ip=ip, inc=inc, exp=exp, sal=sal)
           for ip in ("Все", "Миронов", "Молчанов")}
    p = pnl["Все"]

    # --- сверка: янв–июн должны остаться = 130 312 854 (инвариант независимо от июля) ---
    janjun = inc.revenue("2026-01", "2026-06")
    diff = round(janjun) - CONTROL_REVENUE_JANJUN
    reconciled = (diff == 0)
    if not reconciled:
        print(f"[СВЕРКА] Выручка янв–июн {janjun:,.0f} != контроль {CONTROL_REVENUE_JANJUN:,.0f} (разница {diff:,.0f})",
              file=sys.stderr)

    # --- авто-заглушки: система сама себя охраняет (чтобы Анне не держать это в голове) ---
    warnings = []
    clients = getattr(inc, "client_objects", [])
    active_clients = []
    for o in clients:
        rev_o = inc.revenue(per[0], per[1], obj=o)   # выручка объекта за период
        if rev_o <= 0:
            continue                                   # пустой/архивный/будущий лист — не тревожим
        active_clients.append(o)
        if o not in C.KNOWN_OBJECTS:
            warnings.append(f"Новый клиент «{o}» (выручка {rev_o:,.0f} ₽) — включён в расчёт, ИП по файлу: "
                            f"«{C.ip_of(o)}». Скажите Клоду, чтобы проверить настройки объекта (зарплата, транспорт).")
    if not active_clients:
        warnings.append("Не найдено ни одного листа-клиента в таблице — возможно, изменилась структура "
                        "или сменился год в названиях листов. Нужна проверка.")

    # напоминание про новый файл на новый год: данные отстают от текущего года
    data_years = {m[:4] for o in inc.rev_obj_month.values() for m, v in o.items() if v}
    max_year = max(data_years) if data_years else str(now.year)
    if int(max_year) < now.year:
        warnings.append(f"Начался {now.year} год, а свежих данных за {now.year} в таблице нет "
                        f"(последние — за {max_year}). Похоже, нужен новый файл-источник выручки на {now.year}. "
                        f"Напишите Клоду — подключим и обновим правила.")
    if not reconciled:
        warnings.append(f"Контроль янв–июн не сошёлся: {janjun:,.0f} вместо {CONTROL_REVENUE_JANJUN:,.0f}. "
                        f"Похоже, поменялась структура таблицы — цифрам пока не доверять, нужна проверка.")
    for w in warnings:
        print("[ЗАГЛУШКА] " + w, file=sys.stderr)

    # выручка по объектам (янв–июн) для графика и фильтра «по клиентам»
    rev_by_obj, rev_obj_monthly = [], {}
    months = p.months
    for o, mm in inc.rev_obj_month.items():
        t = sum(v for m, v in mm.items() if "2026-01" <= m <= "2026-06")
        if t:
            rev_by_obj.append({"obj": o, "total": t, "ip": C.ip_of(o)})
            rev_obj_monthly[o] = {m: mm.get(m, 0.0) for m in months}
    rev_by_obj.sort(key=lambda x: -x["total"])

    # выплаты по статьям (для страницы «Расходы — детализация»)
    from collections import defaultdict
    txns_by_disp = defaultdict(list)
    for t in (exp.txns + sal.txns):
        if per[0] <= t["ym"] <= per[1]:
            txns_by_disp[t["disp"]].append(t)
    for k in txns_by_disp:
        txns_by_disp[k].sort(key=lambda x: x["date"])

    # ФОТ менеджеров по месяцам (оклад/премия/добавка) — для раскрытия
    managers_month = {m: {k: v for k, v in dd.items()} for m, dd in exp.mgr_month.items()}

    # оплата рабочим по объектам выручки (для P&L по объектам): {rev_obj:{kind:{month:v}}}
    worker_obj = {}
    for kind, objs in sal.by_kind_obj_month.items():
        for so, mm in objs.items():
            rev = C.salary_obj_to_rev(so)
            if not rev:
                continue
            k = worker_obj.setdefault(rev, {}).setdefault(kind, {})
            for m, v in mm.items():
                if per[0] <= m <= per[1]:
                    k[m] = k.get(m, 0.0) + v

    data = {
        "updated_at": now.strftime("%d.%m.%Y %H:%M") + " МСК",
        "incomplete_month": cur_month,     # текущий месяц — неполный, подсветить
        "expense_txns": txns_by_disp,
        "managers_month": managers_month,
        "reconciled": reconciled,
        "warnings": warnings,
        "known_clients": sorted(active_clients),
        "control_revenue": CONTROL_REVENUE_JANJUN,
        "unit": "тыс ₽",
        "pnl": {ip: pnl[ip].to_dict() for ip in pnl},
        "pnl_all": p.to_dict(),
        "objects": [r["obj"] for r in rev_by_obj],
        "revenue_by_object": rev_by_obj,
        "revenue_obj_monthly": rev_obj_monthly,
        "worker_obj_monthly": worker_obj,
        "transport_obj_monthly": {o: {m: v for m, v in mm.items() if per[0] <= m <= per[1]}
                                  for o, mm in inc.transport_obj_month.items()},
        "hours_obj_monthly": {o: {m: v for m, v in mm.items() if per[0] <= m <= per[1]}
                              for o, mm in inc.hours_obj_month.items()},
        "workcost_obj_monthly": {o: {m: v for m, v in mm.items() if per[0] <= m <= per[1]}
                                 for o, mm in inc.workcost_obj_month.items()},
        "rates_obj": {o: {sm: {m: {"cr": c[0]/c[2], "wr": (c[1]/c[2] if c[1] else 0), "hrs": c[2]}
                               for m, c in mm.items() if per[0] <= m <= per[1] and c[2]}
                          for sm, mm in sms.items()}
                      for o, sms in inc.rates.items()},
        "receivables": [{**r, "ip": C.ip_of(r["obj"])} for r in inc.receivables],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK -> {OUT}")
    print(f"   Выручка {p.revenue:,.0f} | Маржа {p.margin:,.0f} ({p.margin_pct:.1%}) | "
          f"EBITDA {p.ebitda:,.0f} | Чистая {p.net:,.0f} | сверка: {'OK' if reconciled else 'РАСХОЖДЕНИЕ'}")


if __name__ == "__main__":
    main()

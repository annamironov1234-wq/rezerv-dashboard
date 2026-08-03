"""Конфиг источников и правил P&L. Единственное место, где живут пути,
имена листов, маппинг статей и классификация. Меняем таблицы -> правим здесь
(и методологию docs/data-sources.md), логика дашборда не трогается."""
from pathlib import Path

# Пути самодостаточны от папки dashboard/ (чтобы её можно было деплоить репозиторием).
DASH = Path(__file__).resolve().parents[1]      # …/dashboard
CLIENT_ROOT = DASH                               # (совместимость; всё живёт внутри dashboard)
RAW = DASH / "data" / "raw"

# --- Локальные выгрузки (дев-режим). На деплое заменяются пуллингом из Google. ---
INCOME_XLSX   = RAW / "SS.2026.Tablicy.xlsx"
EXPENSES_XLSX = RAW / "expenses" / "Dohody-rashody-2023-26.NEW.xlsx"
SALARY_XLSX   = RAW / "expenses" / "Premiya-dlya-zapolneniya.NEW.xlsx"

# --- Google file id (для авто-пуллинга) ---
GOOGLE_IDS = {
    "income_2026":  "18FBXfBrXiufoj775HgawprM3mWkWeIaPVHVoyZauLkM",
    "income_2025":  "1i4_rluZqzjfpjaVM7ku6OVlqq7oEWkftMtoSLIaxxf4",
    # МАСТЕР (владелец rezervsil40, живой). НЕ датированные копии 1TQ…/1VJ7… — те пересоздаются ежедневно.
    "expenses":     "1zt4yzQ8VYEGoRKCRQpg2TXMebQw7tOXIWzqqL_QG9S0",
    "salary":       "1kbtAsamfQep0KndhvnunrjN6ByjiIVTps324Z7yiHi0",
}

# --- Листы ---
SHEET_EXPENSES_2026 = "РАСХОДы 2026"
SHEET_EXPENSES_2025 = "Расходы 2023-2025"
# ФОТ менеджеров берём из File B «ПРЕМИИ менеджеров» (столбец ИТОГО), НЕ из File A.
MANAGERS_XLSX       = SALARY_XLSX
SHEET_MANAGERS      = "ПРЕМИИ менеджеров"
SHEET_SALARY        = "Зарплата исполнителям"
SHEET_PREMIA        = "Премия new"
SHEET_BRIGADIR      = "Бригадирские new"

UNMAPPED_BUCKET = "Прочее/неразнесённое"

# --- Классификация статей файла 2 «РАСХОДы» ---
# kind: variable | fixed | tax | vat | excluded
# Оплата/премии/бригадирские рабочим берём из файла 3 -> из файла 2 excluded (антидубль).
ARTICLE_MAP = {
    "Комиссия платформа самозанятые": ("variable", "Комиссия платформам (СЗ)"),
    "Расходы на персонал (расходники)": ("variable", "Расходники на персонал"),
    "Транспорт такси":                ("variable", "Транспорт такси"),
    "Банковские расходы":             ("fixed", "Банковские расходы"),
    "Налоги самозанятые":             ("fixed", "Налоги самозанятые"),
    "Бухгалтерия/консультанты":       ("fixed", "Бухгалтерия/консультанты"),
    "Офисные расходы":                ("fixed", "Офисные расходы"),
    "Мебель, оргтехника":             ("fixed", "Мебель, оргтехника"),
    "Связь (телефония, интернет)":    ("fixed", "Связь"),
    "Прочее":                         ("fixed", "Прочее"),
    "Налоги персонал в штате":        ("fixed", "Налоги персонал в штате"),
    "Расходы на рекламу - сотрудники":("fixed", "Реклама"),
    "Корпоративные мероприятия":      ("fixed", "Корпоративные мероприятия"),
    "Аренда помещения":               ("fixed", "Аренда помещения"),
    "НАЛОГИ  НА ДЕЯТЕЛЬНОСТЬ":         ("tax", "Налоги на деятельность"),
    "НАЛОГИ НА ДЕЯТЕЛЬНОСТЬ":          ("tax", "Налоги на деятельность"),
    "НДС":                            ("vat", "НДС оплаченный"),
    "Зарплата исполнителям":          ("excluded", None),   # берём из файла 3
    "Премия исполнителям":            ("excluded", None),   # берём из файла 3
}

# --- Объект -> ИП (проверено: сходится с контролем Миронов 117,52 / Молчанов 12,79 млн) ---
IP_MOLCHANOV_KEYS = ("элинар", "лоссард", "клемер", "окз")

def ip_of(obj):
    ol = str(obj).lower()
    return "Молчанов" if any(k in ol for k in IP_MOLCHANOV_KEYS) else "Миронов"


# --- Объект зарплат -> объект выручки (подтверждено Анной 03.08) ---
# Ключ — нормализованное имя из файла зарплат; значение — имя объекта в файле выручки.
# Не в списке (Элинар Нара / ПФ Нара, 1МК, «Приведи друга», пусто) — нет объекта-выручки.
SALARY_TO_REV = {
    "зеттек": "ООО ЗетТЕК (26)",
    "кцх": "КЦХ (26)",
    "iq": "OOO IQ (26)",
    "лассард": "ЛОССАРД (26)",
    "лоссард": "ЛОССАРД (26)",
    "офки": "ОФКИ (26)",
    "клемер": "Клемер",
    "окз": "ООО ОКЗ (26)",
    "элинарбелоусовоповара": "ЭЛИНАР-Повара (26)",
}

def _norm_obj(name):
    import re
    return re.sub(r"[^a-zа-яё0-9]", "", str(name).lower())

def salary_obj_to_rev(name):
    """Вернуть имя объекта выручки для объекта из файла зарплат, или None."""
    n = _norm_obj(name)
    if n in SALARY_TO_REV:
        return SALARY_TO_REV[n]
    for k, v in SALARY_TO_REV.items():
        if k in n:
            return v
    return None


def classify(article: str):
    """Вернуть (kind, display). Неизвестная статья -> variable? нет: fixed-неразнесённое,
    чтобы не терялась и попадала в постоянные с явным именем."""
    a = (article or "").strip()
    if a in ARTICLE_MAP:
        return ARTICLE_MAP[a]
    return ("fixed", UNMAPPED_BUCKET)

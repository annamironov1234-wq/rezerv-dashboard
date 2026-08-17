"""Собирает дашборд для Netlify: страница отдельно, цифры отдельно.

Раньше собирался один самодостаточный HTML с вшитыми внутрь цифрами - так было
надо для GitHub Pages, который умеет отдавать только готовые файлы. 17.08.2026
выяснилось, чем это кончается: страница висела в открытом доступе с ФИО
сотрудников, окладами и премиями. Пароль поверх такого файла бесполезен -
данные скачиваются раньше, чем выполнится любая проверка.

Теперь:
    _site/      ТОЛЬКО форма входа и иконки            - отдаётся всем
    private/    сам дашборд и все цифры                - только по пропуску

Сама страница дашборда тоже закрыта. Причина: в неё незаметно попали названия
клиентов - в подсказках «откуда взялась цифра» стояло «(ЗетТЕК/КЦХ/Клемер)».
Вычищать такие места по одному бесполезно, следующая правка занесёт новое.

ВАЖНО: web/index.html не переписывается. Вид дашборда, вёрстка и цифры
остаются ровно такими, какими были. Меняется только доставка.

Запуск: python -m pipeline.publish
"""
import base64, json, shutil
from . import config as C

WEB = C.DASH / "web"
BUILD = C.DASH / "build" / "data.json"
SITE = C.DASH / "_site"
PRIVATE = C.DASH / "private"

FAV = ("<link rel=\"icon\" href=\"data:image/svg+xml,"
       "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
       "<text y='.9em' font-size='88'>%F0%9F%92%B0</text></svg>\">")

# Цифры больше не лежат в странице - она просит их у функции, предъявляя пропуск.
# Не пустили (пропуск кончился или его не было) - уходим на форму входа.
СТАРАЯ_ЗАГРУЗКА = "fetch('../build/data.json').then(r=>r.json())"
НОВАЯ_ЗАГРУЗКА = (
    "fetch('/api/data',{credentials:'same-origin',cache:'no-store'})"
    ".then(r=>{if(r.status===401){location.replace('/');"
    "throw new Error('нужен вход');}"
    "if(!r.ok)throw new Error('сервер ответил '+r.status);return r.json();})"
)

СТАРАЯ_МЕТКА = "fetch('stamp.txt?_='+Date.now(),{cache:'no-store'})"
НОВАЯ_МЕТКА = "fetch('/api/stamp?_='+Date.now(),{cache:'no-store',credentials:'same-origin'})"

# Служебное на страницу входа не тащим, но иконки нужны обеим
ИКОНКИ = ["apple-touch-icon.png", "sw.js"]


def _проверить_замену(html, старое, что):
    """Строка в index.html могла измениться - тогда замена молча не сработает,
    и цифры уедут в открытый доступ ровно так же, как 17.08. Лучше упасть."""
    if старое not in html:
        raise SystemExit(
            f"СТОП: в web/index.html не найдено {что}:\n    {старое}\n"
            f"Значит страницу правили, а publish.py об этом не знает.\n"
            f"Публиковать нельзя: цифры могут уехать без пароля."
        )


def build_html():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    data = BUILD.read_text(encoding="utf-8")

    _проверить_замену(html, СТАРАЯ_ЗАГРУЗКА, "загрузку данных")
    _проверить_замену(html, СТАРАЯ_МЕТКА, "проверку свежести")

    logo = base64.b64encode((WEB / "assets" / "logo.png").read_bytes()).decode()
    html = html.replace('src="assets/logo.png"', f'src="data:image/png;base64,{logo}"')
    html = html.replace("</head>", FAV + "\n</head>", 1)
    html = html.replace(СТАРАЯ_ЗАГРУЗКА, НОВАЯ_ЗАГРУЗКА)
    html = html.replace(СТАРАЯ_МЕТКА, НОВАЯ_МЕТКА)

    # ── Публичная часть: только форма входа ────────────
    # На открытом месте лежит один экран с полем пароля. Больше ничего:
    # ни цифр, ни названий клиентов, ни устройства дашборда.
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(
        (WEB / "login.html").read_text(encoding="utf-8"), encoding="utf-8"
    )
    for имя in ИКОНКИ:
        shutil.copy(WEB / имя, SITE / имя)

    # ── Закрытая часть: сюда статика не смотрит ────────
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "app.html").write_text(html, encoding="utf-8")
    shutil.copy(BUILD, PRIVATE / "data.json")

    stamp = json.loads(data).get("updated_at", "")
    (PRIVATE / "stamp.txt").write_text(stamp, encoding="utf-8")

    mt = C.DASH / "build" / "metrics.json"   # слепок цифр: следующая сборка сравнит с ним
    if mt.exists():
        shutil.copy(mt, PRIVATE / "metrics.json")

    # ── Последняя проверка перед публикацией ───────────
    # Дешевле десяти рассуждений: просто ищем в публичной папке то,
    # чего там быть не должно.
    _ни_одной_цифры_в_публичном()

    return len(html)


def _ни_одной_цифры_в_публичном():
    """Стоп-кран: в открытой папке не должно быть ничего, кроме формы входа.

    Проверки нарочно грубые и без кавычек. Первая версия искала '"оклад"'
    с кавычками и пропустила подсказку с названиями клиентов - слово там
    стояло голым. Лучше лишний раз поругаться, чем ещё раз выложить чужие
    зарплаты в интернет.
    """
    приметы = [
        "window.__DATA__", "оклад", "премия", "счет_ндс",
        # названия заказчиков: их не должно быть на открытой странице
        "ЗетТЕК", "ОКЗ", "ОФКИ", "ЭЛИНАР", "1МК", "КЦХ", "Клемер", "Маржанка",
    ]
    разрешено = {"index.html", "apple-touch-icon.png", "sw.js"}
    беда = []

    for файл in SITE.rglob("*"):
        if not файл.is_file():
            continue
        имя = файл.relative_to(SITE).as_posix()
        if имя not in разрешено:
            беда.append(f"лишний файл в открытой папке: {имя}")
            continue
        if файл.suffix.lower() not in {".html", ".js", ".json", ".txt"}:
            continue
        текст = файл.read_text(encoding="utf-8", errors="ignore")
        for примета in приметы:
            if примета in текст:
                беда.append(f"{имя} содержит «{примета}»")

    if беда:
        raise SystemExit(
            "СТОП: в открытую папку попало лишнее, публикации не будет:\n  "
            + "\n  ".join(беда)
        )


if __name__ == "__main__":
    n = build_html()
    print(f"OK -> {SITE}  (страница {n // 1024} КБ, цифры отдельно в {PRIVATE.name}/)")

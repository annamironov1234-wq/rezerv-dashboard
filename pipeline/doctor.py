"""Диагностика дашборда одной командой: `python3 -m pipeline.doctor`.

Отвечает на один вопрос Анны: «сломалось — а что именно и что делать?»
Ничего не чинит и ничего не публикует, только смотрит и говорит по-русски.

Проверяет всю цепочку от будильника до экрана:
  1. что показывает живой сайт и насколько цифры свежие;
  2. состоялся ли последний запуск обновления и чем кончился;
  3. если упал — на какой именно проверке (достаёт причину из лога);
  4. жив ли внешний будильник (по факту прихода запусков за сутки).
"""
import datetime, json, re, subprocess, sys

REPO = "annamironov1234-wq/rezerv-dashboard"
SITE = "https://annamironov1234-wq.github.io/rezerv-dashboard"
MSK = datetime.timezone(datetime.timedelta(hours=3))
OK, WARN, BAD = "  ✓", "  !", "  ✗"


def _get(url, timeout=25):
    """curl надёжнее urllib: на части сетей urllib рвёт длинный ответ GitHub API."""
    r = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout),
                        "-H", "Cache-Control: no-cache",
                        "-H", "Accept: application/vnd.github+json", url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError((r.stderr or "пустой ответ").strip()[:120])
    return r.stdout


def _msk(iso):
    return datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ") \
        .replace(tzinfo=datetime.timezone.utc).astimezone(MSK)


def main():
    now = datetime.datetime.now(MSK)
    print(f"ДИАГНОСТИКА ДАШБОРДА · {now:%d.%m.%Y %H:%M} МСК\n")
    problems, hours = [], None

    # 1. Живой сайт -------------------------------------------------------
    print("1. Что видит Анна на экране")
    try:
        stamp = _get(SITE + "/stamp.txt").strip()
        t = datetime.datetime.strptime(stamp.replace(" МСК", ""), "%d.%m.%Y %H:%M").replace(tzinfo=MSK)
        hours = (now - t).total_seconds() / 3600
        if hours < 20:
            print(f"{OK} данные на {stamp}, это {hours:.0f} ч назад — свежие")
        else:
            print(f"{BAD} данные на {stamp}, это {hours:.0f} ч назад — УСТАРЕЛИ")
            print(f"      на дашборде сейчас висит жёлтый баннер")
            problems.append("обновление не приходит")
    except Exception as e:
        print(f"{BAD} сайт не отвечает: {e}")
        problems.append("сайт недоступен")

    # 2. Последние запуски ------------------------------------------------
    print("\n2. Запуски обновления (последние 10)")
    runs, runs_ok = [], False
    try:
        runs = json.loads(_get(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=10"))["workflow_runs"]
        runs_ok = True
        for r in runs[:5]:
            when = _msk(r["created_at"])
            mark = OK if r["conclusion"] == "success" else BAD
            src = "будильник" if r["event"] == "workflow_dispatch" else "расписание GitHub"
            print(f"{mark} {when:%d.%m %H:%M} · {src} · {r['conclusion'] or r['status']}")
    except Exception as e:
        print(f"{WARN} не смогла прочитать историю запусков: {e}")

    # 3. Причина падения ---------------------------------------------------
    failed = next((r for r in runs if r["conclusion"] not in ("success", None)), None)
    if failed and runs and runs[0]["conclusion"] != "success":
        print(f"\n3. Последний запуск УПАЛ — ищу причину")
        problems.append("сборка не проходит проверки")
        try:
            log = subprocess.run(["gh", "run", "view", str(failed["id"]), "--log-failed"],
                                 capture_output=True, text=True, timeout=90).stdout
            hit = [re.sub(r"^\S+Z\s+", "", l.split("\t")[-1].strip())     # убрать метку времени
                   for l in log.splitlines()
                   if "ПРОВЕРКА НЕ ПРОШЛА" in l or "  • " in l]
            if hit:
                print("   Проверки, которые не прошли:")
                for h in hit[:12]:
                    print("   " + h)
                print("\n   Это значит: цифры признаны недостоверными и НЕ опубликованы.")
                print("   На сайте остались прошлые верные данные. Так и задумано.")
            else:
                print(f"   Причина в логе: {failed['html_url']}")
        except FileNotFoundError:
            print(f"   Смотреть лог: {failed['html_url']}")
        except Exception as e:
            print(f"   Лог не достался ({e}): {failed['html_url']}")
    else:
        print("\n3. Причина падения: последний запуск прошёл успешно, разбирать нечего")

    # 4. Жив ли будильник --------------------------------------------------
    print("\n4. Внешний будильник (cron-job.org)")
    day_ago = now - datetime.timedelta(hours=26)
    fired = [r for r in runs if r["event"] == "workflow_dispatch" and _msk(r["created_at"]) > day_ago]
    if not runs_ok:
        # историю не прочитали — молчим. Диагност не имеет права поднимать ложную тревогу.
        print(f"{WARN} не смогла проверить: история запусков не прочиталась")
    elif fired:
        print(f"{OK} за сутки пришло запусков: {len(fired)} (ждём 2: 07:40 и 19:40)")
    else:
        print(f"{BAD} за сутки НИ ОДНОГО запуска от будильника")
        print("      значит умер он, а не дашборд. Токен истёк или задача выключена.")
        problems.append("будильник не звонит")

    # Вердикт ---------------------------------------------------------------
    print("\n" + "=" * 62)
    if not problems:
        print("ВСЁ ИСПРАВНО. Цифрам можно верить, делать ничего не нужно.")
    else:
        print("ЧТО СЛОМАНО: " + "; ".join(problems))
        print("\nЧТО ДЕЛАТЬ:")
        if "будильник не звонит" in problems:
            print("  • открыть console.cron-job.org, посмотреть историю задачи;")
            print("    ответ 401 значит истёк токен — инструкция в docs/автообновление.md")
        if "сборка не проходит проверки" in problems:
            print("  • это разбор данных, не расписание. Напишите Клоду и покажите")
            print("    список непрошедших проверок выше — он объяснит и починит.")
        if "сайт недоступен" in problems:
            print("  • проверьте интернет; если он есть, напишите Клоду.")
        print("\n  Обновить руками прямо сейчас: gh workflow run refresh.yml")
        print(f"  или кнопкой на https://github.com/{REPO}/actions")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

"""Тянет свежие Google-таблицы роботом (сервис-аккаунт) в data/raw/.
Ключ: dashboard/.secrets/sa.json (локально) или переменная GOOGLE_SA_JSON (в CI).
Запуск: python -m dashboard.pipeline.gsync"""
import os, io, json, time, urllib.parse
from google.oauth2 import service_account
import google.auth.transport.requests as gt
import requests
from . import config as C

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SA_FILE = C.DASH / ".secrets" / "sa.json"

# какой Google-файл -> в какой локальный xlsx
TARGETS = {
    "income_2026": C.INCOME_XLSX,
    "expenses":    C.EXPENSES_XLSX,
    "salary":      C.SALARY_XLSX,
}


def _creds():
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    env = os.environ.get("GOOGLE_SA_JSON")
    if env:
        return service_account.Credentials.from_service_account_info(json.loads(env), scopes=scopes)
    return service_account.Credentials.from_service_account_file(str(SA_FILE), scopes=scopes)


def _download(token, fid, dest, retries=6):
    url = f"https://www.googleapis.com/drive/v3/files/{fid}/export?mimeType={urllib.parse.quote(XLSX)}"
    for a in range(retries):
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=180, stream=True)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
            data = b"".join(r.iter_content(65536))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return len(data)
        except requests.exceptions.RequestException:
            time.sleep(3)
    raise RuntimeError("сеть: не удалось скачать после ретраев")


def sync():
    creds = _creds()
    creds.refresh(gt.Request())
    token = creds.token
    for key, dest in TARGETS.items():
        fid = C.GOOGLE_IDS[key]
        sz = _download(token, fid, dest)
        print(f"  {key}: {sz//1024} КБ -> {dest.name}")
    print("Google-таблицы синхронизированы.")


if __name__ == "__main__":
    sync()

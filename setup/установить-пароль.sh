#!/bin/bash
# Задать пароль на дашборд.
#
# Пароль вводится скрыто и никуда не записывается: ни в файл, ни в историю
# команд, ни в переписку с Клодом. На Netlify уезжает только его хэш,
# из которого пароль обратно не достать.
#
# Запуск:  bash setup/установить-пароль.sh
#
# Имена переменных латиницей: bash 3.2 в macOS кириллицу в именах не понимает.

set -u
cd "$(dirname "$0")/.." || exit 1

echo "Пароль на финансовый дашборд Резерв Сил"
echo "───────────────────────────────────────"
echo

# ── Пароль, дважды, скрыто ─────────────────────────
printf "Придумайте пароль: "
stty -echo 2>/dev/null; read -r pass1; stty echo 2>/dev/null; echo
printf "Повторите: "
stty -echo 2>/dev/null; read -r pass2; stty echo 2>/dev/null; echo
echo

if [ "$pass1" != "$pass2" ]; then
  echo "Пароли не совпали. Ничего не меняли, запустите ещё раз."
  exit 1
fi

if [ ${#pass1} -lt 8 ]; then
  echo "Слишком короткий: нужно хотя бы 8 символов."
  echo "Этот пароль закрывает зарплаты сотрудников, он стоит подлиннее."
  exit 1
fi

# ── Считаем хэш и ключи ────────────────────────────
hash=$(node -e '
  const crypto = require("node:crypto");
  const plain = process.argv[1];
  const salt = crypto.randomBytes(16).toString("hex");
  const key = crypto.scryptSync(plain.normalize("NFKC"), salt, 32).toString("hex");
  process.stdout.write("scrypt$" + salt + "$" + key);
' "$pass1") || { echo "Не нашёлся node. Поставьте Node.js и повторите."; exit 1; }

unset pass1 pass2

ticket_secret=$(node -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("hex"))')
build_token=$(node -e 'process.stdout.write(require("node:crypto").randomBytes(24).toString("hex"))')

echo "Хэш посчитан. Отправляю настройки на Netlify..."
echo

# ── Кладём на Netlify ──────────────────────────────
set_var() {
  if netlify env:set "$1" "$2" >/dev/null 2>&1; then
    echo "  ✓ $1"
  else
    echo "  ✗ $1 — не записалось"
    return 1
  fi
}

ok=0
set_var PASSWORD_HASH "$hash"   || ok=1
set_var TICKET_SECRET "$ticket_secret" || ok=1
set_var BUILD_TOKEN   "$build_token"   || ok=1

echo
if [ "$ok" -ne 0 ]; then
  echo "Что-то не записалось. Проверьте, что папка связана с проектом:"
  echo "    netlify link"
  exit 1
fi

echo "Готово. Пароль работает."
echo
echo "Осталось положить служебный ключ в GitHub, чтобы сборка могла"
echo "сравнивать цифры с прошлым прогоном. Одной командой:"
echo
echo "    gh secret set BUILD_TOKEN --body '$build_token' --repo annamironov1234-wq/rezerv-dashboard"
echo
echo "Пароль нигде не сохранён. Забудете — запустите этот скрипт заново"
echo "и задайте новый, старый перестанет работать."

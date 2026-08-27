# Save the Date — Telegram-бот

Реалізація за ТЗ: запрошення партнерів на виставку, вибір дати, збір даних гостя,
нагадування, Excel-звіт на email.

## Стек
- Python 3.11+, aiogram 3 (async)
- SQLAlchemy (async) — за замовчуванням SQLite, легко перемкнути на PostgreSQL (`DATABASE_URL`)
- APScheduler — нагадування й авто-звіт за розкладом (timezone Europe/Kyiv)
- openpyxl — Excel-звіти та персональні посилання
- pandas — імпорт CSV/Excel

## Встановлення
```bash
pip install -r requirements.txt
cp .env.example .env
# заповнити .env: BOT_TOKEN, BOT_USERNAME, ADMIN_IDS, дати виставки, SMTP-дані
```

Покладіть банер у `data/banner.jpg` (шлях налаштовується в `texts.yaml` -> `banner_path`).
Усі тексти повідомлень редагуються в `texts.yaml` без змін коду.

## Запуск
```bash
python main.py
```

## Джерела контактів (працюють одночасно)

**Варіант А — вже є chat_id.**
1. `/import` у відповідь на CSV/Excel файл з колонкою `chat_id` (+ опційно username/full_name/phone/company/position). Приклад — `data/import_template.csv`.
2. `/send_invitations` — розсилає Save-the-date усім імпортованим гостям зі статусом "не надіслано".

**Варіант Б — персональні посилання.**
1. `/import` тим самим файлом, але без `chat_id` (лише ім'я/телефон/компанія за наявності).
2. `/links` — бот згенерує Excel з посиланнями виду `t.me/BotUsername?start=code` для кожного такого гостя. Ці посилання розсилаються партнерам поза ботом (email, месенджер тощо).
3. Коли партнер переходить за посиланням і тисне Start, бот одразу показує Save-the-date.

Обидва варіанти можна імпортувати одночасно тим самим файлом (просто в одних рядків є `chat_id`, в інших — ні).

## Адмін-команди
Доступні тільки user_id, вказаним у `ADMIN_IDS` (.env):
- `/import` — імпорт контактів (reply на файл)
- `/links` — вивантажити персональні посилання (варіант Б)
- `/send_invitations` — розіслати Save-the-date по варіанту А
- `/report_now` — сформувати Excel-звіт і надіслати в чат + на email
- `/stats` — коротка статистика по статусах

## Нагадування
Автоматично, раз на день о `SCHEDULER_HOUR:SCHEDULER_MINUTE` (Europe/Kyiv):
- через `REMINDER_1_DAYS_AFTER_INVITE` днів після запрошення — тим, хто не відповів
- за `REMINDER_2_DAYS_BEFORE_EVENT` днів до першої дати виставки — тим, хто не підтвердив
- після дати виставки гостям без підтвердження виставляється статус `no_response` для звітності

Щоденний авто-звіт на email вмикається `DAILY_AUTO_REPORT=true` в `.env`.

## Зміна дати
У підтверджуючому повідомленні є кнопка "Змінити дату" — відкриває вибір дати заново.
Запис у базі оновлюється (не дублюється), а історія змін (дата + час) зберігається
в полі `date_history` і потрапляє у звіт.

## Що потрібно від замовника перед запуском (п. 6, 8 ТЗ)
- Точні дати виставки (зараз у `.env` як заглушка 28-30.10.2026)
- Банер і фінальні тексти повідомлень (`texts.yaml`, `data/banner.jpg`)
- Хостинг і БД (за замовчуванням готово для SQLite "з коробки"; для PostgreSQL — просто змінити `DATABASE_URL`)
- SMTP-дані для відправки звіту та адреса отримувача

## Структура проекту
```
main.py                      # точка входу
bot/config.py                 # налаштування з .env + тексти з texts.yaml
bot/db.py                     # модель Guest, доступ до БД
bot/keyboards.py               # inline/reply клавіатури
bot/states.py                  # FSM стани збору даних
bot/middlewares.py             # DB-сесія в кожен апдейт
bot/scheduler.py               # нагадування + авто-звіт (APScheduler)
bot/handlers/start.py          # /start (deep-link і звичайний)
bot/handlers/date_selection.py # вибір/зміна дати, підтвердження prefilled-даних
bot/handlers/data_collection.py# збір імені/телефону/компанії
bot/handlers/admin.py          # адмін-команди
bot/services/import_contacts.py# імпорт CSV/Excel
bot/services/link_generator.py # персональні посилання (варіант Б)
bot/services/excel_export.py   # звіт для замовника
bot/services/email_sender.py   # відправка звіту на email
bot/services/messaging.py      # надсилання Save-the-date/нагадувань + обробка помилок доставки
texts.yaml                     # усі редаговані тексти й шлях до банера
data/import_template.csv       # приклад файлу для /import
```

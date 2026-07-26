# InvestmentsScraper — v0.0

Нормализует CSV-выгрузки с брокерских платформ в единую таблицу и генерирует
markdown-заметки по позициям в Obsidian-vault "AI Brain"
(`07_Финансы и активы/Позиции/`, путь захардкожен в `POSITIONS_DIR` в скрипте).

> Репозиторий публичный. Все `raw/**/*.csv` (реальные брокерские выгрузки) в
> `.gitignore` и не попадают в коммиты — трекается только пустой
> `manual.example.csv`. Путь к Obsidian-vault в `POSITIONS_DIR` тоже стоит
> проверить, если форкаете к себе — он захардкожен под конкретный vault.

## Куда класть сырые выгрузки

Клади CSV в `raw/<platform>/`, затем запускай `python normalize_investments.py`.

## Robinhood
Account → Reports and Statements → задать диапазон дат → Generate Report →
Download CSV (готовится до 24ч). Файл(ы) → `robinhood/`.

## Fidelity
Activity & Orders → экспорт. Выгружается по 90 дней за раз — если истории
больше, скачай несколько файлов и положи все в `fidelity/`.
Учти: cost basis по проданным позициям в этом отчёте не указан — для точного
P&L дополнительно понадобится отчёт Realized Gain/Loss (не обязательно для
разовой сверки позиций).

## Charles Schwab
Accounts → History → выбрать счёт/период → Export → CSV.
Лимит 1500 строк на файл — при большой истории выгружай по периодам,
все файлы в `schwab/`.

## Webull
В приложении/на сайте: Account → Statements/History → экспорт. Формат заранее
не проверен — положи файл в `webull/` и запусти скрипт; если он не распознает
колонки, выведет реальные заголовки и её надо будет поправить в `COLUMN_MAP`
скрипта (или сообщи мне — поправлю).

## Fundrise
Нормального CSV-экспорта транзакций нет, только PDF-выписки (Documents →
Statements). Скопируй `fundrise/manual.example.csv` → `fundrise/manual.csv`
и вручную заполни по шаблону (колонки: date, ticker, action, quantity, price,
amount, notes). `manual.csv` с реальными данными в `.gitignore` — в репозиторий
не попадёт, только пустой example.

## Computershare
Investor Center → Activity → экспорт в CSV. Положи в `computershare/`.
Если колонки не совпадут — так же выведет реальные заголовки.

## Если формат не подошёл
```
python normalize_investments.py --inspect <platform> <файл.csv>
```
Покажет реальные заголовки CSV — дальше просто правим словарь `COLUMN_MAP`
в начале скрипта под них, логику трогать не нужно.

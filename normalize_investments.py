"""
Нормализация выгрузок с брокерских платформ в единый CSV + markdown-заметки
для Obsidian (Dataview-совместимые).

Использование:
    1. Скачать сырые CSV с каждой платформы (см. README.md) и положить
       в raw/<platform>/ — можно несколько файлов на платформу.
    2. pip install pandas
    3. python normalize_investments.py
    4. Проверить raw/normalized_transactions.csv
    5. Заметки появятся в Obsidian-vault, папка "Позиции" (путь ниже,
       POSITIONS_DIR), по одной на пару (платформа, тикер)

Если парсер платформы падает с "нет колонки ...":
    python normalize_investments.py --inspect <platform> <путь_к_файлу.csv>
покажет реальные заголовки CSV — поправь COLUMN_MAP под них.

Скрипт не считает P&L и не сверяется с рынком — это финальный шаг, который
будет делать агент отдельно. Здесь только сведение сырых транзакций к общей
таблице и черновые markdown-заметки по позициям.
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
POSITIONS_DIR = Path(r"A:\Obsidian\AI Brain\07_Финансы и активы\Позиции")
OUT_CSV = RAW / "normalized_transactions.csv"

NORMALIZED_COLUMNS = [
    "platform",
    "date",
    "ticker",
    "asset_name",
    "action",
    "quantity",
    "price",
    "fees",
    "amount",
    "notes",
    "source_file",
]

# Догадки по заголовкам реальных экспортов на момент написания (2026-07).
# Если формат платформы поменялся — правь только это, логика ниже не трогается.
COLUMN_MAP = {
    "robinhood": {
        "date": "Activity Date",
        "ticker": "Instrument",
        "action": "Trans Code",
        "quantity": "Quantity",
        "price": "Price",
        "amount": "Amount",
        "desc": "Description",
    },
    "schwab": {
        "date": "Date",
        "ticker": "Symbol",
        "action": "Action",
        "quantity": "Quantity",
        "price": "Price",
        "fees": "Fees & Comm",
        "amount": "Amount",
        "desc": "Description",
    },
    "fidelity": {
        "date": "Run Date",
        "ticker": "Symbol",
        "action": "Action",
        "quantity": "Quantity",
        "price": "Price ($)",
        "fees": "Fees ($)",
        "amount": "Amount ($)",
        "desc": "Description",
    },
    "webull": {
        "date": "Filled Time",
        "ticker": "Symbol",
        "action": "Side",
        "quantity": "Filled",
        "price": "Avg Price",
        "amount": "Amount",
        "desc": None,
    },
    "computershare": {
        "date": "Transaction Date",
        "ticker": None,
        "action": "Transaction Type",
        "quantity": "Shares",
        "price": "Price",
        "amount": "Amount",
        "desc": "Description",
    },
}

# Fundrise отдаёт только PDF-выписки — данные вносятся вручную в этот шаблон.
MANUAL_TEMPLATE_COLUMNS = [
    "date",
    "ticker",
    "action",
    "quantity",
    "price",
    "amount",
    "notes",
]

ACTION_KEYWORDS = [
    (re.compile(r"reinvest", re.IGNORECASE), "reinvest"),
    (re.compile(r"\bbuy|bought|purchase", re.IGNORECASE), "buy"),
    (re.compile(r"\bsell|sold", re.IGNORECASE), "sell"),
    (re.compile(r"div", re.IGNORECASE), "dividend"),
    (re.compile(r"interest", re.IGNORECASE), "interest"),
    (re.compile(r"transfer.*in|received|deposit", re.IGNORECASE), "transfer_in"),
    (re.compile(r"transfer.*out|withdraw", re.IGNORECASE), "transfer_out"),
    (re.compile(r"fee|gold", re.IGNORECASE), "fee"),
]


def normalize_action(raw: str) -> str:
    if not raw:
        return "other"
    for pattern, label in ACTION_KEYWORDS:
        if pattern.search(str(raw)):
            return label
    return "other"


def find_header_row(path: Path, hint_cols: list[str], max_scan: int = 10) -> int:
    """Некоторые экспорты (Schwab) добавляют преамбулу перед заголовком."""
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        for i, line in enumerate(f):
            if i > max_scan:
                break
            hits = sum(1 for h in hint_cols if h.lower() in line.lower())
            if hits >= 2:
                return i
    return 0


def load_csv(path: Path, cmap: dict) -> pd.DataFrame:
    hints = [v for v in cmap.values() if v]
    skip = find_header_row(path, hints)
    return pd.read_csv(path, skiprows=skip, encoding="utf-8-sig")


def parse_platform(platform: str, cmap: dict) -> pd.DataFrame:
    folder = RAW / platform
    files = sorted(folder.glob("*.csv"))
    rows = []
    for path in files:
        try:
            df = load_csv(path, cmap)
        except Exception as e:
            print(f"[{platform}] не удалось прочитать {path.name}: {e}")
            continue

        missing = [
            v for k, v in cmap.items() if v and v not in df.columns and k != "desc"
        ]
        if missing:
            print(
                f"[{platform}] {path.name}: нет колонок {missing}. "
                f"Реальные заголовки: {list(df.columns)}"
            )
            continue

        for _, r in df.iterrows():
            action_src = r.get(cmap["action"], "")
            rows.append(
                {
                    "platform": platform,
                    "date": r.get(cmap["date"], ""),
                    "ticker": r.get(cmap["ticker"], "") if cmap.get("ticker") else "",
                    "asset_name": r.get(cmap.get("desc"), "")
                    if cmap.get("desc")
                    else "",
                    "action": normalize_action(str(action_src)),
                    "quantity": r.get(cmap.get("quantity"), None),
                    "price": r.get(cmap.get("price"), None),
                    "fees": r.get(cmap.get("fees"), None) if cmap.get("fees") else None,
                    "amount": r.get(cmap.get("amount"), None),
                    "notes": str(action_src),
                    "source_file": path.name,
                }
            )
    return pd.DataFrame(rows, columns=NORMALIZED_COLUMNS)


def parse_manual(platform: str) -> pd.DataFrame:
    """Fundrise и любая платформа без нормального CSV — заполняется вручную
    по шаблону raw/<platform>/manual.csv (см. README.md)."""
    path = RAW / platform / "manual.csv"
    if not path.exists():
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["platform"] = platform
    df["action"] = df["action"].apply(normalize_action)
    df["source_file"] = "manual.csv"
    df["asset_name"] = df.get("notes", "")
    for col in NORMALIZED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[NORMALIZED_COLUMNS]


def write_position_note(platform: str, ticker: str, group: pd.DataFrame):
    safe_ticker = re.sub(r"[\\/:*?\"<>|]", "_", str(ticker)) or "UNKNOWN"
    fname = f"{safe_ticker} — {platform}.md"
    path = POSITIONS_DIR / fname

    buys = group[group["action"] == "buy"]
    sells = group[group["action"] == "sell"]
    net_qty = (
        pd.to_numeric(buys["quantity"], errors="coerce").sum()
        - pd.to_numeric(sells["quantity"], errors="coerce").sum()
    )

    lines = [
        "---",
        f'title: "{ticker} — {platform}"',
        "type: finance",
        "tags: [me/finance, investments, position]",
        "source: SELF",
        'up: "[[Финансовые активы]]"',
        f"platform: {platform}",
        f"ticker: {ticker}",
        f"net_qty: {net_qty:g}" if pd.notna(net_qty) else "net_qty:",
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        f"# {ticker} — {platform}",
        "",
        "## Сделки",
        "",
        "| Дата | Действие | Кол-во | Цена | Сумма | Комментарий |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in group.sort_values("date").iterrows():
        lines.append(
            f"| {r['date']} | {r['action']} | {r['quantity']} | {r['price']} | "
            f"{r['amount']} | {str(r['notes'])[:60]} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index_note(all_df: pd.DataFrame):
    path = POSITIONS_DIR / "_Позиции (сводная).md"
    lines = [
        "---",
        "title: Позиции — сводная таблица",
        "type: finance",
        "tags: [me/finance, investments, moc]",
        "source: SELF",
        'up: "[[Финансовые активы]]"',
        f"updated: {date.today().isoformat()}",
        "---",
        "",
        "# Позиции — сводная таблица",
        "",
        "```dataview",
        'TABLE platform as "Платформа", ticker as "Тикер", net_qty as "Кол-во"',
        'FROM "07_Финансы и активы/Позиции"',
        "WHERE ticker",
        "SORT platform, ticker",
        "```",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inspect(platform: str, file_path: str):
    df = pd.read_csv(file_path, nrows=5, encoding="utf-8-sig")
    print(f"Заголовки {file_path}:\n{list(df.columns)}\n")
    print(df.head())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--inspect":
        inspect(sys.argv[2], sys.argv[3])
        return

    frames = []
    for platform, cmap in COLUMN_MAP.items():
        frames.append(parse_platform(platform, cmap))
    frames.append(parse_manual("fundrise"))

    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.dropna(how="all", subset=["ticker", "asset_name", "amount"])

    RAW.mkdir(exist_ok=True)
    POSITIONS_DIR.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Сведено {len(all_df)} транзакций → {OUT_CSV}")

    key_cols = ["platform", "ticker"]
    for (platform, ticker), group in all_df.groupby(key_cols):
        if not str(ticker).strip():
            continue
        write_position_note(platform, ticker, group)

    write_index_note(all_df)
    print(f"Заметки по позициям записаны в {POSITIONS_DIR}")


if __name__ == "__main__":
    main()

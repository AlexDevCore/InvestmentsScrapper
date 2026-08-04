# InvestmentsScraper

[![tests](https://github.com/AlexDevCore/InvestmentsScraper/actions/workflows/tests.yml/badge.svg)](https://github.com/AlexDevCore/InvestmentsScraper/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Six brokerages export their transaction history six different ways, and none of them agree on a format. This normalizes all of them into one transaction table and generates a per-position markdown note for an Obsidian vault.

Supported: **Robinhood · Fidelity · Charles Schwab · Webull · Computershare · Fundrise**

> This repository is public. Every `raw/**/*.csv` — the real brokerage exports — is in `.gitignore` and never reaches a commit. Only an empty `manual.example.csv` is tracked.

## Usage

Drop exports into `raw/<platform>/`, then run:

```bash
pip install -e .
python normalize_investments.py
```

Output: a combined `normalized_transactions.csv` plus one markdown note per position.

Where the notes are written is set by `POSITIONS_DIR`; without it they land in `./positions` next to the script.

```powershell
$env:POSITIONS_DIR = "C:\path\to\your\vault\Positions"
python normalize_investments.py
```

## When a broker changes its export format

```bash
python normalize_investments.py --inspect <platform> <file.csv>
```

This prints the CSV's actual headers. Map them in `COLUMN_MAP` at the top of the script — the parsing logic itself does not change. That is the point of the design: a new or altered export is a dictionary entry, not a rewrite.

The loader also copes with two things that break a naive `read_csv` call: an export whose real header sits several lines below a preamble (Schwab does this), and a UTF-8 BOM on Windows exports that otherwise ends up glued to the first column name.

## Getting the exports

**Robinhood** — Account → Reports and Statements → set a date range → Generate Report → Download CSV. The report can take up to 24 hours to prepare. Files go in `raw/robinhood/`.

**Fidelity** — Activity & Orders → export. Limited to 90 days per file, so a longer history means several files; put them all in `raw/fidelity/`. Note that this report omits cost basis for sold positions — exact P&L needs the separate Realized Gain/Loss report, which is not required for a position reconciliation.

**Charles Schwab** — Accounts → History → pick account and period → Export → CSV. Capped at 1500 rows per file; split a long history by period and drop every file into `raw/schwab/`.

**Webull** — Account → Statements/History → export. If the column names do not match, run `--inspect` and add them to `COLUMN_MAP`.

**Computershare** — Investor Center → Activity → export to CSV, into `raw/computershare/`.

**Fundrise** — no transaction CSV export exists, only PDF statements (Documents → Statements). Copy `raw/fundrise/manual.example.csv` to `manual.csv` and fill it in by hand: `date, ticker, action, quantity, price, amount, notes`. The filled `manual.csv` is gitignored.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

20 tests covering action classification — a reinvested dividend must not be counted twice, as both a dividend and a purchase — and header detection underneath an export preamble.

## Requirements

Python 3.10+ · pandas

## License

MIT — see [LICENSE](LICENSE).

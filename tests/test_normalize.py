"""Tests for the two pieces every broker import depends on: action labelling
and finding the real header row underneath an export's preamble."""

import pytest
from normalize_investments import find_header_row, load_csv, normalize_action

SCHWAB_HINTS = ["Date", "Action", "Symbol", "Quantity"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Buy", "buy"),
        ("BOUGHT 10 SHARES", "buy"),
        ("Purchase", "buy"),
        ("Sell", "sell"),
        ("Sold Short", "sell"),
        ("Qualified Dividend", "dividend"),
        ("Bank Interest", "interest"),
        ("Transfer In", "transfer_in"),
        ("Wire Withdrawal", "transfer_out"),
        ("ADR Fee", "fee"),
        ("Reinvest Dividend", "reinvest"),
    ],
)
def test_known_actions_are_labelled(raw, expected):
    assert normalize_action(raw) == expected


def test_reinvestment_wins_over_dividend():
    """Both keywords match; 'reinvest' must take priority or cash flow is double counted."""
    assert normalize_action("Reinvest Dividend") == "reinvest"


@pytest.mark.parametrize("raw", ["", None, "Journaled Shares"])
def test_unrecognised_actions_fall_back_to_other(raw):
    assert normalize_action(raw) == "other"


def test_header_row_found_when_the_file_starts_clean(tmp_path):
    path = tmp_path / "clean.csv"
    path.write_text(
        "Date,Action,Symbol,Quantity\n2026-01-02,Buy,VOO,1\n", encoding="utf-8"
    )
    assert find_header_row(path, SCHWAB_HINTS) == 0


def test_header_row_found_underneath_a_preamble(tmp_path):
    """Schwab prefixes exports with account and date-range lines."""
    path = tmp_path / "schwab.csv"
    path.write_text(
        '"Transactions for account XXXX-1234"\n'
        '"Date Range: 01/01/2026 to 12/31/2026"\n'
        "\n"
        "Date,Action,Symbol,Quantity\n"
        "2026-01-02,Buy,VOO,1\n",
        encoding="utf-8",
    )
    assert find_header_row(path, SCHWAB_HINTS) == 3


def test_header_search_gives_up_instead_of_scanning_the_whole_file(tmp_path):
    path = tmp_path / "noheader.csv"
    path.write_text("\n".join(f"junk line {i}" for i in range(40)), encoding="utf-8")
    assert find_header_row(path, SCHWAB_HINTS) == 0


def test_load_csv_skips_the_preamble_and_returns_real_columns(tmp_path):
    path = tmp_path / "schwab.csv"
    path.write_text(
        '"Transactions for account XXXX-1234"\n'
        "Date,Action,Symbol,Quantity\n"
        "2026-01-02,Buy,VOO,1\n"
        "2026-01-03,Sell,VOO,1\n",
        encoding="utf-8",
    )
    frame = load_csv(path, {"date": "Date", "action": "Action", "ticker": "Symbol"})
    assert list(frame.columns) == ["Date", "Action", "Symbol", "Quantity"]
    assert len(frame) == 2


def test_load_csv_handles_a_utf8_bom(tmp_path):
    """Windows exports routinely carry a BOM; it must not end up inside the first column name."""
    path = tmp_path / "bom.csv"
    path.write_text(
        "Date,Action,Symbol,Quantity\n2026-01-02,Buy,VOO,1\n", encoding="utf-8-sig"
    )
    frame = load_csv(path, {"date": "Date", "action": "Action"})
    assert frame.columns[0] == "Date"

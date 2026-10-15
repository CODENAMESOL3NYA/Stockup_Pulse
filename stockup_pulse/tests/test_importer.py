from io import BytesIO

import pytest
from openpyxl import Workbook

from stockup_pulse.ingest.importer import (
    ImportValidationError,
    normalize_leaflet_candidates,
    parse_sales_stock_files,
)


def test_csv_sales_aggregate_and_zero_fill_missing_days():
    sales = b"date,product,quantity_sold\n2025-01-01,Brown Bread,2\n2025-01-01,Brown Bread,3\n2025-01-03,Brown Bread,4\n"
    stock = b"product,current_stock\nBrown Bread,5\n"

    imported = parse_sales_stock_files([
        ("sales.csv", sales),
        ("stock.csv", stock),
    ])

    assert imported["sales"]["brown bread"] == {
        "2025-01-01": 5.0,
        "2025-01-02": 0.0,
        "2025-01-03": 4.0,
    }
    assert imported["stock"]["brown bread"] == 5.0
    assert imported["sales_interval"] == {"start": "2025-01-01", "end": "2025-01-03"}


def test_xlsx_sales_and_stock_sheets_are_parsed():
    workbook = Workbook()
    sales = workbook.active
    sales.title = "sales"
    sales.append(["date", "product", "quantity_sold"])
    sales.append(["2025-02-01", "Rice 2kg", 7])
    stock = workbook.create_sheet("stock")
    stock.append(["product", "current_stock"])
    stock.append(["Rice 2kg", 3])
    content = BytesIO()
    workbook.save(content)

    imported = parse_sales_stock_files([("store.xlsx", content.getvalue())])

    assert imported["sales"]["rice 2kg"] == {"2025-02-01": 7.0}
    assert imported["stock"]["rice 2kg"] == 3.0


@pytest.mark.parametrize(
    "sales,stock",
    [
        (b"date,product,quantity_sold\n01/02/2025,Rice,1\n", b"product,current_stock\nRice,1\n"),
        (b"date,product,quantity_sold\n2025-02-01,Rice,nan\n", b"product,current_stock\nRice,1\n"),
        (b"date,product,quantity_sold\n2025-02-01,Rice,1\n", b"product,current_stock\nRice,1\nRICE,2\n"),
    ],
)
def test_csv_rejects_invalid_dates_quantities_and_conflicting_stock(sales, stock):
    with pytest.raises(ImportValidationError):
        parse_sales_stock_files([("sales.csv", sales), ("stock.csv", stock)])


def test_normalized_name_collisions_are_marked_ambiguous():
    imported = parse_sales_stock_files([
        ("sales.csv", b"date,product,quantity_sold\n2025-01-01,Milk-1L,2\n2025-01-02,Milk 1L,3\n"),
        ("stock.csv", b"product,current_stock\nMilk-1L,4\n"),
    ])

    assert imported["product_names"]["milk 1l"] == ["Milk 1L", "Milk-1L"]


def test_leaflet_pack_count_derives_unit_price_and_preserves_evidence():
    candidates = normalize_leaflet_candidates(
        [{
            "product": "Milk 1L",
            "pack_size": "6 x 1L",
            "pack_price": 60,
            "supplier": "Makro",
            "currency": "ZAR",
            "availability": "In stock",
            "evidence": "6 for R60",
            "confidence": 0.9,
        }],
        source="amd",
        source_filename="leaflet.jpg",
    )

    assert candidates[0]["pack_count"] == 6
    assert candidates[0]["supplier_price"] == 60.0
    assert candidates[0]["unit_price"] == 10.0
    assert candidates[0]["currency"] == "ZAR"
    assert candidates[0]["evidence"] == "6 for R60"
    assert candidates[0]["warnings"] == []


def test_leaflet_rejects_conflicting_pack_counts_and_warns_when_unclear():
    with pytest.raises(ImportValidationError, match="conflicting"):
        normalize_leaflet_candidates(
            [{
                "product": "Milk",
                "pack_size": "6 x 1L",
                "pack_count": 12,
                "pack_price": 60,
                "supplier": "Makro",
            }],
            source="evolus",
            source_filename="leaflet.pdf",
        )

    normalized = normalize_leaflet_candidates(
        [{"product": "Milk", "pack_price": 60, "supplier": "Makro"}],
        source="evolus",
        source_filename="leaflet.pdf",
    )
    assert normalized[0]["unit_price"] is None
    assert "Currency was not supplied; verify the amount is in ZAR." in normalized[0]["warnings"]
    assert "Pack count is unclear; supplier unit price requires manual review." in normalized[0]["warnings"]


def test_leaflet_missing_supplier_price_is_retained_for_manual_review():
    normalized = normalize_leaflet_candidates(
        [{"product": "Milk", "pack_size": "6 x 1L"}],
        source="amd",
        source_filename="leaflet.jpg",
    )

    assert normalized[0]["supplier"] == ""
    assert normalized[0]["supplier_price"] is None
    assert "Supplier pack price was not supplied; enter the observed price." in normalized[0]["warnings"]

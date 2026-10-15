from stockup_pulse.app.ingest.live_scraper import parse_price


def test_parse_price_supports_south_african_formats():
    assert parse_price("R 24,99") == 24.99
    assert parse_price("R1,299.00") == 1299.0


def test_parse_price_rejects_invalid_values():
    assert parse_price(0) is None
    assert parse_price(-1) is None
    assert parse_price("-5") is None
    assert parse_price(float("nan")) is None
    assert parse_price("not a price") is None
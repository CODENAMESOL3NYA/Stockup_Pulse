import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine

import stockup_pulse.core.db as database


def _create_legacy_orders_table(engine, records):
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE api_orders ("
            "id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, plan_id VARCHAR NOT NULL, "
            "order_number VARCHAR NOT NULL, order_json TEXT NOT NULL, created_at_utc VARCHAR NOT NULL)"
        )
        for index, payload in enumerate(records, start=1):
            connection.execute(
                text(
                    "INSERT INTO api_orders "
                    "(id, owner_id, plan_id, order_number, order_json, created_at_utc) "
                    "VALUES (:id, 1, 'plan-1', :order_number, :order_json, '2025-01-01')"
                ),
                {
                    "id": index,
                    "order_number": f"PO-{index}",
                    "order_json": json.dumps(payload),
                },
            )


def test_migration_backfills_supplier_and_is_idempotent(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    _create_legacy_orders_table(engine, [{"supplier": "Makro"}])
    monkeypatch.setattr(database, "engine", engine)

    database.migrate_database()
    database.migrate_database()

    with engine.begin() as connection:
        row = connection.execute(text("SELECT supplier FROM api_orders WHERE id = 1")).one()
        index = connection.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name = 'uq_api_orders_owner_plan_supplier'"
            )
        ).one()
        migration = connection.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar_one()

    assert row.supplier == "Makro"
    assert index.name == "uq_api_orders_owner_plan_supplier"
    assert migration == 1
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO api_orders "
                    "(owner_id, plan_id, supplier, order_number, order_json, created_at_utc) "
                    "VALUES (1, 'plan-1', 'Makro', 'PO-duplicate', '{}', '2025-01-02')"
                )
            )
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO api_orders "
                "(owner_id, plan_id, supplier, order_number, order_json, created_at_utc) "
                "VALUES (1, 'plan-1', 'Shoprite', 'PO-other-supplier', '{}', '2025-01-02')"
            )
        )
    engine.dispose()


def test_migration_fails_explicitly_when_legacy_supplier_orders_are_duplicated(
    tmp_path, monkeypatch
):
    engine = create_engine(f"sqlite:///{tmp_path / 'duplicates.db'}")
    _create_legacy_orders_table(
        engine,
        [{"supplier": "Makro"}, {"supplier": "Makro"}],
    )
    monkeypatch.setattr(database, "engine", engine)

    with pytest.raises(RuntimeError, match="duplicate orders already exist"):
        database.migrate_database()
    engine.dispose()

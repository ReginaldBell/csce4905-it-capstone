"""Add Sprint 3 columns and tables to an existing database, keeping records.

Run after init-db and upgrade-community.
"""

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from extensions import db

# These table, column, and type names are constants, never form input.
ADDITIONS = {
    "users": {
        "full_name": "VARCHAR(100)",
        "phone": "VARCHAR(30)",
        "session_version": "INTEGER NOT NULL DEFAULT 1",
    },
    "pets": {
        "sex": "VARCHAR(20)",
        "height_inches": "FLOAT",
        "weight_lbs": "FLOAT",
        "colors": "VARCHAR(100)",
        "markings": "VARCHAR(255)",
        "microchip_status": "VARCHAR(20) DEFAULT 'unknown'",
        "microchip_number": "VARCHAR(15)",
    },
    "contacts": {"address": "VARCHAR(255)"},
}


def upgrade_sprint3():
    inspector = inspect(db.engine)
    missing = []
    for table, columns in ADDITIONS.items():
        if not inspector.has_table(table):
            continue  # create_all below builds it with every column.
        existing = {column["name"] for column in inspector.get_columns(table)}
        missing += [
            (table, name, sql_type)
            for name, sql_type in columns.items()
            if name not in existing
        ]

    with db.engine.begin() as connection:
        for table, name, sql_type in missing:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
            )
    # Creates only missing tables: password_reset_tokens and auth_attempts.
    db.create_all()


@click.command("upgrade-sprint3")
@with_appcontext
def upgrade_sprint3_command():
    """Add Sprint 3 fields/tables; safe to run again on SQLite or PostgreSQL."""
    upgrade_sprint3()
    click.echo("Sprint 3 schema is ready. Existing records were kept.")

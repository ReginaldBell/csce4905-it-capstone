"""Add community fields to an existing database without resetting records."""

import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from extensions import db


def upgrade_community():
    inspector = inspect(db.engine)
    additions = {
        "users": {"display_name": "VARCHAR(50)"},
        "reports": {
            "is_shared": "BOOLEAN NOT NULL DEFAULT FALSE",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "community_area": "VARCHAR(120)",
            "community_description": "TEXT",
            "shared_at": "TIMESTAMP",
        },
    }
    # These table, column, and type names are constants, never form input.
    with db.engine.begin() as connection:
        for table, columns in additions.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                    )
    db.create_all()


@click.command("upgrade-community")
@with_appcontext
def upgrade_community_command():
    """Add community fields/tables; safe to run again on SQLite or PostgreSQL."""
    upgrade_community()
    click.echo("Community schema is ready. Existing records were kept.")

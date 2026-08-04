# Database migrations

Alembic is the only supported way to change the database schema.

```bash
make db-upgrade
make db-check
```

For a database that was created by the old `Base.metadata.create_all()` startup hook,
`upgrade_database()` compares its table/column contract with revision `0001`. It stamps `0001`
automatically only when all four legacy tables match exactly, then upgrades to head.

For an operator-controlled migration, verify the schema first and run:

```bash
uv run alembic stamp 0001
uv run alembic upgrade head
```

Do not stamp an unverified production database.

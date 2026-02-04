# Yoyo Migrations

Database migrations for the email-service using [yoyo-migrations](https://ollycope.com/software/yoyo/latest/).

## Configuration

Database credentials are loaded from `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your_password
DB_NAME=email_service
```

## Commands

### Create a new migration
```bash
uv run yoyo new -m "description of migration"
```

### Apply pending migrations
```bash
uv run yoyo apply
```

### Rollback last migration
```bash
uv run yoyo rollback
```

### Show migration status
```bash
uv run yoyo list
```

## Migration File Structure

Migrations are stored in the `migrations/` directory. Each migration file contains:

```python
from yoyo import step

steps = [
    step(
        "CREATE TABLE example (id SERIAL PRIMARY KEY, name VARCHAR(255))",
        "DROP TABLE example"
    )
]
```

- First argument: **apply** SQL
- Second argument: **rollback** SQL

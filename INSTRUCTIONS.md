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

Use the Makefile to run migrations with `.env` variables auto-exported:

```bash
# Create a new migration (prompts for name)
make migrate-new

# Apply pending migrations
make migrate-apply

# Rollback last migration
make migrate-rollback

# Show migration status
make migrate-list
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

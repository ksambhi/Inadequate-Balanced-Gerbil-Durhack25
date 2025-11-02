# Quick Reference - Database Commands

## Alembic Migration Commands

```bash
# Check current migration status
uv run alembic current

# View migration history
uv run alembic history

# Apply all pending migrations
uv run alembic upgrade head

# Apply specific number of migrations
uv run alembic upgrade +1

# Rollback one migration
uv run alembic downgrade -1

# Rollback to base (drops everything)
uv run alembic downgrade base

# Create new migration (auto-generate from models)
uv run alembic revision --autogenerate -m "description"

# Create empty migration (manual)
uv run alembic revision -m "description"
```

## Testing Database Operations

```bash
# Run the example script (CRUD operations)
uv run python -m app.db_example

# Start FastAPI server
uv run fastapi dev app/main.py
```

## API Endpoints

```bash
# Simple hello (no database)
curl http://localhost:8000/api/hello

# Create a Hello record
curl -X POST "http://localhost:8000/api/hello?order=first_order"

# Get all Hello records
curl http://localhost:8000/api/hellos

# Get specific Hello by ID
curl http://localhost:8000/api/hello/1
```

## Python Usage Example

```python
from sqlalchemy import select
from app.database import async_session
from app.models import Hello

# Create
async with async_session() as session:
    hello = Hello(order="example")
    session.add(hello)
    await session.commit()
    await session.refresh(hello)

# Read
async with async_session() as session:
    result = await session.execute(select(Hello))
    hellos = result.scalars().all()

# Update
async with async_session() as session:
    result = await session.execute(
        select(Hello).where(Hello.id == 1)
    )
    hello = result.scalar_one_or_none()
    if hello:
        hello.order = "updated"
        await session.commit()

# Delete
async with async_session() as session:
    result = await session.execute(
        select(Hello).where(Hello.id == 1)
    )
    hello = result.scalar_one_or_none()
    if hello:
        await session.delete(hello)
        await session.commit()
```

## Environment Variables (.env)

```bash
DB_USER=postgres
DB_PASS=your_password
DB_HOST=your_host
DB_PORT=5432
DB_NAME=postgres
```

## Key Files

- `app/database.py` - Database configuration
- `app/models.py` - ORM models (Hello model)
- `app/routers/hello.py` - API endpoints
- `app/db_example.py` - Example CRUD operations
- `alembic/env.py` - Alembic async configuration
- `alembic/versions/*.py` - Migration files
- `DATABASE_SETUP.md` - Complete documentation
- `SETUP_SUMMARY.md` - Setup overview

# Database Setup Guide

This document describes the Alembic + SQLAlchemy async setup for PostgreSQL.

## Overview

The backend uses:
- **SQLAlchemy 2.0+** with async support
- **asyncpg** as the PostgreSQL driver
- **Alembic** for database migrations
- **FastAPI** for the web framework

## Structure

```
backend/
├── alembic/
│   ├── env.py              # Alembic environment configuration
│   └── versions/           # Migration scripts
│       └── dc1cf3323bd8_create_hello_table.py
├── app/
│   ├── database.py         # Database engine and session management
│   ├── models.py           # ORM models (Hello model defined here)
│   └── routers/
│       └── hello.py        # Example router using the database
├── alembic.ini             # Alembic configuration
└── .env                    # Database credentials
```

## Configuration

### Environment Variables (.env)

```bash
DB_USER=postgres
DB_PASS=your_password
DB_HOST=your_host
DB_PORT=5432
DB_NAME=postgres
```

### Database URL

The connection string is built in `app/database.py`:
```
postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}
```

## Models

### Hello Model

Located in `app/models.py`:

```python
class Hello(Base):
    __tablename__ = "hello"
    
    id = Column(Integer, primary_key=True, index=True)
    order = Column(String, nullable=False)
```

## Running Migrations

### Check migration status
```bash
cd backend
uv run alembic current
```

### Apply migrations (upgrade to latest)
```bash
uv run alembic upgrade head
```

### Downgrade one revision
```bash
uv run alembic downgrade -1
```

### View migration history
```bash
uv run alembic history
```

## Creating New Migrations

### Auto-generate from model changes
```bash
uv run alembic revision --autogenerate -m "description of changes"
```

**Note:** Auto-generate requires database connectivity. If the database is not accessible, create an empty migration and populate it manually:

```bash
uv run alembic revision -m "description of changes"
```

### Manual migration example

See `alembic/versions/dc1cf3323bd8_create_hello_table.py` for an example.

## Using the Database in FastAPI

### Dependency Injection

Use the `get_db()` dependency to get database sessions:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Hello

@router.post("/hello")
async def create_hello(order: str, db: AsyncSession = Depends(get_db)):
    hello = Hello(order=order)
    db.add(hello)
    await db.commit()
    await db.refresh(hello)
    return {"id": hello.id, "order": hello.order}

@router.get("/hellos")
async def get_hellos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Hello))
    hellos = result.scalars().all()
    return [{"id": h.id, "order": h.order} for h in hellos]
```

## Troubleshooting

### Import Error: Cannot import 'async_sessionmaker'

Make sure you're using SQLAlchemy 2.0+:
```bash
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

### Network Unreachable

If you get network errors when running migrations, ensure:
1. Your database is accessible from your current network
2. The credentials in `.env` are correct
3. The database server is running

### Migration conflicts

If you have conflicts between migrations:
```bash
# Reset the database (CAUTION: This drops all data)
uv run alembic downgrade base
uv run alembic upgrade head
```

## Best Practices

1. **Always use async/await** with database operations
2. **Use transactions** for multiple operations that should be atomic
3. **Close sessions properly** - the `get_db()` dependency handles this automatically
4. **Test migrations** in a development environment first
5. **Never commit `.env`** to version control

## Adding New Models

1. Define the model in `app/models.py` inheriting from `Base`
2. Import the model in `alembic/env.py` (already configured for `Hello`)
3. Create a migration: `uv run alembic revision --autogenerate -m "add new model"`
4. Review and apply: `uv run alembic upgrade head`

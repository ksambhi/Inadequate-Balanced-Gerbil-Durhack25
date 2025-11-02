"""
Example script demonstrating database operations with the Hello model.
This can be run directly to test database connectivity and operations.

Usage:
    uv run python -m app.db_example
"""
import asyncio
from sqlalchemy import select
from app.database import async_session, engine, Base
from app.models import Hello


async def init_db():
    """Initialize database tables (alternative to running migrations)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_hello_example():
    """Example: Create a new Hello record."""
    async with async_session() as session:
        hello = Hello(order="first")
        session.add(hello)
        await session.commit()
        await session.refresh(hello)
        print(f"Created: {hello}")
        return hello.id


async def get_all_hellos():
    """Example: Query all Hello records."""
    async with async_session() as session:
        result = await session.execute(select(Hello))
        hellos = result.scalars().all()
        print(f"\nAll Hellos ({len(hellos)}):")
        for hello in hellos:
            print(f"  - {hello}")
        return hellos


async def get_hello_by_id(hello_id: int):
    """Example: Query a specific Hello record by ID."""
    async with async_session() as session:
        result = await session.execute(
            select(Hello).where(Hello.id == hello_id)
        )
        hello = result.scalar_one_or_none()
        if hello:
            print(f"\nFound: {hello}")
        else:
            print(f"\nNo Hello found with id={hello_id}")
        return hello


async def update_hello_example(hello_id: int, new_order: str):
    """Example: Update a Hello record."""
    async with async_session() as session:
        result = await session.execute(
            select(Hello).where(Hello.id == hello_id)
        )
        hello = result.scalar_one_or_none()
        if hello:
            hello.order = new_order
            await session.commit()
            await session.refresh(hello)
            print(f"\nUpdated: {hello}")
        return hello


async def delete_hello_example(hello_id: int):
    """Example: Delete a Hello record."""
    async with async_session() as session:
        result = await session.execute(
            select(Hello).where(Hello.id == hello_id)
        )
        hello = result.scalar_one_or_none()
        if hello:
            await session.delete(hello)
            await session.commit()
            print(f"\nDeleted: Hello with id={hello_id}")
            return True
        return False


async def main():
    """Run example operations."""
    print("=== Database Example Operations ===\n")
    
    # Note: Uncomment this if you want to create tables without migrations
    # await init_db()
    
    # Create
    print("1. Creating a new Hello...")
    hello_id = await create_hello_example()
    
    # Read one
    print("\n2. Getting Hello by ID...")
    await get_hello_by_id(hello_id)
    
    # Read all
    print("\n3. Getting all Hellos...")
    await get_all_hellos()
    
    # Update
    print("\n4. Updating Hello...")
    await update_hello_example(hello_id, "updated_order")
    
    # Read again to confirm update
    print("\n5. Getting updated Hello...")
    await get_hello_by_id(hello_id)
    
    # Delete
    print("\n6. Deleting Hello...")
    await delete_hello_example(hello_id)
    
    # Confirm deletion
    print("\n7. Confirming deletion...")
    await get_all_hellos()
    
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())

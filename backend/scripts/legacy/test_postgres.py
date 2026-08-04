import asyncio
from sqlalchemy.ext.asyncio import create_async_engine


async def test():
    try:
        import asyncpg

        print("asyncpg installed")
    except ImportError:
        print("asyncpg NOT installed")


asyncio.run(test())

import cli2
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

# Create async engine from config
engine = create_async_engine(cli2.cfg["CODE2_DB"], echo=False)
Base = declarative_base()

# Global async session factory
async_session_factory = None


class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    # Relationship
    files = relationship("File", backref="language")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    mtime = Column(Float, nullable=False)
    language_id = Column(
        Integer, ForeignKey("languages.id", ondelete="SET NULL")
    )
    token_count = Column(Integer, default=0, nullable=False)

    # Relationships
    symbols = relationship("Symbol", backref="file")
    references = relationship("Reference", backref="file")


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True)
    file_id = Column(
        Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    line_number = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)

    # Relationship
    references = relationship("Reference", backref="symbol")


class Reference(Base):
    __tablename__ = "reference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(
        Integer, ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    file_id = Column(
        Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )

    # Define unique constraint
    __table_args__ = (
        Index("idx_symbol_file", "symbol_id", "file_id", unique=True),
    )


async def connect():
    """Initialize database connection and create tables asynchronously."""
    global async_session_factory
    if async_session_factory is None:
        # Create all tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Create async session factory
        async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return async_session_factory


async def close():
    """Close the database engine."""
    await engine.dispose()


# Optional: Initialize database when module is imported (for testing)
if __name__ == "__main__":
    import asyncio

    asyncio.run(connect())

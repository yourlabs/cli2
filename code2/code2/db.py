import cli2
import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index, create_engine
from sqlalchemy.orm import declarative_base, relationship, configure_mappers

Base = declarative_base()


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
    references = relationship("Import", backref="file")


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True)
    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=True)
    score = Column(Integer, nullable=False)

    # Relationship
    references = relationship("Import", backref="symbol")


class Import(Base):
    __tablename__ = "import"

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


configure_mappers()

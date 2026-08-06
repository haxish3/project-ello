from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from ello.config import DATABASE_POOL_MODE, DATABASE_URL

opcoes_engine = {}
if DATABASE_URL.startswith("sqlite"):
    opcoes_engine["connect_args"] = {"check_same_thread": False}
elif DATABASE_POOL_MODE == "transaction":
    opcoes_engine["poolclass"] = NullPool
    opcoes_engine["connect_args"] = {"prepare_threshold": None}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **opcoes_engine)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass

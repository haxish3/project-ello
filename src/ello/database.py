from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(
    "sqlite:///./escola.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass

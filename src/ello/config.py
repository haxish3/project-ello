import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def normalizar_url_postgres(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif not url.startswith("postgresql+psycopg://"):
        return url
    partes = urlsplit(url)
    parametros = [
        (chave, valor)
        for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if chave.casefold() != "pgbouncer"
    ]
    return urlunsplit(partes._replace(query=urlencode(parametros)))


DATABASE_URL = normalizar_url_postgres(
    os.getenv("DATABASE_URL", "sqlite:///./escola.db")
)
MIGRATION_DATABASE_URL = normalizar_url_postgres(
    os.getenv("MIGRATION_DATABASE_URL", DATABASE_URL)
)
DATABASE_POOL_MODE = os.getenv("DATABASE_POOL_MODE", "session").casefold()
FRONTEND_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origem.strip()
]
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
PORT = int(os.getenv("PORT", "8000"))

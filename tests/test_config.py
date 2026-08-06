from ello.config import normalizar_url_postgres


def test_preserva_url_sqlite():
    assert normalizar_url_postgres("sqlite:///./escola.db") == "sqlite:///./escola.db"


def test_adapta_url_do_prisma_para_psycopg():
    resultado = normalizar_url_postgres(
        "postgresql://usuario:senha@host:6543/postgres?pgbouncer=true"
    )
    assert resultado == "postgresql+psycopg://usuario:senha@host:6543/postgres"

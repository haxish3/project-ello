from sqlalchemy import select

from ello.database import SessionLocal
from ello.models import Cargo, Usuario


def main():
    login = input("Login que receberá o cargo dev: ").strip().casefold()
    if not login:
        raise SystemExit("Login é obrigatório.")

    with SessionLocal() as banco:
        usuario = banco.scalar(select(Usuario).where(Usuario.login == login))
        if usuario is None:
            raise SystemExit("Usuário não encontrado.")

        cargo = banco.scalar(select(Cargo).where(Cargo.nome == "dev"))
        if cargo is None:
            raise SystemExit("Execute 'uv run alembic upgrade head' primeiro.")

        if cargo not in usuario.cargos:
            usuario.cargos.append(cargo)
            banco.commit()
        print(f"Usuário '{login}' agora possui o cargo dev.")


if __name__ == "__main__":
    main()

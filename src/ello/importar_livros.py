import argparse
import json
from pathlib import Path

from ello.database import Base, atualizar_estrutura_do_banco, engine
from ello.routes.livros import ImportacaoCsv, importar_csv


def main():
    parser = argparse.ArgumentParser(
        description="Importa livros de um CSV separado por ponto e vírgula."
    )
    parser.add_argument("arquivo", type=Path, help="Caminho do arquivo CSV")
    argumentos = parser.parse_args()

    conteudo = argumentos.arquivo.read_text(encoding="utf-8-sig")
    Base.metadata.create_all(engine)
    atualizar_estrutura_do_banco()
    resultado = importar_csv(ImportacaoCsv(conteudo=conteudo))
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

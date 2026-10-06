from banco_agil.bootstrap import build_engine
from banco_agil.presentation import greeting
from banco_agil.session import Session


def main():
    engine = build_engine()
    session = Session()
    print("Banco Ágil — confira .env.example para os modos disponíveis.")
    print(greeting())
    while session.stage != "closed":
        try:
            message = input("Você: ")
        except (EOFError, KeyboardInterrupt):
            session.close()
            break
        print("Banco Ágil:", engine.respond(session, message))


if __name__ == "__main__":
    main()

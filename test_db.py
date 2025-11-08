import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT"))
db   = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
pwd  = os.getenv("DB_PASS")

dsn = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
engine = create_engine(dsn, pool_pre_ping=True)

def main():
    try:
        with engine.connect() as conn:
            ok = conn.execute(text("SELECT 1")).scalar()
            ver = conn.execute(text("SELECT VERSION()")).scalar()
            print(f"Conexão OK (SELECT 1 = {ok}). MySQL versão: {ver}")
    except Exception as e:
        print("Falha ao conectar ou executar teste:")
        print(repr(e))

if __name__ == "__main__":
    main()
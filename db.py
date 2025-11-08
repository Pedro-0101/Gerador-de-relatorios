from sqlalchemy import create_engine, text
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def get_engine():
  user = os.getenv("DB_USER")
  pwd  = os.getenv("DB_PASS")
  host = os.getenv("DB_HOST")
  port = os.getenv("DB_PORT")
  db   = os.getenv("DB_NAME")
  url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
  return create_engine(url, pool_pre_ping=True)

def load_dataframe(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as con:
        df = pd.read_sql(text(sql), con, params=params or {})
    return df
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table

load_dotenv()

def get_engine():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True)



# Instanciar engine y metadata
engine = get_engine()
metadata = MetaData()

# Autoload de tablas reales de tu DB
clientes      = Table("clientes", metadata, autoload_with=engine)
cuentas       = Table("cuentas", metadata, autoload_with=engine)
otras_deudas  = Table("otras_deudas", metadata, autoload_with=engine)
propietario   = Table("propietario", metadata, autoload_with=engine)
registros     = Table("registros", metadata, autoload_with=engine)
usuarios      = Table("usuarios", metadata, autoload_with=engine)
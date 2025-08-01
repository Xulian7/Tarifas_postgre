from sqlalchemy import create_engine, text

# Conexión
DATABASE_URL = "postgresql+psycopg2://postgres:cUVmSghVIpRTJkWWtUymoMaadGwzLKUn@shuttle.proxy.rlwy.net:38698/railway"
engine = create_engine(DATABASE_URL)

# Alter y update
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE registros ADD COLUMN IF NOT EXISTS user_log TEXT;"))
    conn.execute(text("UPDATE registros SET user_log = 'Cobros1';"))

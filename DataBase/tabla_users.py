from sqlalchemy import Table, Column, Integer, String, MetaData
from conexion import engine

metadata = MetaData()

usuarios = Table("usuarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario", String, nullable=False, unique=True),
    Column("password", String, nullable=False),
    Column("nivel", String, nullable=False, default="usuario")
)

def crear_tabla_usuarios():
    metadata.create_all(engine)

if __name__ == "__main__":
    crear_tabla_usuarios()
    print("✅ Tabla 'usuarios' creada (o ya existía).")

import psycopg2

# URL de conexión descompuesta
conn = psycopg2.connect(
    dbname="railway",
    user="postgres",
    password="kOqrfNfhwfoUJQLCjYaRENZsGAJjdTue",
    host="yamanote.proxy.rlwy.net",
    port="43719"
)

cur = conn.cursor()

# Aquí irán las sentencias CREATE TABLE traducidas a PostgreSQL
create_clientes = """
CREATE TABLE clientes (
    Cedula TEXT PRIMARY KEY,
    Nombre TEXT NOT NULL,
    Nacionalidad TEXT,
    Telefono TEXT,
    Direccion TEXT,
    Placa TEXT,
    Fecha_inicio DATE NOT NULL,
    Fecha_final DATE NOT NULL,
    Tipo_contrato TEXT NOT NULL,
    Valor_cuota REAL CHECK(Valor_cuota >= 0),
    Estado TEXT DEFAULT 'activo' CHECK (Estado IN ('activo', 'inactivo')),
    Otras_deudas INTEGER DEFAULT 0,
    Visitador TEXT DEFAULT 'No aplica',
    Referencia TEXT DEFAULT 'No aplica',
    Telefono_ref TEXT DEFAULT 'No aplica'
    -- FK a propietario será agregada si decidimos la tabla objetivo real
);
"""

create_cuentas = """
CREATE TABLE cuentas (
    ID SERIAL PRIMARY KEY,
    Nombre_cuenta TEXT,
    Llave TEXT UNIQUE
);
"""

create_otras_deudas = """
CREATE TABLE otras_deudas (
    id SERIAL PRIMARY KEY,
    Cedula TEXT NOT NULL,
    Placa TEXT,
    Fecha_deuda DATE,
    Descripcion TEXT,
    Valor REAL,
    FOREIGN KEY (Cedula) REFERENCES clientes (Cedula)
);
"""

create_propietario = """
CREATE TABLE propietario (
    ID SERIAL PRIMARY KEY,
    Placa TEXT,
    Modelo TEXT,
    Color TEXT,
    Tipo TEXT DEFAULT 'Nueva',
    Tarjeta_propiedad TEXT
);
"""

create_registros = """
CREATE TABLE registros (
    id SERIAL PRIMARY KEY,
    Fecha_sistema DATE NOT NULL,
    Fecha_registro DATE NOT NULL,
    Cedula TEXT NOT NULL,
    Nombre TEXT NOT NULL,
    Placa TEXT,
    Valor REAL CHECK (Valor >= 0),
    Saldos REAL CHECK (Saldos >= 0),
    Tipo TEXT NOT NULL,
    Nombre_cuenta TEXT,
    Referencia TEXT,
    Verificada TEXT,
    FOREIGN KEY (Cedula) REFERENCES clientes(Cedula) ON DELETE CASCADE
    -- FK a propietario_old omitida por ahora
);
"""

# Ejecutar creación
cur.execute(create_clientes)
cur.execute(create_cuentas)
cur.execute(create_otras_deudas)
cur.execute(create_propietario)
cur.execute(create_registros)

conn.commit()
cur.close()
conn.close()

print("Tablas creadas con éxito en Railway 🚀")

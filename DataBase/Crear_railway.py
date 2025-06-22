import psycopg2
from dotenv import load_dotenv
import os

# Cargar las variables de entorno
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

schema_sql = """
CREATE TABLE IF NOT EXISTS cuentas (
    id SERIAL PRIMARY KEY,
    nombre_cuenta VARCHAR(100) UNIQUE NOT NULL,
    llave VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS propietario (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(20) UNIQUE NOT NULL,
    modelo VARCHAR(50),
    color VARCHAR(30),
    tipo VARCHAR(50),
    tarjeta_propiedad VARCHAR(100),
    cuenta VARCHAR(100),
    FOREIGN KEY (cuenta) REFERENCES cuentas(nombre_cuenta)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS clientes (
    cedula VARCHAR(20) PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    nacionalidad VARCHAR(50),
    telefono VARCHAR(30),
    direccion TEXT,
    placa VARCHAR(20),  -- SIN restricción FOREIGN KEY aquí
    fecha_inicio DATE,
    fecha_final TEXT,
    tipo_contrato VARCHAR(50),
    valor_cuota NUMERIC(12, 2),
    estado VARCHAR(20),
    otras_deudas NUMERIC(12, 2),
    visitador VARCHAR(100),
    referencia VARCHAR(100),
    telefono_ref VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS registros (
    id SERIAL PRIMARY KEY,
    fecha_sistema DATE NOT NULL,
    fecha_registro DATE,
    cedula VARCHAR(20),
    nombre VARCHAR(100),
    placa VARCHAR(20),  -- SIN restricción FOREIGN KEY
    valor NUMERIC(12, 2),
    saldos NUMERIC(12, 2),
    motivo TEXT,
    tipo VARCHAR(50),
    nombre_cuenta VARCHAR(100),
    referencia VARCHAR(100),
    verificada TEXT,
    FOREIGN KEY (cedula) REFERENCES clientes(cedula)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (nombre) REFERENCES clientes(nombre)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (nombre_cuenta) REFERENCES cuentas(nombre_cuenta)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS otras_deudas (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    placa VARCHAR(20),
    fecha_deuda DATE,
    descripcion TEXT,
    valor NUMERIC(12, 2),
    FOREIGN KEY (cedula) REFERENCES clientes(cedula)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (placa) REFERENCES propietario(placa)
        ON DELETE SET NULL ON UPDATE CASCADE
);
"""

def crear_esquema():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
                conn.commit()
                print("✅ Base de datos y tablas creadas exitosamente.")
    except Exception as e:
        print("❌ Error al crear la base de datos:", e)

if __name__ == "__main__":
    crear_esquema()

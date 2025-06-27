import os
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from sqlalchemy import create_engine
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

# ---------- DB Connection ----------
def get_engine():
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "cUVmSghVIpRTJkWWtUymoMaadGwzLKUn")
    host = os.getenv("DB_HOST", "shuttle.proxy.rlwy.net")
    port = os.getenv("DB_PORT", "38698")
    dbname = os.getenv("DB_NAME", "railway")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)

# ---------- Cálculo de recaudo esperado ----------
def calcular_recaudo_esperado(fecha_inicio, fecha_fin):
    engine = get_engine()
    query = """
        SELECT fecha_inicio::date, valor_cuota
        FROM clientes
        WHERE valor_cuota IS NOT NULL
    """
    df_clientes = pd.read_sql(query, engine)
    df_clientes["fecha_inicio"] = pd.to_datetime(df_clientes["fecha_inicio"])

    dias = pd.date_range(fecha_inicio, fecha_fin)
    esperado_por_dia = []

    for dia in dias:
        activos = df_clientes[df_clientes["fecha_inicio"] <= pd.Timestamp(dia)]
        total = activos["valor_cuota"].sum()
        esperado_por_dia.append({"fecha": dia.date(), "esperado": total})

    return pd.DataFrame(esperado_por_dia)



# ---------- Cálculo de recaudo real ----------
def calcular_recaudo_real(fecha_inicio, fecha_fin):
    engine = get_engine()
    query = """
        SELECT fecha_registro::date AS fecha, SUM(valor) AS total
        FROM registros
        WHERE fecha_registro BETWEEN %s AND %s
        GROUP BY fecha
        ORDER BY fecha
    """
    return pd.read_sql(query, engine, params=(fecha_inicio, fecha_fin))

# ---------- Crear interfaz ----------
def crear_grafico_comparativo():
    ventana = tk.Tk()
    ventana.title("Recaudo: Real vs Esperado")
    ventana.geometry("1000x600")

    frame_filtros = tk.Frame(ventana)
    frame_filtros.pack(pady=10)

    tk.Label(frame_filtros, text="Desde:", font=("Arial", 12)).pack(side="left")
    entry_fecha = DateEntry(frame_filtros, width=12, background="darkblue", foreground="white",
                            borderwidth=2, date_pattern="yyyy-mm-dd")
    entry_fecha.set_date(datetime.now())
    entry_fecha.pack(side="left", padx=5)

    btn_generar = tk.Button(frame_filtros, text="Generar Gráfico")
    btn_generar.pack(side="left", padx=10)

    frame_grafico = tk.Frame(ventana)
    frame_grafico.pack(fill="both", expand=True)

    def generar():
        for widget in frame_grafico.winfo_children():
            widget.destroy()

        fecha_fin = entry_fecha.get_date()
        fecha_inicio = fecha_fin - timedelta(days=6)

        df_real = calcular_recaudo_real(fecha_inicio, fecha_fin)
        df_esperado = calcular_recaudo_esperado(fecha_inicio, fecha_fin)

        df_final = pd.merge(df_esperado, df_real, on="fecha", how="left")
        df_final["total"] = df_final["total"].fillna(0)

        fig, ax = plt.subplots(figsize=(10, 5))

        ax.bar(df_final["fecha"], df_final["esperado"], label="Esperado", alpha=0.7, color="skyblue")
        ax.bar(df_final["fecha"], df_final["total"], label="Recaudado", alpha=0.7, color="seagreen")

        # Etiquetas de valores
        for i, row in df_final.iterrows():
            ax.text(row["fecha"], row["esperado"] + 500, f"{row['esperado']:,.0f}", ha='center', fontsize=9, color="blue")
            ax.text(row["fecha"], row["total"] + 500, f"{row['total']:,.0f}", ha='center', fontsize=9, color="green")

        ax.set_title("Recaudo real vs esperado", fontsize=14, fontweight='bold')
        ax.set_ylabel("Valor")
        ax.set_xlabel("Fecha")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    btn_generar.config(command=generar)
    ventana.mainloop()

# ---------- Ejecutar ----------
if __name__ == "__main__":
    crear_grafico_comparativo()

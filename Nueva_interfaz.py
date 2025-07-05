import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from sqlalchemy import select, and_
from conexion import engine,clientes as tabla_clientes, otras_deudas as tabla_otras_deudas, registros as tabla_registros


# --- FUNCIONES ---
def cargar_clientes(filtro=""):
    tree_clientes.delete(*tree_clientes.get_children())
    with engine.begin() as conn:
        stmt = select(tabla_clientes.c.nombre, tabla_clientes.c.placa, tabla_clientes.c.cedula)
        if filtro:
            stmt = stmt.where(tabla_clientes.c.nombre.ilike(f"%{filtro}%"))
        stmt = stmt.order_by(tabla_clientes.c.placa)
        for nombre, placa, cedula in conn.execute(stmt):
            tree_clientes.insert("", "end", values=(nombre, placa), tags=(cedula, placa, nombre))

def cargar_deudas(cedula, placa):
    tree_deudas.delete(*tree_deudas.get_children())
    total = 0
    with engine.begin() as conn:
        stmt = select(tabla_otras_deudas).where(
            tabla_otras_deudas.c.cedula == cedula,
            tabla_otras_deudas.c.placa == placa
        ).order_by(tabla_otras_deudas.c.fecha_deuda.desc())
        for row in conn.execute(stmt):
            tree_deudas.insert("", "end", values=(
                row.id, row.fecha_deuda, row.descripcion, f"$ {row.valor:,.0f}"
            ))
            total += float(row.valor)
    resumen_total_deudas.set(f"Total Deudas: $ {total:,.0f}")
    actualizar_resumen()

def cargar_abonos(nombre, placa):
    tree_abonos.delete(*tree_abonos.get_children())
    total = 0
    with engine.begin() as conn:
        stmt = select(
            tabla_registros.c.fecha_registro,
            tabla_registros.c.saldos,
            tabla_registros.c.motivo,
            tabla_registros.c.tipo
        ).where(
            and_(
                tabla_registros.c.nombre == nombre,
                tabla_registros.c.placa == placa,
                tabla_registros.c.saldos > 0,
                tabla_registros.c.motivo.notin_(["N-a", "Multa"])
            )
        ).order_by(tabla_registros.c.fecha_registro.desc())
        for row in conn.execute(stmt):
            tree_abonos.insert("", "end", values=(
                row.fecha_registro, f"$ {row.saldos:,.0f}", row.motivo, row.tipo
            ))
            total += float(row.saldos)
    resumen_total_abonos.set(f"Total Abonos: $ {total:,.0f}")
    actualizar_resumen()

def actualizar_resumen():
    try:
        total_deuda = float(resumen_total_deudas.get().replace("Total Deudas: $ ", "").replace(",", ""))
        total_abonos = float(resumen_total_abonos.get().replace("Total Abonos: $ ", "").replace(",", ""))
        resumen_deuda_actual.set(f"Deuda Actual: $ {total_deuda - total_abonos:,.0f}")
    except:
        pass

def on_cliente_dobleclick(event):
    selected = tree_clientes.focus()
    if not selected:
        return
    cedula, placa, nombre = tree_clientes.item(selected, "tags")
    cargar_deudas(cedula, placa)
    cargar_abonos(nombre, placa)

def eliminar_deuda():
    selected = tree_deudas.selection()
    if not selected:
        messagebox.showwarning("Sin selección", "Selecciona una deuda para eliminar.")
        return

    confirm = messagebox.askyesno("Confirmar eliminación", "¿Estás seguro de eliminar esta deuda?")
    if not confirm:
        return

    item = tree_deudas.item(selected[0])
    id_deuda = item["values"][0]
    try:
        with engine.begin() as conn:
            conn.execute(tabla_otras_deudas.delete().where(tabla_otras_deudas.c.id == id_deuda))
        tree_deudas.delete(selected[0])
        item_cliente = tree_clientes.focus()
        if item_cliente:
            cedula, placa, nombre = tree_clientes.item(item_cliente, "tags")
            cargar_deudas(cedula, placa)
            cargar_abonos(nombre, placa)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo eliminar la deuda:\n{e}")

def agregar_deuda():
    item_cliente = tree_clientes.focus()
    if not item_cliente:
        messagebox.showwarning("Selecciona un cliente", "Debes seleccionar un cliente primero.")
        return

    cedula, placa, nombre = tree_clientes.item(item_cliente, "tags")

    def guardar():
        descripcion = entry_desc.get().strip()
        valor = entry_valor.get().strip()
        if not descripcion or not valor:
            messagebox.showerror("Campos vacíos", "Todos los campos son obligatorios.")
            return
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Valor inválido", "El valor debe ser un número.")
            return
        try:
            with engine.begin() as conn:
                conn.execute(tabla_otras_deudas.insert().values(
                    cedula=cedula,
                    placa=placa,
                    fecha_deuda=date.today(),
                    descripcion=descripcion,
                    valor=valor_float
                ))
            top.destroy()
            cargar_deudas(cedula, placa)
            cargar_abonos(nombre, placa)
            messagebox.showinfo("Éxito", "Deuda agregada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la deuda.\n{e}")

    top = tk.Toplevel(ventana)
    top.title("Agregar Deuda")
    top.geometry("300x180")
    top.resizable(False, False)
    tk.Label(top, text=f"Cliente: {nombre}", font=("Arial", 10, "bold")).pack(pady=5)
    tk.Label(top, text="Descripción:").pack()
    entry_desc = tk.Entry(top, width=30, justify="center")
    entry_desc.pack(pady=3)
    tk.Label(top, text="Valor ($COP):").pack()
    entry_valor = tk.Entry(top, width=20, justify="center")
    entry_valor.pack(pady=3)
    tk.Button(top, text="Guardar", bg="#4CAF50", fg="white", command=guardar).pack(pady=10)

# --- INTERFAZ PRINCIPAL ---
ventana = tk.Tk()
ventana.title("Gestión de Deudas")
ventana.geometry("1200x700")
ventana.configure(bg="white")

# --- Configuración general del grid ---
ventana.grid_rowconfigure(1, weight=1)
ventana.grid_columnconfigure(1, weight=1)

# Panel superior (izquierda): Filtro + Botones + Resumen
frame_izq_superior = tk.Frame(ventana, bg="white")
frame_izq_superior.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
frame_izq_superior.grid_columnconfigure(0, weight=1)

# Filtro
frame_filtro = tk.Frame(frame_izq_superior, bg="white")
frame_filtro.grid(row=0, column=0, sticky="w", pady=2)
tk.Label(frame_filtro, text="Filtrar por nombre:", font=("Arial", 10, "bold"), bg="white").grid(row=0, column=0, sticky="w")
entry_filtro = tk.Entry(frame_filtro, width=40)
entry_filtro.grid(row=0, column=1, padx=10)
entry_filtro.bind("<KeyRelease>", lambda e: cargar_clientes(entry_filtro.get()))

# Botones de deuda
frame_botones = tk.Frame(frame_izq_superior, bg="white")
frame_botones.grid(row=1, column=0, sticky="w", pady=5)
tk.Button(frame_botones, text="➕ Agregar Deuda", bg="#3498db", fg="white", command=agregar_deuda).grid(row=0, column=0, padx=5)
tk.Button(frame_botones, text="🗑️ Eliminar Deuda", bg="#e74c3c", fg="white", command=eliminar_deuda).grid(row=0, column=1, padx=5)

# Resumen
frame_resumen = tk.Frame(frame_izq_superior, bg="white")
frame_resumen.grid(row=2, column=0, sticky="w")
resumen_total_deudas = tk.StringVar()
resumen_total_abonos = tk.StringVar()
resumen_deuda_actual = tk.StringVar()

for i, (text_var, fg) in enumerate(zip(
    [resumen_total_deudas, resumen_total_abonos, resumen_deuda_actual],
    ["darkred", "darkgreen", "blue"])):
    tk.Label(frame_resumen, textvariable=text_var, font=("Arial", 10, "bold"), fg=fg, bg="white").grid(row=i, column=0, sticky="w", pady=1)

# Panel superior derecho - Deudas
frame_deudas = tk.Frame(ventana, bg="white")
frame_deudas.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
frame_deudas.grid_rowconfigure(0, weight=1)
frame_deudas.grid_columnconfigure(0, weight=1)

cols_deudas = ("ID", "Fecha", "Descripción", "Valor")
tree_deudas = ttk.Treeview(frame_deudas, columns=cols_deudas, show="headings")
for col in cols_deudas:
    tree_deudas.heading(col, text=col)
    tree_deudas.column(col, anchor="center")

scroll_deudas = ttk.Scrollbar(frame_deudas, orient="vertical", command=tree_deudas.yview)
tree_deudas.configure(yscrollcommand=scroll_deudas.set)

tree_deudas.grid(row=0, column=0, sticky="nsew")
scroll_deudas.grid(row=0, column=1, sticky="ns")

# Panel inferior izquierdo - Clientes
frame_clientes = tk.Frame(ventana, bg="white")
frame_clientes.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
frame_clientes.grid_rowconfigure(0, weight=1)
frame_clientes.grid_columnconfigure(0, weight=1)

cols_clientes = ("Nombre", "Placa")
tree_clientes = ttk.Treeview(frame_clientes, columns=cols_clientes, show="headings")
for col in cols_clientes:
    tree_clientes.heading(col, text=col)
    tree_clientes.column(col, anchor="center")

scroll_clientes = ttk.Scrollbar(frame_clientes, orient="vertical", command=tree_clientes.yview)
tree_clientes.configure(yscrollcommand=scroll_clientes.set)

tree_clientes.grid(row=0, column=0, sticky="nsew")
scroll_clientes.grid(row=0, column=1, sticky="ns")

tree_clientes.bind("<Double-1>", on_cliente_dobleclick)

# Panel inferior derecho - Abonos
frame_abonos = tk.Frame(ventana, bg="white")
frame_abonos.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
frame_abonos.grid_rowconfigure(0, weight=1)
frame_abonos.grid_columnconfigure(0, weight=1)

cols_abonos = ("Fecha", "Saldos", "Motivo", "Tipo")
tree_abonos = ttk.Treeview(frame_abonos, columns=cols_abonos, show="headings")
for col in cols_abonos:
    tree_abonos.heading(col, text=col)
    tree_abonos.column(col, anchor="center")

scroll_abonos = ttk.Scrollbar(frame_abonos, orient="vertical", command=tree_abonos.yview)
tree_abonos.configure(yscrollcommand=scroll_abonos.set)

tree_abonos.grid(row=0, column=0, sticky="nsew")
scroll_abonos.grid(row=0, column=1, sticky="ns")
# --- CARGAR CLIENTES AL INICIAR ---


# Cargar inicial
cargar_clientes()

ventana.mainloop()

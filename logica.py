import pandas as pd
import tkinter as tk
import tkinter.font as tkFont
from tkinter import font
from tkinter import filedialog, messagebox, ttk
import sqlite3
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, time
from tkcalendar import DateEntry
import locale
from tkinter import filedialog
import math
from PIL import ImageGrab
import io
import win32clipboard
import json
from openpyxl import Workbook
import ctypes
from tkinter import Toplevel
import psycopg2

# Configuración de rutas
BLACKLIST_PATH = "diccionarios/black_list.json"
DB_PATH = "diccionarios/base_dat.db"
JSON_PATH = 'diccionarios/columnas.json'
XLSX_PATH = 'diccionarios/estructura.xlsx'
# Cargar las variables del archivo .env
load_dotenv()
# Acceder a las variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
# Establecer configuraciones locales - español
locale.setlocale(locale.LC_ALL, 'es_CO.utf8')
ventana_clientes = None  # Variable global dentro del módulo

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def cargar_db(tree, entry_cedula, entry_nombre, entry_placa, entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada):
    try:
        # Obtener los valores de los widgets
        cedula = entry_cedula.get()
        nombre = entry_nombre.get()
        placa = entry_placa.get()
        referencia = entry_referencia.get()
        fecha = entry_fecha.get()
        tipo = combo_tipo.get()
        nequi = combo_nequi.get()
        verificada = combo_verificada.get()

        if fecha:
            fecha = datetime.strptime(fecha, "%d-%m-%Y").strftime("%Y-%m-%d")

        # Conectar a PostgreSQL en Railway
        conn = get_connection()
        cursor = conn.cursor()

        # Armar query
        query = """
            SELECT r.id, r.Fecha_sistema, r.Fecha_registro, r.Cedula, r.Nombre, 
                   r.Placa, r.Valor, r.Saldos, r.Tipo, r.Nombre_cuenta, 
                   r.Referencia, r.Verificada
            FROM registros r
            LEFT JOIN propietario p ON r.Placa = p.Placa
            WHERE 1=1
        """
        params = []

        if cedula:
            query += " AND r.Cedula = %s"
            params.append(cedula)
        if nombre:
            query += " AND r.Nombre ILIKE %s"
            params.append(f"%{nombre}%")
        if placa:
            query += " AND r.Placa ILIKE %s"
            params.append(f"%{placa}%")
        if referencia:
            query += " AND r.Referencia ILIKE %s"
            params.append(f"%{referencia}%")
        if fecha:
            query += " AND r.Fecha_registro = %s"
            params.append(fecha)
        if tipo:
            query += " AND r.Tipo = %s"
            params.append(tipo)
        if nequi:
            query += " AND r.Nombre_cuenta = %s"
            params.append(nequi)
        if verificada:
            query += " AND r.Verificada = %s"
            params.append(verificada)

        # Ejecutar la consulta
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Limpiar el TreeView
        for row in tree.get_children():
            tree.delete(row)

        # Ordenar por Cedula y Fecha_sistema
        rows.sort(key=lambda x: (str(x[3]), str(x[1])))

        for row in rows:
            fecha_sistema = pd.to_datetime(row[1]).strftime('%d-%m-%Y')
            fecha_registro = pd.to_datetime(row[2]).strftime('%d-%m-%Y')

            values = list(row)
            values[1] = fecha_sistema
            values[2] = fecha_registro

            tree.insert("", "end", values=values)

        # Ajustar columnas automáticamente
        for col in tree["columns"]:
            max_width = max([tkFont.Font().measure(col)] + [tkFont.Font().measure(str(value)) for value in rows])
            tree.column(col, width=max_width)

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar los datos desde PostgreSQL: {e}")

def agregar_registro(tree, entry_hoy, entry_cedula, entry_nombre, entry_placa, entry_monto, entry_saldos,
                     entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada,
                     listbox_sugerencias, entry_deuda):
    
    # Obtener valores
    cedula = entry_cedula.get().strip()
    nombre = entry_nombre.get().strip()
    placa = entry_placa.get().strip()
    valor = entry_monto.get().strip()
    saldos = entry_saldos.get().strip()
    referencia = entry_referencia.get().strip()
    fecha_hoy = entry_hoy.get().strip()
    fecha = entry_fecha.get().strip()
    tipo = combo_tipo.get().strip()
    nequi = combo_nequi.get().strip()
    verificada = "No"  # 🔒 Valor fijo

    # Validación
    campos_faltantes = []
    if not cedula: campos_faltantes.append("Cédula")
    if not nombre: campos_faltantes.append("Nombre")
    if not placa: campos_faltantes.append("Placa")
    if not valor: campos_faltantes.append("Valor")
    if not saldos: campos_faltantes.append("Saldos")
    if not fecha_hoy: campos_faltantes.append("Fecha de hoy")
    if not fecha: campos_faltantes.append("Fecha de registro")
    if not tipo: campos_faltantes.append("Tipo")
    if not verificada: campos_faltantes.append("Verificada")
    if tipo.lower() not in ["efectivo", "ajuste p/p"]:
        if not referencia: campos_faltantes.append("Referencia")
        if not nequi: campos_faltantes.append("Nequi")

    if campos_faltantes:
        mensaje_error = "Faltan valores obligatorios:\n- " + "\n- ".join(campos_faltantes)
        messagebox.showerror("Error", mensaje_error)
        return

    try:
        # ⚙️ Conexión PostgreSQL
        conn = get_connection()
        cursor = conn.cursor()

        # Validar referencia duplicada
        if referencia:
            cursor.execute("SELECT Referencia, Cedula, Nombre FROM registros WHERE Referencia = %s", (referencia,))
            registro_existente = cursor.fetchone()
            if registro_existente:
                ref, ced, nom = registro_existente
                messagebox.showwarning("Referencia duplicada", 
                    f"El registro con referencia '{ref}' ya existe.\n"
                    f"Cédula: {ced}\nNombre: {nom}\n\nNo se guardará el nuevo registro.")
                conn.close()
                return

        # Validar combinación única
        cursor.execute("SELECT COUNT(*) FROM clientes WHERE Cedula = %s AND Nombre = %s AND Placa = %s", (cedula, nombre, placa))
        count = cursor.fetchone()[0]
        if count != 1:
            messagebox.showerror("Error", "La combinación de cédula, nombre y placa no es única o no existe en la base de datos.")
            conn.close()
            return

        try:
            valor = float(valor)
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser numérico.")
            conn.close()
            return

        if not saldos:
            saldos = "0"
        try:
            saldos = float(saldos)
        except ValueError:
            messagebox.showerror("Error", "El campo 'Saldos' debe ser numérico.")
            conn.close()
            return

        fecha_hoy_bd = convertir_fecha(fecha_hoy)
        fecha_bd = convertir_fecha(fecha)
        if fecha_hoy_bd is None or fecha_bd is None:
            conn.close()
            return

        confirmar = messagebox.askyesno("Confirmar", "¿Deseas grabar este registro?")
        if confirmar:
            cursor.execute("""
                INSERT INTO registros (
                    Fecha_sistema, Fecha_registro, Cedula, Nombre, Placa, Valor, Saldos, Tipo, Nombre_cuenta, Referencia, Verificada
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                fecha_hoy_bd, fecha_bd, cedula, nombre, placa, valor, saldos,
                tipo, nequi, referencia, verificada
            ))
            conn.commit()

            mostrar_msgbox_exito(entry_cedula, lambda: limpiar_formulario(
                entry_cedula, entry_nombre, entry_placa, entry_monto, entry_saldos,
                entry_referencia, entry_fecha, combo_tipo, combo_nequi, combo_verificada,
                listbox_sugerencias, entry_deuda, tree
            ))
        else:
            messagebox.showinfo("Cancelado", "La operación fue cancelada.")
        conn.close()

    except psycopg2.Error as e:
        messagebox.showerror("Error", f"Error en base de datos: {e}")
        if conn:
            conn.close()

def mostrar_msgbox_exito(entry_cedula, limpiar_funcion):
    ventana = Toplevel()
    ventana.title("Éxito")
    ventana.geometry("350x150")
    ventana.resizable(False, False)
    ventana.grab_set()  # Ventana modal
    label = tk.Label(ventana, text="Registro agregado correctamente.", font=("Arial", 12))
    label.pack(pady=20)
    botones_frame = tk.Frame(ventana)
    botones_frame.pack(pady=10)
    btn_generar = tk.Button(botones_frame, text="Generar Recibo", width=15,
    command=lambda: [
        mostrar_registros(entry_cedula),
        limpiar_funcion(),
        ventana.destroy()
    ])
    btn_generar.pack(side="left", padx=10)
    btn_aceptar = tk.Button(botones_frame, text="No generar", width=10,
                            command=lambda: [limpiar_funcion(), ventana.destroy()])
    btn_aceptar.pack(side="right", padx=10)

def limpiar_formulario(entry_cedula, entry_nombre, entry_placa, entry_monto, entry_saldos, entry_referencia, entry_fecha,
combo_tipo, combo_nequi, combo_verificada, listbox_sugerencias, entry_deuda, tree):
    # Limpiar campos de texto (Entry)
    entry_cedula.focus_set()
    entry_cedula.delete(0, tk.END)
    entry_nombre.delete(0, tk.END)
    entry_placa.delete(0, tk.END)
    entry_monto.delete(0, tk.END)
    entry_saldos.delete(0, tk.END)
    entry_referencia.delete(0, tk.END)
    entry_fecha.delete(0, tk.END)
    entry_deuda.delete(0, tk.END)
    
    # Limpiar los Combobox
    combo_tipo.set('')  # Resetear el ComboBox de Tipo
    combo_nequi.set('')  # Resetear el ComboBox de Nequi
    combo_verificada.set('No')  # Resetear el ComboBox de Verificada
    listbox_sugerencias.grid_forget()
    
    # Limpiar Treeview
    for row in tree.get_children():
        tree.delete(row)
        
    # Colocar el enfoque en entry_cedula

def cargar_nequi_opciones():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT nombre_cuenta FROM cuentas")
        rows = cursor.fetchall()

        nequi_opciones = [row[0] for row in rows]

        cursor.close()
        conn.close()

        return nequi_opciones

    except Exception as e:
        print(f"Error al cargar los datos: {e}")
        return []

def convertir_fecha(fecha_str):
    """Convierte una fecha de formato dd-mm-yyyy a yyyy-mm-dd."""
    try:
        return datetime.strptime(fecha_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Error", "Formato de fecha incorrecto. Use dd-mm-yyyy.")
        return None

def ajustar_columnas(tree):
    """Ajusta automáticamente el ancho de las columnas en función del contenido."""
    for col in tree["columns"]:
        tree.column(col, anchor="center")  # Justificar contenido al centro
        max_len = len(col)  # Inicia con el ancho del encabezado
        for item in tree.get_children():
            text = str(tree.item(item, "values")[tree["columns"].index(col)])
            max_len = max(max_len, len(text))
        tree.column(col, width=max_len * 10)  # Ajusta el ancho en función del contenido

def obtener_datos_clientes():
    """Obtiene los datos de la tabla clientes desde la base de datos PostgreSQL y formatea Capital y Fecha_inicio."""
    try:
        conexion = get_connection()
        cursor = conexion.cursor()
        
        # Consulta SQL
        query = """
            SELECT 
                c.cedula, c.nombre, c.nacionalidad, c.telefono, c.direccion, 
                c.placa, p.modelo, p.tarjeta_propiedad, 
                c.fecha_inicio, c.fecha_final, c.tipo_contrato, c.valor_cuota, 
                c.estado, c.otras_deudas, c.visitador, c.referencia, c.telefono_ref
            FROM clientes c 
            LEFT JOIN propietario p ON c.placa = p.placa;
        """

        cursor.execute(query)
        datos = cursor.fetchall()

        # Formatear los datos
        datos_formateados = []
        for fila in datos:
            (
                cedula, nombre, nacionalidad, telefono, direccion, 
                placa, modelo, tarjeta_propiedad, fecha_inicio, fecha_final, 
                tipo_contrato, valor_cuota, estado, otras_deudas, 
                visitador, referencia, telefono_ref
            ) = fila

            # Formatear la fecha si existe
            if fecha_inicio:
                try:
                    fecha_inicio = fecha_inicio.strftime("%d-%m-%Y")
                except Exception:
                    fecha_inicio = "Formato Inválido"
            
            datos_formateados.append((
                cedula, nombre, nacionalidad, telefono, direccion, 
                placa, modelo, tarjeta_propiedad, fecha_inicio, fecha_final, 
                tipo_contrato, valor_cuota, estado, otras_deudas, 
                visitador, referencia, telefono_ref
            ))

        return datos_formateados

    except psycopg2.Error as e:
        print(f"Error al obtener datos de clientes: {e}")
        return []

    finally:
        if conexion:
            cursor.close()
            conexion.close()

def abrir_ventana_clientes():
    
    global ventana_clientes

    if ventana_clientes and ventana_clientes.winfo_exists():
        ventana_clientes.lift()  # Trae la ventana al frente si ya existe
        return
    
    ventana_clientes = tk.Toplevel()
    ventana_clientes.title("Clientes")
    ventana_clientes.geometry("900x600")
    icono_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'inicio.ico')
    if os.path.exists(icono_path):
        ventana_clientes.iconbitmap(icono_path)
    else:
        print("No se encontró el icono en la ruta especificada")

    # Crear un Frame para contener el Treeview y la Scrollbar
    frame_tree = ttk.Frame(ventana_clientes)
    frame_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

    # Crear el Treeview dentro del Frame
    columnas = ("Cédula", "Nombre","Nacionalidad", "Teléfono", "Dirección", 
                "Placa","Modelo","Tarjeta propiedad", "Fecha Inicio", "Fecha Final", "Tipo Contrato", "Valor Cuota", "Estado", "Total_inicial", "Visitador", "Referencia", "Telefono_ref")

    tree = ttk.Treeview(frame_tree, columns=columnas, show="headings")

    # Configurar encabezados y justificar contenido al centro
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")

    # Crear Scrollbar dentro del Frame
    scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    # Ubicar Treeview y Scrollbar con grid dentro del Frame
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Configurar expansión del Frame
    frame_tree.columnconfigure(0, weight=1)
    frame_tree.rowconfigure(0, weight=1)

    # Llenar el Treeview con datos de la base de datos
    for fila in obtener_datos_clientes():
        tree.insert("", "end", values=fila)
    # Ajustar automáticamente el ancho de las columnas después de insertar los datos
    ajustar_columnas(tree)
    
    global datos_originales
    datos_originales = [tree.item(item)["values"] for item in tree.get_children()]
    
    # Función para configurar correctamente los DateEntry
    def create_date_entry(parent):
        return DateEntry(parent, width=27, background='darkblue', 
                        foreground='white', borderwidth=2, 
                        date_pattern='dd-MM-yyyy',  # Establecer el formato Día-Mes-Año
                        locale='es_ES')

    # Frame para los Labels y Entries
    frame_form = ttk.LabelFrame(ventana_clientes, text="Información del Cliente")
    frame_form.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

    # Diccionario para almacenar las entradas
    entries = {}
    
    cedula_var = tk.StringVar()
    # Función para validar que solo sean números (Si son letras las borra)
    def validar_cedula(*args):
        valor = cedula_var.get()
        if not valor.isdigit():
            cedula_var.set("".join(filter(str.isdigit, valor)))  # Elimina caracteres no numéricos

    # Agregando manualmente cada etiqueta y entrada en un diseño de 3 columnas
    cedula_var.trace_add("write", validar_cedula)
    lbl_cedula = ttk.Label(frame_form, text="Cédula:")
    lbl_cedula.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    entries["Cédula"] = ttk.Entry(frame_form, textvariable=cedula_var, width=30)
    entries["Cédula"].grid(row=0, column=1, padx=5, pady=5, sticky="w")

    nombre_var = tk.StringVar()
    nombre_var.trace_add("write", lambda *args: nombre_var.set(nombre_var.get().title()))
    nombre_var.trace_add("write", lambda *args: filtrar_treeview(tree, nombre_var))
    lbl_nombre = ttk.Label(frame_form, text="Nombre:")
    lbl_nombre.grid(row=0, column=2, padx=5, pady=5, sticky="w")
    
    def filtrar_treeview(tree, nombre_var):
        filtro = nombre_var.get().strip().lower()
        items = tree.get_children()

        if not filtro:
            tree.delete(*items)
            for fila in datos_originales:
                tree.insert("", "end", values=fila)
            return

        tree.delete(*items)
        for fila in datos_originales:
            if filtro in fila[1].lower():
                tree.insert("", "end", values=fila)
    
    def consultar_datos_vehiculo(*args):
        placa = placa_var.get()
        if not placa:
            return

        # Conectamos a la base de datos de PostgreSQL
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT modelo, tarjeta_propiedad FROM propietario WHERE placa = %s",
                (placa,)
            )
            resultado = cursor.fetchone()

            if resultado:
                modelo, tarjeta = resultado

                entries["Modelo"].config(state="normal")
                entries["Modelo"].delete(0, tk.END)
                entries["Modelo"].insert(0, modelo)
                entries["Modelo"].config(state="readonly")

                entries["Tarjeta_propiedad"].config(state="normal")
                entries["Tarjeta_propiedad"].delete(0, tk.END)
                entries["Tarjeta_propiedad"].insert(0, tarjeta)
                entries["Tarjeta_propiedad"].config(state="readonly")

        except Exception as e:
            print(f"Error al consultar el vehículo: {e}")

        finally:
            cursor.close()
            conn.close()

    entries["Nombre"] = ttk.Entry(frame_form, textvariable=nombre_var, width=30)
    entries["Nombre"].grid(row=0, column=3, padx=5, pady=5, sticky="w")
    nacion_var = tk.StringVar()
    nacion_var.trace_add("write", lambda *args: nacion_var.set(nacion_var.get().title()))
    lbl_nacion = ttk.Label(frame_form, text="Nacionalidad:")
    lbl_nacion.grid(row=0, column=4, padx=4, pady=5, sticky="w")
    entries["Nacionalidad"] = ttk.Entry(frame_form, textvariable=nacion_var, width=30)
    entries["Nacionalidad"].grid(row=0, column=5, padx=5, pady=5, sticky="w")
    lbl_telefono = ttk.Label(frame_form, text="Teléfono:")
    lbl_telefono.grid(row=1, column=0, padx=0, pady=5, sticky="w")
    entries["Teléfono"] = ttk.Entry(frame_form, width=30)
    entries["Teléfono"].grid(row=1, column=1, padx=5, pady=5, sticky="w")
    lbl_direccion = ttk.Label(frame_form, text="Dirección:")
    lbl_direccion.grid(row=1, column=2, padx=5, pady=5, sticky="w")
    entries["Dirección"] = ttk.Entry(frame_form, width=30)
    entries["Dirección"].grid(row=1, column=3, padx=5, pady=5, sticky="w")
    placa_var = tk.StringVar()
    placa_var.trace_add("write", lambda *args: placa_var.set(placa_var.get().upper()))
    placa_var.trace_add("write", consultar_datos_vehiculo)  # Consultar modelo y tarjeta
    lbl_placa = ttk.Label(frame_form, text="Placa:")
    lbl_placa.grid(row=1, column=4, padx=5, pady=5, sticky="w")
    entries["Placa"] = ttk.Entry(frame_form, textvariable=placa_var, width=30)
    entries["Placa"].grid(row=1, column=5, padx=5, pady=5, sticky="w")
    lbl_modelo = ttk.Label(frame_form, text="Modelo:")
    lbl_modelo.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    entries["Modelo"] = ttk.Entry(frame_form, width=30, state="readonly")
    entries["Modelo"].grid(row=2, column=1, padx=5, pady=5, sticky="w")
    lbl_tarjeta_propiedad = ttk.Label(frame_form, text="Tarjeta Propiedad:")
    lbl_tarjeta_propiedad.grid(row=2, column=2, padx=5, pady=5, sticky="w")
    entries["Tarjeta_propiedad"] = ttk.Entry(frame_form, width=30, state="readonly")
    entries["Tarjeta_propiedad"].grid(row=2, column=3, padx=5, pady=5, sticky="w")
    lbl_fecha_inicio = ttk.Label(frame_form, text="Fecha Inicio:")
    lbl_fecha_inicio.grid(row=2, column=4, padx=5, pady=5, sticky="w")
    entries["Fecha Inicio"] = create_date_entry(frame_form)
    entries["Fecha Inicio"].grid(row=2, column=5, padx=5, pady=5, sticky="w")
    lbl_fecha_final = ttk.Label(frame_form, text="Fecha Final:")
    lbl_fecha_final.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    entries["Fecha Final"] = ttk.Entry(frame_form, width=30)
    entries["Fecha Final"].grid(row=3, column=1, padx=5, pady=5, sticky="w")
    lbl_tipo_contrato = ttk.Label(frame_form, text="Tipo Contrato:")
    lbl_tipo_contrato.grid(row=3, column=2, padx=5, pady=5, sticky="w")
    tipos_opciones = ["Dia", "Semana", "Quincena", "Mes", "Sin asignar"]
    entries["Tipo Contrato"] = ttk.Combobox(frame_form, values=tipos_opciones, state="readonly", width=30)
    entries["Tipo Contrato"].grid(row=3, column=3, padx=5, pady=5, sticky="w")
    lbl_valor_cuota = ttk.Label(frame_form, text="Valor Cuota:")
    lbl_valor_cuota.grid(row=3, column=4, padx=5, pady=5, sticky="w")
    entries["Valor Cuota"] = ttk.Entry(frame_form, width=30)
    entries["Valor Cuota"].grid(row=3, column=5, padx=5, pady=5, sticky="w")
    lbl_estado = ttk.Label(frame_form, text="Estado:")
    lbl_estado.grid(row=0, column=6, padx=5, pady=5, sticky="w")
    estado_opciones = ["","activo", "inactivo"]
    combo_estado = ttk.Combobox(frame_form, values=estado_opciones, width=30)
    combo_estado.grid(row=0, column=7, padx=5, pady=5, sticky="w")
    lbl_otras_deudas = ttk.Label(frame_form, text="Otras deudas:")
    lbl_otras_deudas.grid(row=1, column=6, padx=5, pady=5, sticky="w")
    entries["Otras deudas"] = ttk.Entry(frame_form, width=30)
    entries["Otras deudas"].grid(row=1, column=7, padx=5, pady=5, sticky="w")
    lbl_visitador = ttk.Label(frame_form, text="Visitador:")
    lbl_visitador.grid(row=2, column=6, padx=5, pady=5, sticky="w")
    entries["Visitador"] = ttk.Entry(frame_form, width=30)
    entries["Visitador"].grid(row=2, column=7, padx=5, pady=5, sticky="w")
    lbl_referencia = ttk.Label(frame_form, text="Referencia:")
    lbl_referencia.grid(row=3, column=6, padx=5, pady=5, sticky="w")
    entries["Referencia"] = ttk.Entry(frame_form, width=30)
    entries["Referencia"].grid(row=3, column=7, padx=5, pady=5, sticky="w")
    lbl_tel_referencia = ttk.Label(frame_form, text="Telefono Ref:")
    lbl_tel_referencia.grid(row=3, column=8, padx=5, pady=5, sticky="w")
    entries["Telefono Ref"] = ttk.Entry(frame_form, width=30)
    entries["Telefono Ref"].grid(row=3, column=9, padx=5, pady=5, sticky="w")


    def limpiar_formulario():
        """Limpia todos los campos de entrada en el formulario."""
        for entry in entries.values():
                entry.delete(0, "end")
        
        entries["Tipo Contrato"].set("")  # Resetear el Combobox
        entries["Tarjeta_propiedad"].config(state="normal")
        entries["Tarjeta_propiedad"].delete(0, tk.END)
        entries["Tarjeta_propiedad"].config(state="readonly")
        combo_estado.set("")
        
    def convertir_fecha_formato_sqlite(fecha_ui):
        """Convierte una fecha de formato dd-mm-yyyy a yyyy-mm-dd"""
        try:
            dia, mes, año = fecha_ui.split('-')
            return f"{año}-{mes}-{dia}"
        except ValueError:
            messagebox.showerror("Error", f"Formato de fecha inválido: {fecha_ui}")
            return None

    def registrar_cliente():
        # Obtener valores de los campos
        valores = [
            entries["Cédula"].get().strip(), 
            entries["Nombre"].get().strip(), 
            entries["Nacionalidad"].get().strip(), 
            entries["Teléfono"].get().strip(), 
            entries["Dirección"].get().strip(), 
            entries["Placa"].get().strip(), 
            convertir_fecha_formato_sqlite(entries["Fecha Inicio"].get().strip()), 
            entries["Fecha Final"].get().strip(), 
            entries["Tipo Contrato"].get().strip(), 
            entries["Valor Cuota"].get().strip(), 
            combo_estado.get().strip(), 
            entries["Otras deudas"].get().strip(), 
            entries["Visitador"].get().strip(), 
            entries["Referencia"].get().strip(), 
            entries["Telefono Ref"].get().strip()
        ]

        # Verificar si hay campos vacíos
        if '' in valores:
            messagebox.showerror("Error", "Todos los campos deben estar llenos.")
            ventana_clientes.focus_force()
            return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Validar que la placa esté registrada en la tabla propietario
            cursor.execute("SELECT Placa FROM propietario WHERE Placa = %s LIMIT 1", (valores[5],))
            if not cursor.fetchone():
                messagebox.showwarning("Advertencia", f"La Placa {valores[5]} no está registrada en la base de datos de propietarios.")
                return

            # Validar que el cliente o la placa no esté ya registrada
            cursor.execute("SELECT Cedula, Placa FROM clientes WHERE Cedula = %s OR Placa = %s LIMIT 1", (valores[0], valores[5],))
            resultado = cursor.fetchone()

            if resultado:
                mensaje = "No se puede registrar el cliente porque:\n"
                if resultado[0] == valores[0]:
                    mensaje += f"- La Cédula {resultado[0]} ya está registrada.\n"
                if resultado[1] == valores[5]:
                    mensaje += f"- La Placa {resultado[1]} ya está asignada a otro cliente.\n"
                messagebox.showwarning("Advertencia", mensaje)
            else:
                # Insertar nuevo cliente
                cursor.execute("""
                    INSERT INTO clientes (Cedula, Nombre, Nacionalidad, Telefono, Direccion, Placa, Fecha_inicio, Fecha_final, Tipo_contrato, Valor_cuota, Estado, Otras_deudas, Visitador, Referencia, Telefono_ref)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, valores)
                conn.commit()

                # Insertar deuda cuota inicial
                fecha_deuda = valores[6]
                cursor.execute("""
                    INSERT INTO otras_deudas (Cedula, Placa, Fecha_deuda, Descripcion, Valor)
                    VALUES (%s, %s, %s, %s, %s)
                """, (valores[0], valores[5], fecha_deuda, "Cuota Inicial", valores[11]))

                conn.commit()

                messagebox.showinfo("Éxito", "Cliente guardado correctamente.")
                ventana_clientes.focus_force()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el cliente.\n{e}")

        finally:
            cursor.close()
            conn.close()

        # 🔹 ACTUALIZAR EL TREEVIEW
        tree.delete(*tree.get_children())  # Limpiar datos actuales en el Treeview
        for fila in obtener_datos_clientes():
            tree.insert("", "end", values=fila)
        ajustar_columnas(tree)  # Ajustar el ancho de las columnas automáticamente

        # 🔹 ACTUALIZAR datos_originales
        global datos_originales
        datos_originales = [tree.item(item)["values"] for item in tree.get_children()]
        ventana_clientes.focus_force()

    def actualizar_cliente():
        # Obtener valores de los campos
        valores = {
            "Cedula": entries["Cédula"].get().strip(), 
            "Nombre": entries["Nombre"].get().strip(), 
            "Nacionalidad": entries["Nacionalidad"].get().strip(), 
            "Telefono": entries["Teléfono"].get().strip(), 
            "Direccion": entries["Dirección"].get().strip(), 
            "Placa": entries["Placa"].get().strip(), 
            "Fecha_inicio": convertir_fecha_formato_sqlite(entries["Fecha Inicio"].get().strip()), 
            "Fecha_final": entries["Fecha Final"].get().strip(), 
            "Tipo_contrato": entries["Tipo Contrato"].get().strip(), 
            "Valor_cuota": entries["Valor Cuota"].get().strip(), 
            "Estado": combo_estado.get().strip(), 
            "Otras_deudas": entries["Otras deudas"].get().strip(), 
            "Visitador": entries["Visitador"].get().strip(), 
            "Referencia": entries["Referencia"].get().strip(), 
            "Telefono_ref": entries["Telefono Ref"].get().strip()
        }

        # Verificar si hay campos vacíos
        if '' in valores.values():
            messagebox.showerror("Error", "Todos los campos deben estar llenos.")
            ventana_clientes.focus_force()
            return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Obtener estado y placa actuales del cliente
            cursor.execute("SELECT Estado, Placa FROM clientes WHERE Cedula = %s LIMIT 1", (valores["Cedula"],))
            datos_actuales = cursor.fetchone()

            if not datos_actuales:
                messagebox.showerror("Error", f"No existe un cliente con la Cédula {valores['Cedula']}.")
                return

            estado_anterior, placa_actual = datos_actuales

            print(f"Estado anterior: {estado_anterior}, Placa actual: {placa_actual}")

            # Validaciones específicas para cambio de estado
            placa_actual = placa_actual.strip()
            if estado_anterior == "activo" and valores["Estado"] == "inactivo":
                if "**" not in placa_actual:
                    valores["Placa"] = placa_actual + " **"
                    print(f"Placa actualizada a INACTIVO: {valores['Placa']}")

            elif estado_anterior == "inactivo" and valores["Estado"] == "activo":
                valores["Placa"] = placa_actual.replace(" **", "").strip()
                print(f"Placa actualizada a ACTIVO: {valores['Placa']}")

                # Validar que la placa esté registrada en propietarios
                cursor.execute("SELECT 1 FROM propietario WHERE Placa = %s LIMIT 1", (valores["Placa"],))
                if not cursor.fetchone():
                    messagebox.showerror("Error", f"La Placa '{valores['Placa']}' no está registrada en la base de datos de propietarios.")
                    return

                # Validar que la placa no esté ya asignada a otro cliente
                cursor.execute("SELECT 1 FROM clientes WHERE Placa = %s AND Cedula <> %s LIMIT 1",
                                (valores["Placa"], valores["Cedula"]))
                if cursor.fetchone():
                    messagebox.showerror("Error", f"La Placa '{valores['Placa']}' ya está asignada a otro cliente.")
                    return

            # Actualizar cliente
            cursor.execute("""
                    UPDATE clientes
                    SET Nombre = %s, Nacionalidad = %s, Telefono = %s, Direccion = %s, Placa = %s, 
                        Fecha_inicio = %s, Fecha_final = %s, Tipo_contrato = %s, Valor_cuota = %s, Estado = %s, 
                        Otras_deudas = %s, Visitador = %s, Referencia = %s, Telefono_ref = %s
                    WHERE Cedula = %s
                """, (
                    valores["Nombre"], valores["Nacionalidad"], valores["Telefono"], valores["Direccion"],
                    valores["Placa"], valores["Fecha_inicio"], valores["Fecha_final"], valores["Tipo_contrato"],
                    valores["Valor_cuota"], valores["Estado"], valores["Otras_deudas"],
                    valores["Visitador"], valores["Referencia"], valores["Telefono_ref"],
                    valores["Cedula"]
                )
            )

            # Actualizar registros relacionados
            cursor.execute("""
                UPDATE registros
                SET Nombre = %s, Placa = %s
                WHERE Cedula = %s
            """, (valores["Nombre"], valores["Placa"], valores["Cedula"]))

            conn.commit()
            messagebox.showinfo("Éxito", "Cliente actualizado correctamente.")
            ventana_clientes.focus_force()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"No se pudo actualizar el cliente.\n{e}")

        finally:
            cursor.close()
            conn.close()

        # 🔹 ACTUALIZAR EL TREEVIEW
        tree.delete(*tree.get_children())  # Limpiar datos actuales en el Treeview
        for fila in obtener_datos_clientes():
            tree.insert("", "end", values=fila)
        ajustar_columnas(tree)  # Ajustar el ancho de las columnas automáticamente

        # 🔹 ACTUALIZAR datos_originales
        global datos_originales
        datos_originales = [tree.item(item)["values"] for item in tree.get_children()]
        ventana_clientes.focus_force()

    def cargar_datos_desde_treeview():
        # Carga los datos seleccionados del Treeview en los campos del formulario.
        seleccion = tree.selection()
        
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un cliente en la tabla.")
            return

        # Obtiene los valores de la fila seleccionada
        valores = tree.item(seleccion[0], "values")
        
        for item_id in seleccion:
            valores = tree.item(item_id, "values")
            print(valores)


        if not valores:
            messagebox.showwarning("Advertencia", "No hay datos en la selección.")
            return
        
        #print(valores)
        # Asignación de valores a cada campo del formulario
        entries["Cédula"].delete(0, tk.END)
        entries["Cédula"].insert(0, valores[0])
        entries["Nombre"].delete(0, tk.END)
        entries["Nombre"].insert(0, valores[1])
        entries["Nacionalidad"].delete(0, tk.END)
        entries["Nacionalidad"].insert(0, valores[2])
        entries["Teléfono"].delete(0, tk.END)
        entries["Teléfono"].insert(0, valores[3])
        entries["Dirección"].delete(0, tk.END)
        entries["Dirección"].insert(0, valores[4])
        entries["Placa"].delete(0, tk.END)
        entries["Placa"].insert(0, valores[5])
        entries["Fecha Inicio"].set_date(valores[8])  # Para DateEntry
        entries["Fecha Final"].insert(0, valores[9])  # Para DateEntry

        # Manejo del Combobox de "Tipo Contrato"
        opciones_tipo_contrato = entries["Tipo Contrato"]["values"]
        if valores[10] in opciones_tipo_contrato:
            entries["Tipo Contrato"].set(valores[10])
        else:
            print(f"El valor '{valores[8]}' no está en las opciones del Combobox")
        entries["Valor Cuota"].delete(0, tk.END)
        entries["Valor Cuota"].insert(0, valores[11])
        combo_estado.set(valores[12])
        entries["Otras deudas"].delete(0, tk.END)
        entries["Otras deudas"].insert(0, valores[13])
        entries["Visitador"].delete(0, tk.END)
        entries["Visitador"].insert(0, valores[14])
        entries["Referencia"].delete(0, tk.END)
        entries["Referencia"].insert(0, valores[15])
        entries["Telefono Ref"].delete(0, tk.END)
        entries["Telefono Ref"].insert(0, valores[16])

    # Configurar estilo de los botones
    style = ttk.Style()
    style.configure("TButton", font=("Arial", 12, "bold"), padding=6, width=12)
    style.configure("BotonCrear.TButton", background="#4CAF50", foreground="black")
    style.configure("BotonModificar.TButton", background="#FFC107", foreground="black")
    style.configure("BotonLimpiar.TButton", background="#F44336", foreground="black")
    # Configurar el frame con un borde
    frame_buttons = ttk.Frame(ventana_clientes, relief="ridge", borderwidth=3)
    frame_buttons.grid(row=2, column=0, columnspan=4, pady=10, padx=10, sticky="ew")
    # Botones Crear, Modificar, Limpiar con estilos personalizados
    btn_crear = ttk.Button(frame_buttons, text="Crear", command=registrar_cliente, style="BotonCrear.TButton")
    btn_crear.grid(row=0, column=0, padx=10, pady=5)
    btn_modificar = ttk.Button(frame_buttons, text="Modificar", command=actualizar_cliente, style="BotonModificar.TButton")
    btn_modificar.grid(row=0, column=1, padx=10, pady=5)
    btn_limpiar = ttk.Button(frame_buttons, text="Limpiar", command=limpiar_formulario, style="BotonLimpiar.TButton")
    btn_limpiar.grid(row=0, column=2, padx=10, pady=5)
    tree.bind("<Double-1>", lambda event: cargar_datos_desde_treeview())
    # Expansión de filas y columnas
    ventana_clientes.columnconfigure(0, weight=1)
    ventana_clientes.rowconfigure(0, weight=1)
    ventana_clientes.protocol("WM_DELETE_WINDOW", cerrar_ventana_clientes)
    return ventana_clientes  # Si quieres capturar la ventana creada

def cerrar_ventana_clientes():
    global ventana_clientes
    ventana_clientes.destroy()
    ventana_clientes = None  # Resetea la variable

def abrir_ventana_cuentas():
    # Crear ventana
    ventana_cuentas = tk.Toplevel()
    ventana_cuentas.title("Gestión de Cuentas")
    ventana_cuentas.geometry("600x400")
    ventana_cuentas.rowconfigure(0, weight=1)
    ventana_cuentas.columnconfigure(0, weight=1)

    # Establecer un icono (si existe)
    icono_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'inicio.ico')
    if os.path.exists(icono_path):
        ventana_cuentas.iconbitmap(icono_path)


    # Frame superior para la tabla
    frame_tabla = ttk.Frame(ventana_cuentas)
    frame_tabla.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    # Permitir expansión dentro del frame
    frame_tabla.rowconfigure(0, weight=1)
    frame_tabla.columnconfigure(0, weight=1)

    # Crear Treeview con scrollbar
    columnas = ("ID", "Nombre cuenta", "Llave")
    tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings")

    # Scrollbar vertical
    scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)

    # Configuración de columnas
    for col in columnas:
        tree.heading(col, text=col, anchor="center")
        tree.column(col, anchor="center", width=150, stretch=True)

    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

   # Función para cargar datos desde la base de datos
    def cargar_datos():
        try:
            # Limpiar el Treeview antes de recargar los datos
            for item in tree.get_children():
                tree.delete(item)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre_cuenta, llave FROM cuentas")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                tree.insert("", "end", values=row)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los datos: {e}")
            ventana_cuentas.focus_force()


    # Función para crear una nueva cuenta
    def crear_cuenta():
        titular_valor = entry_titular.get().strip()
        llave_valor = entry_llave.get().strip()

        if not titular_valor or not llave_valor:
            messagebox.showwarning("Advertencia", "Todos los campos deben ser completados")
            ventana_cuentas.focus_force()
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Verificar si la combinación Entidad - Llave ya existe
            cursor.execute(
                "SELECT COUNT(*) FROM cuentas WHERE nombre_cuenta = %s AND llave = %s",
                (titular_valor, llave_valor)
            )
            if cursor.fetchone()[0] > 0:
                messagebox.showwarning("Advertencia", "La combinación Titular - Llave ya existe en la base de datos.")
                entry_llave.focus_force()
                return

            # Insertar la nueva cuenta
            cursor.execute(
                "INSERT INTO cuentas (nombre_cuenta, llave) VALUES (%s, %s) RETURNING id",
                (titular_valor, llave_valor)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()

            # Insertar en Treeview y limpiar entradas
            tree.insert("", "end", values=(new_id, titular_valor, llave_valor))
            entry_titular.delete(0, tk.END)
            entry_llave.delete(0, tk.END)

            messagebox.showinfo("Éxito", "Cuenta creada exitosamente")
            ventana_cuentas.focus_force()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la cuenta: {e}")

        finally:
            if conn:
                conn.close()


    # Función para eliminar una cuenta
    def eliminar_cuenta():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Seleccione un registro para eliminar.")
            ventana_cuentas.focus_force()
            return

        item_values = tree.item(selected_item)["values"]
        
        if not item_values:  # Evitar errores si no hay valores
            messagebox.showerror("Error", "No se pudo obtener la información del registro seleccionado.")
            return
        
        id_cuenta = item_values[0]  # Se asume que el ID está en la primera columna

        confirmacion = messagebox.askyesno("Confirmar", f"¿Deseas eliminar la cuenta con ID {id_cuenta}?")
        ventana_cuentas.focus_force()
        if confirmacion:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cuentas WHERE id = %s", (id_cuenta,))
                conn.commit()
                                    
                tree.delete(selected_item)
                messagebox.showinfo("Éxito", f"Cuenta con ID {id_cuenta} eliminada.")
                                    
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")  
                                    
            finally:
                if conn:
                    conn.close()
            
            ventana_cuentas.focus_force()


    # Cargar datos al inicio
    cargar_datos()

    # Frame medio para formularios
    frame_formulario = ttk.Frame(ventana_cuentas, padding=10)
    frame_formulario.grid(row=1, column=0, columnspan=3, pady=10, sticky="ew")

    label_titular = ttk.Label(frame_formulario, text="Entidad Titular:")
    label_titular.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
    titular_var = tk.StringVar()
    titular_var.trace_add("write", lambda *args: titular_var.set(titular_var.get().title()))
    entry_titular = ttk.Entry(frame_formulario, textvariable = titular_var, width=30)
    entry_titular.grid(row=0, column=1, padx=5, pady=5)
    
    label_llave = ttk.Label(frame_formulario, text="Llave:")
    label_llave.grid(row=1, column=0, padx=5, pady=5, sticky="w")

    entry_llave = ttk.Entry(frame_formulario, width=30)
    entry_llave.grid(row=1, column=1, padx=5, pady=5)
    
    # Configurar estilo de los botones
    style = ttk.Style()
    style.configure("TButton", font=("Arial", 12, "bold"), padding=6, width=12)
    style.configure("BotonCrear.TButton", background="#4CAF50", foreground="black")
    style.configure("BotonLimpiar.TButton", background="#F44336", foreground="black")

    # Configurar el frame con un borde
    frame_botones = ttk.Frame(ventana_cuentas, relief="ridge", borderwidth=3)
    frame_botones.grid(row=2, column=0, columnspan=4, pady=10, padx=10, sticky="ew")

    btn_crear = ttk.Button(frame_botones, text="Crear", command= crear_cuenta, style="BotonCrear.TButton")
    btn_crear.grid(row=0, column=0, padx=10, pady=5)

    btn_eliminar = ttk.Button(frame_botones, text="Eliminar", command= eliminar_cuenta, style="BotonLimpiar.TButton")
    btn_eliminar.grid(row=0, column=1, padx=10, pady=5)


    # Expandir columnas
    ventana_cuentas.columnconfigure(0, weight=1)
    ventana_cuentas.rowconfigure(0, weight=1)

def mostrar_registros(entry_cedula):
    cedula = entry_cedula.get().strip()
    # Obtener alto de la pantalla
    
    if not cedula:
        messagebox.showerror("Error", "Debe ingresar un cliente.")
        return
    
    def obtener_area_usable():
        user32 = ctypes.windll.user32
        rect = ctypes.wintypes.RECT()
        # SPI_GETWORKAREA = 48
        if user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
            ancho = rect.right - rect.left
            alto = rect.bottom - rect.top
            return ancho, alto
        else:
            return None, None

    ventana = tk.Toplevel()
    alto_pantalla = ventana.winfo_screenheight()
    ventana.title("Extracto del Cliente")
    ancho_usable, alto_usable = obtener_area_usable()
    if ancho_usable and alto_usable:
        ventana.geometry(f"900x{alto_usable-100}")  # 800 de ancho fijo, altura usable
    else:
        ventana.geometry("800x600")  # fallback

    try:
        """Obtiene un cliente y sus pagos de la base de datos PostgreSQL."""
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Obtener datos del cliente por cédula en lugar de nombre
                cursor.execute("""
                    SELECT Cedula, Nombre, COALESCE(Placa, 'N/A'), Fecha_inicio, Valor_cuota
                    FROM clientes
                    WHERE Cedula = %s
                """, (cedula,))
                cliente = cursor.fetchone()

                if not cliente:
                    messagebox.showerror("Error", "Cliente no encontrado.")
                    return

                cedula, nombre, placa, fecha_inicio, valor_cuota = cliente

                if not fecha_inicio or not valor_cuota:
                    messagebox.showerror("Error", "Datos del cliente incompletos.")
                    return

                fecha_inicio = datetime.strptime(str(fecha_inicio), "%Y-%m-%d")
                fecha_actual = datetime.today()
                
                
                print(f"- Fecha inicio: {fecha_inicio} (tipo: {type(fecha_inicio)})")
                print(f"- Fecha actual: {fecha_actual} (tipo: {type(fecha_actual)})")

                # Obtener registros de pagos por cédula en lugar de nombre
                cursor.execute("""
                    SELECT Fecha_registro, Valor, Tipo, Referencia
                    FROM registros
                    WHERE Cedula = %s
                    ORDER BY Fecha_registro
                """, (cedula,))
                registros = cursor.fetchall()
                
                # Transformamos las fechas a datetime
                registros_modificados = []
                for fecha, valor, tipo, referencia in registros:
                    fecha_dt = datetime.combine(fecha, time())
                    print(f"Fecha registro: {fecha_dt} (tipo: {type(fecha_dt)})")
                    registros_modificados.append((fecha_dt, valor, tipo, referencia))
            

        total = sum(row[1] for row in registros_modificados)  # row[1] es el campo "Valor"
        cuotas_pagadas = math.ceil(total / valor_cuota)  # Redondea al siguiente entero
        
        # Calcular la diferencia de días entre fecha_inicio y fecha_actual
        dias_rango = (fecha_actual - fecha_inicio).days + 1

        # Si cuotas_pagadas es mayor que la cantidad de días en el rango, ampliamos la fecha_actual
        if cuotas_pagadas > dias_rango:
            diferencia = cuotas_pagadas - dias_rango
            fecha_actual += timedelta(days=diferencia)


        # Generación del DataFrame con fechas
        fechas = pd.date_range(start=fecha_inicio, end=fecha_actual)
        df = pd.DataFrame({
            "Fecha Programada": fechas.strftime("%Y-%m-%d"),
            "Fecha Pago": "", 
            "Valor Pagado": 0, 
            "Tipo": "", 
            "Referencia": ""
        })

        # Aplicar pagos al DataFrame
        saldo = 0
        pagos_idx = 0
        for i in range(len(df)):
            while pagos_idx < len(registros_modificados) and saldo < valor_cuota:
                registro_fecha, valor, tipo, referencia = registros_modificados[pagos_idx]
                while valor + saldo >= valor_cuota:  # Manejar múltiples cuotas con un solo pago
                    falta_para_cuota = valor_cuota - saldo
                    # Evitar sobrescribir valores existentes
                    df.at[i, "Valor Pagado"] = df.at[i, "Valor Pagado"] if pd.notna(df.at[i, "Valor Pagado"]) else 0
                    df.at[i, "Valor Pagado"] += falta_para_cuota
                    df.at[i, "Fecha Pago"] = registro_fecha
                    #df.at[i, "Fecha Pago"] = registro_fecha.date().strftime("%d-%m-%Y")
                    # df.at[i, "Fecha Pago"] = datetime.strptime(registro_fecha, "%Y-%m-%d").strftime("%d-%m-%Y")
                    if pd.isna(df.at[i, "Referencia"]) or df.at[i, "Referencia"] == "":
                        df.at[i, "Referencia"] = referencia
                    if pd.isna(df.at[i, "Tipo"]) or df.at[i, "Tipo"] == "":
                        df.at[i, "Tipo"] = tipo
                    valor -= falta_para_cuota
                    saldo = 0  # Reiniciar saldo porque la cuota se completó
                    i += 1  # Pasar a la siguiente fila (día)
                    if i >= len(df):  # Evitar salir del índice
                        break

                saldo += valor
                #Solo asignar si todavía hay valor a registrar
                if valor > 0:
                    df.at[i, "Valor Pagado"] = df.at[i, "Valor Pagado"] if pd.notna(df.at[i, "Valor Pagado"]) else 0
                    df.at[i, "Valor Pagado"] += valor
                    if pd.isna(df.at[i, "Tipo"]) or df.at[i, "Tipo"] == "":
                        df.at[i, "Tipo"] = tipo
                if saldo >= valor_cuota:
                    df.at[i, "Fecha Pago"] = registro_fecha
                    #df.at[i, "Fecha Pago"] = registro_fecha.date().strftime("%d-%m-%Y")
                    # df.at[i, "Fecha Pago"] = datetime.strptime(registro_fecha, "%Y-%m-%d").strftime("%d-%m-%Y")
                    if pd.isna(df.at[i, "Referencia"]) or df.at[i, "Referencia"] == "":
                        df.at[i, "Referencia"] = referencia
                    if pd.isna(df.at[i, "Tipo"]) or df.at[i, "Tipo"] == "":
                        df.at[i, "Tipo"] = tipo
                    saldo -= valor_cuota
                else:
                    pagos_idx += 1  # Seguimos con el siguiente pago

        
        
        #df["Fecha Programada"] = pd.to_datetime(df["Fecha Programada"]).dt.strftime("%d-%m-%Y")
        df["Fecha Programada"] = pd.to_datetime(df["Fecha Programada"])
        
        # Cuotas completas pagadas
        cuotas_pagadas_completas = (df["Valor Pagado"] // valor_cuota).sum()
        # Verificar si hay un remanente en la última fila
        remanente = (df["Valor Pagado"] % valor_cuota).sum()  # Suma de los sobrantes
        # Si el remanente es suficiente para una fracción de cuota, la contamos proporcionalmente
        fraccion_cuota = remanente / valor_cuota
        # Total de cuotas pagadas (sin redondear para cálculos)
        cuotas_pagadas = cuotas_pagadas_completas + fraccion_cuota
        # Cuotas vencidas
        cuotas_vencidas = len(df)
        # Cuotas pendientes (sin redondear para cálculos)
        cuotas_pendientes = cuotas_vencidas - cuotas_pagadas
        # Valor pendiente (se mantiene con precisión completa)
        valor_pendiente = cuotas_pendientes * valor_cuota
        valor_pendiente_cop = f"${valor_pendiente:,.0f}".replace(",", ".")
        # 🔹 Solo para mostrar con 1 decimal (sin afectar cálculos internos)
        cuotas_pagadas_mostrar = f"{cuotas_pagadas:.1f}"
        cuotas_pendientes_mostrar = f"{cuotas_pendientes:.1f}"
        
        def capturar_y_copiar():
            # Obtener coordenadas de la ventana
            x = ventana.winfo_rootx()
            y = ventana.winfo_rooty()
            ancho = x + ventana.winfo_width()
            alto = y + ventana.winfo_height()
            # Capturar la pantalla dentro de la ventana
            captura = ImageGrab.grab(bbox=(x, y, ancho, alto))
            # Guardar la imagen en un buffer de memoria en formato PNG
            output = io.BytesIO()
            captura.save(output, format="PNG")
            image_data = output.getvalue()
            # Copiar la imagen al portapapeles en formato DIB (Device Independent Bitmap)
            output.seek(0)
            image = ImageGrab.grab(bbox=(x, y, ancho, alto)).convert("RGB")  # Convertir a RGB
            output = io.BytesIO()
            image.save(output, format="DIB")
            data = output.getvalue()
            # Abrir el portapapeles y copiar la imagen
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            ventana.destroy()

        # ====== TÍTULO ======
        lbl_titulo = tk.Label(ventana, text="Extracto de pagos", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=5)
        # ====== Botón de Acción ======
        boton_accion = tk.Button(ventana, text="Captura", font=("Arial", 10), bg="#d9d9d9", command=capturar_y_copiar)
        boton_accion.pack(pady=5)

        # ====== PANEL DE INFORMACIÓN ======
        frame_info = tk.Frame(ventana, bg="#f0f0f0", bd=2, relief="solid", padx=10, pady=10)
        frame_info.pack(fill=tk.X, padx=10, pady=5)

        # Crear los 4 paneles que representarán las columnas
        frame_col1 = tk.Frame(frame_info, bg="#f0f0f0")
        frame_col2 = tk.Frame(frame_info, bg="#f0f0f0")
        frame_col3 = tk.Frame(frame_info, bg="#f0f0f0")
        frame_col4 = tk.Frame(frame_info, bg="#f0f0f0")

        # Empaquetar los frames en línea horizontal
        frame_col1.pack(side=tk.LEFT, expand=True, padx=10, pady=5)
        frame_col2.pack(side=tk.LEFT, expand=True, padx=10, pady=5)
        frame_col3.pack(side=tk.LEFT, expand=True, padx=10, pady=5)
        frame_col4.pack(side=tk.LEFT, expand=True, padx=10, pady=5)

        # ====== Información del Cliente (Columna 1) ======
        tk.Label(frame_col1, text="Información del Cliente", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col1, text=f"Cédula: {cedula}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col1, text=f"Nombre: {nombre}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")

        # ====== Información del Vehículo (Columna 2) ======
        tk.Label(frame_col2, text="Información del Vehículo", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col2, text=f"Placa: {placa}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")
        valor_cuota_cop = f"${valor_cuota:,.0f}".replace(",", ".")
        tk.Label(frame_col2, text=f"Valor cuota: {valor_cuota_cop}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")

        # ====== Datos Financieros (Columna 3) ======
        tk.Label(frame_col3, text="Datos Financieros", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col3, text=f"Cuotas generadas: {cuotas_vencidas}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col3, text=f"Cuotas pagadas: {cuotas_pagadas:.1f}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")

        # ====== Estado Financiero (Columna 4) ======
        tk.Label(frame_col4, text="Estado Financiero", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col4, text=f"Cuotas pendientes: {cuotas_pendientes:.1f}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")
        tk.Label(frame_col4, text=f"Valor para estar al día: {valor_pendiente_cop}", font=("Arial", 11), bg="#f0f0f0").pack(anchor="w")

        # ====== TREEVIEW ======
        frame_tree = tk.Frame(ventana)
        frame_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columnas = ("Fecha Programada", "Fecha Pago", "Valor Pagado", "Tipo", "Referencia")
        # Scrollbar vertical
        scrollbar_y = ttk.Scrollbar(frame_tree, orient="vertical")
        tree = ttk.Treeview(frame_tree, columns=columnas, show='headings', style="Custom.Treeview")

        # Configurar encabezados
        for col in columnas:
            tree.heading(col, text=col, anchor="center")
            tree.column(col, anchor="center", width=150)

        # Estilos del Treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        # Definir un estilo para las filas resaltadas
        tree.tag_configure("resaltado", background="lightcoral")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar_y.set)
        

        # Insertar datos en el Treeview desde el DataFrame
        for _, row in df.iterrows():
            tags = ("pendiente",) if row["Valor Pagado"] == 0 else ()
            valor_fecha_pago = row["Fecha Pago"]
            valor_formateado = ""
            if pd.notnull(valor_fecha_pago) and valor_fecha_pago:
                if isinstance(valor_fecha_pago, datetime):
                    # Si ya es un datetime, formatear
                    valor_formateado = valor_fecha_pago.strftime("%d-%m-%Y")
                else:
                    # Si es un str, parsear y formatear
                    try:
                        fecha_dt = datetime.strptime(valor_fecha_pago, "%Y-%m-%d")
                        valor_formateado = fecha_dt.strftime("%d-%m-%Y")
                    except ValueError:
                        # Si falla, deja el texto original
                        valor_formateado = valor_fecha_pago
                    
            print(f"Valor formateado: {valor_formateado} (tipo: {type(valor_formateado)})")
            # Insertar fila en el Treeview    
            tree.insert(
                "", 
                "end", 
                values=(
                    row["Fecha Programada"].strftime("%d-%m-%Y"),
                    valor_formateado,  # Aquí usamos el valor formateado
                    row["Valor Pagado"],
                    row["Tipo"],
                    row["Referencia"]
                ),
                tags=tags
            )


        # Estilo para saldo pendiente
        tree.tag_configure("pendiente", foreground="red")
        tree.yview_moveto(1.0)


    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado: {str(e)}")

def ventana_propietario():
    # Crear ventana secundaria
    ventana_propietario = tk.Toplevel()
    ventana_propietario.title("Gestión de Propietarios")
    ventana_propietario.geometry("700x400")
    # Configurar el grid en la ventana principal
    ventana_propietario.columnconfigure(0, weight=1)
    ventana_propietario.rowconfigure(0, weight=1)
    ventana_propietario.rowconfigure(1, weight=0)
    ventana_propietario.rowconfigure(2, weight=0)
    
    def seleccionar_fila(event):
        # Obtener la fila seleccionada
        item = tree.selection()
        if item:
            valores = tree.item(item, "values")  # Obtener valores de la fila
            # Asignar los valores a las variables del formulario
            placa_var.set(valores[0])  # Placa
            modelo_var.set(valores[1])  # Modelo
            color_var.set(valores[2]) #Color
            tipo_var.set(valores[3])  # Tipo
            tarjeta_var.set(valores[4])  # Tarjeta Propiedad
            cuenta_var.set(valores[5])  # Cuenta

    def cargar_propietarios():
        """Carga los datos de la base de datos en el treeview para filtrarlos posteriormente."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Placa, Modelo, Color, Tipo, Tarjeta_propiedad, Cuenta FROM propietario")

        global data  # Guardamos los datos originales para filtrar
        data = cursor.fetchall()
        conn.close()
        
        tree.delete(*tree.get_children())  # Limpiar registros previos

        for registro in data:
            tree.insert("", "end", values=registro)

    def limpiar_campos():
        placa_var.set("")
        modelo_var.set("")
        color_var.set("")
        tipo_var.set("")
        tarjeta_var.set("")
        cuenta_var.set("")

    def agregar_propietario():
        """Agregar un nuevo propietario a la base de datos de PostgreSQL."""
        conn = get_connection()
        cursor = conn.cursor()
        
        placa = placa_var.get().strip()
        modelo = modelo_var.get().strip()
        color = color_var.get().strip()
        tipo = tipo_var.get().strip()
        tarjeta = tarjeta_var.get().strip()
        cuenta = cuenta_var.get().strip()

        # Verificar que todos los campos están llenos
        if not placa or not modelo or not tarjeta or not color or not tipo or not cuenta:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            ventana_propietario.focus_force()
            return

        # Verificar si la placa ya existe
        cursor.execute("SELECT COUNT(*) FROM propietario WHERE Placa = %s", (placa,))
        existe = cursor.fetchone()[0]

        if existe:
            messagebox.showerror("Error", f"La placa {placa} ya está registrada.")
            ventana_propietario.focus_force()
        else:
            cursor.execute(
                "INSERT INTO propietario (Placa, Modelo, Color, Tipo, Tarjeta_propiedad, Cuenta) VALUES (%s, %s, %s, %s, %s, %s)", 
                (placa, modelo, color, tipo, tarjeta, cuenta) 
            )
            conn.commit()
            messagebox.showinfo("Éxito", "Propietario agregado correctamente.")

        conn.close()
        cargar_propietarios()
        limpiar_campos()

    def modificar_propietario():
    
        """Modificar un propietario en la base de datos de PostgreSQL."""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Selección requerida", "Por favor, seleccione un propietario para modificar.")
            ventana_propietario.focus_force()
            return

        # Obtener los nuevos valores
        placa_nueva = placa_var.get().strip().upper()
        modelo_nuevo = modelo_var.get().strip().title()
        color_nuevo = color_var.get().strip().title()
        tipo_nuevo = tipo_var.get()
        tarjeta_nueva = tarjeta_var.get().strip().title()
        cuenta_nueva = cuenta_var.get().strip().title()

        if not placa_nueva or not modelo_nuevo or not color_nuevo or not tipo_nuevo or not tarjeta_nueva or not cuenta_nueva:
            messagebox.showwarning("Campos vacíos", "Todos los campos deben estar llenos.")
            ventana_propietario.focus_force()
            return

        # Obtener la placa original del Treeview
        item = tree.item(selected_item)
        placa_original = item["values"][0]

        conn = get_connection()
        conn.autocommit = False  # Desactivar autocommit antes de inicio de la transacción
        cursor = conn.cursor()

        try:
            # Verificar duplicidad
            cursor.execute("SELECT COUNT(*) FROM propietario WHERE Placa = %s AND Placa <> %s", (placa_nueva, placa_original))
            if cursor.fetchone()[0] > 0:
                messagebox.showerror("Error de duplicado", f"La placa '{placa_nueva}' ya existe en otro registro.")
                ventana_propietario.focus_force()
                conn.rollback()
                return

            # Actualización en todas las tablas relacionadas
            cursor.execute("""
                UPDATE propietario 
                SET Placa = %s, Modelo = %s, Color = %s, Tipo = %s, Tarjeta_propiedad = %s, Cuenta = %s
                WHERE Placa = %s
            """, (placa_nueva, modelo_nuevo, color_nuevo, tipo_nuevo, tarjeta_nueva, cuenta_nueva, placa_original))

            cursor.execute("UPDATE clientes SET Placa = %s WHERE Placa = %s", (placa_nueva, placa_original))
            cursor.execute("UPDATE registros SET Placa = %s WHERE Placa = %s", (placa_nueva, placa_original))

            # Confirmar
            conn.commit()
            messagebox.showinfo("Éxito", "El propietario ha sido modificado correctamente.")
            ventana_propietario.focus_force()

            # Actualizar el Treeview
            tree.item(selected_item, values=(placa_nueva, modelo_nuevo, color_nuevo, tipo_nuevo, tarjeta_nueva, cuenta_nueva))
            tree.selection_set(selected_item)

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error de base de datos", f"Ocurrió un error: {e}")
            ventana_propietario.focus_force()

        finally:
            conn.autocommit = True
            conn.close()

        # Recargar y limpiar
        cargar_propietarios()
        limpiar_campos()

    # 🌟 FRAME PARA EL TREEVIEW
    frame_tree = ttk.Frame(ventana_propietario, padding=10)
    frame_tree.grid(row=0, column=0, sticky="nsew")
    columnas = ("Placa", "Modelo", "Color", "Tipo", "Tarjeta Propiedad", "Cuenta")
    tree = ttk.Treeview(frame_tree, columns=columnas, show="headings", height=8)
    # Variable para almacenar el estado de orden (ascendente/descendente)
    sort_states = {col: False for col in columnas}
    
    def ordenar_por_columna(tree, col):
        """Ordena el Treeview al hacer clic en un encabezado."""
        # Obtener datos actuales del Treeview
        datos = [(tree.set(item, col), item) for item in tree.get_children('')]
        
        # Determinar el tipo de datos y ordenar correctamente
        try:
            datos.sort(key=lambda x: int(x[0]), reverse=sort_states[col])
        except ValueError:
            datos.sort(key=lambda x: x[0], reverse=sort_states[col])

        # Invertir el estado de orden para el próximo clic
        sort_states[col] = not sort_states[col]

        # Reorganizar los datos en el Treeview
        for index, (_, item) in enumerate(datos):
            tree.move(item, '', index)

        # Actualizar visualmente el encabezado (opcional)
        tree.heading(col, text=f"{col} {'▲' if sort_states[col] else '▼'}")

    # Encabezados del Treeview con eventos de clic
    for col in columnas:
        tree.heading(col, text=col, anchor="center", command=lambda c=col: ordenar_por_columna(tree, c))
        tree.column(col, width=180, anchor="center")
    # Barra de desplazamiento vertical
    scrollbar_vertical = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    scrollbar_vertical.grid(row=0, column=1, sticky="ns")
    # Configuración para que el Treeview use el scroll
    tree.configure(yscrollcommand=scrollbar_vertical.set)
    tree.grid(row=0, column=0, sticky="nsew")
    tree.bind("<Double-1>", seleccionar_fila)
    # Expandir el TreeView dentro del frame
    frame_tree.columnconfigure(0, weight=1)
    frame_tree.rowconfigure(0, weight=1)

    # 🌟 FRAME PARA FORMULARIO
    frame_form = ttk.Frame(ventana_propietario, padding=10, borderwidth=2, relief="solid")
    frame_form.grid(row=1, column=0, sticky="ew")
    
    def update_total_entries():
        """
        Cuenta la cantidad de registros actuales en el Treeview y actualiza el valor en el Entry correspondiente.
        """
        total = len(tree.get_children())
        entry_total_placas.delete(0, "end")  # Limpiar el Entry
        entry_total_placas.insert(0, str(total))  # Insertar el total
    
    def filter_treeview(*args):
        """Filtra el Treeview en función del texto ingresado en el Entry."""
        search_term = placa_var.get().lower()
        
        # Restaurar datos si no hay texto
        tree.delete(*tree.get_children())  # Limpiar Treeview
        
        for item in data:
            if any(search_term in str(value).lower() for value in item):  
                tree.insert("", "end", values=item)  # Insertar si coincide
        update_total_entries()  # Actualizar el total de registros
                
    def filter2_treeview(*args):
        """Filtra el Treeview en función del texto ingresado en el Entry."""
        search_term = tarjeta_var.get().title()
        
        # Restaurar datos si no hay texto
        tree.delete(*tree.get_children())  # Limpiar Treeview
        
        for item in data:
            if any(search_term in str(value).title() for value in item):  
                tree.insert("", "end", values=item)  # Insertar si coincide  
        update_total_entries()  # Actualizar el total de registros          
                

    # Crear campos del formulario en línea horizontal
    placa_var = tk.StringVar()
    placa_var.trace_add("write", filter_treeview)  # Ejecuta la función en cada cambio
    placa_var.trace_add("write", lambda *args: placa_var.set(placa_var.get().upper()))
    ttk.Label(frame_form, text="Placa:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    entry_placa = ttk.Entry(frame_form, textvariable=placa_var, width=30)
    entry_placa.grid(row=0, column=1, padx=5, pady=5)

    modelo_var = tk.StringVar()
    modelo_var.trace_add("write", lambda *args: modelo_var.set(modelo_var.get().title()))
    ttk.Label(frame_form, text="Modelo:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    entry_modelo = ttk.Entry(frame_form, textvariable=modelo_var, width=30)
    entry_modelo.grid(row=0, column=3, padx=5, pady=5)
    
    color_var = tk.StringVar()
    color_var.trace_add("write", lambda *args: color_var.set(color_var.get().title()))
    ttk.Label(frame_form, text="Color:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    entry_color = ttk.Entry(frame_form, textvariable=color_var, width=30)
    entry_color.grid(row=1, column=1, padx=5, pady=5)
    
    tipo_var = tk.StringVar()
    # Definición del Combobox con las dos opciones
    ttk.Label(frame_form, text="Tipo:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
    combo_tipo = ttk.Combobox(frame_form, textvariable=tipo_var, values=["Nueva", "Usada"], state="readonly", width=28)
    combo_tipo.grid(row=1, column=3, padx=5, pady=5)
    # Seleccionar un valor por defecto (opcional)
    combo_tipo.current(0)  # Selecciona "Nueva" por defecto

    tarjeta_var = tk.StringVar()
    tarjeta_var.trace_add("write", filter2_treeview)  # Ejecuta la función en cada cambio
    tarjeta_var.trace_add("write", lambda *args: tarjeta_var.set(tarjeta_var.get().title()))
    ttk.Label(frame_form, text="Tarjeta Propiedad:").grid(row=1, column=4, padx=5, pady=5, sticky="w")
    entry_tarjeta = ttk.Entry(frame_form, textvariable=tarjeta_var, width=30)
    entry_tarjeta.grid(row=1, column=5, padx=5, pady=5)
    cuenta_var = tk.StringVar()
    cuenta_var.trace_add("write", lambda *args: cuenta_var.set(cuenta_var.get().title()))
    ttk.Label(frame_form, text="Cuenta:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
    entry_cuenta = ttk.Entry(frame_form, textvariable=cuenta_var, width=30)
    entry_cuenta.grid(row=0, column=5, padx=5, pady=5)
    
    frame_info = ttk.Frame(ventana_propietario, padding=10)
    frame_info.grid(row=2, column=0, sticky="nsew")
    # Campo 1: Total Placas
    label_total_placas = ttk.Label(frame_info, text="Total Placas:")
    label_total_placas.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    entry_total_placas = ttk.Entry(frame_info)
    entry_total_placas.grid(row=0, column=1, padx=5, pady=5)

    # 🌟 FRAME PARA BOTONES
    frame_buttons = ttk.Frame(ventana_propietario, relief="ridge", borderwidth=3)
    frame_buttons.grid(row=3, column=0, columnspan=4, pady=10, padx=10, sticky="ew")

    style = ttk.Style()
    style.configure("TButton", font=("Arial", 12, "bold"), padding=6, width=12)
    style.configure("BotonCrear.TButton", background="#4CAF50", foreground="black")
    style.configure("BotonModificar.TButton", background="#FFC107", foreground="black")
    style.configure("BotonLimpiar.TButton", background="#F44336", foreground="black")
    style.configure("BotonDashBoard.TButton", background="#F44336", foreground="black")
    
    # Botones con funcionalidades
    btn_crear = ttk.Button(frame_buttons, text="Crear", command= agregar_propietario, style="BotonCrear.TButton")
    btn_crear.grid(row=0, column=0, padx=10, pady=5)
    btn_modificar = ttk.Button(frame_buttons, text="Modificar", command= modificar_propietario, style="BotonModificar.TButton")
    btn_modificar.grid(row=0, column=1, padx=10, pady=5)
    btn_limpiar = ttk.Button(frame_buttons, text="Limpiar", command= limpiar_campos, style="BotonLimpiar.TButton")
    btn_limpiar.grid(row=0, column=2, padx=10, pady=5)
    
    # Expandir columnas en el frame de botones
    frame_buttons.columnconfigure((0, 1, 2), weight=1)

    cargar_propietarios()

def join_and_export():
    # Selección de carpeta
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Selecciona una carpeta para guardar el archivo")

    if not folder_selected:
        messagebox.showwarning("Operación cancelada", "No se guardó ningún archivo.")
        return

    output_path = os.path.join(folder_selected, "resultado.xlsx")

    try:
        conn = get_connection()

        query = """
        SELECT r.*, p.*
        FROM registros r
        LEFT JOIN propietario p ON r.placa = p.placa
        """

        merged_df = pd.read_sql_query(query, conn)
        merged_df.to_excel(output_path, index=False)

        messagebox.showinfo("Exportación exitosa", f"El archivo .xlsx se guardó en:\n{output_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error:\n{e}")

    finally:
        if 'conn' in locals():
            conn.close()

def mostrar_consulta_registros():
    # Función para crear y mostrar la interfaz de consulta
    def buscar_registros():
        # Obtener los valores de las fechas
        fecha_sis_inicio = date_sis_inicio.get_date()
        fecha_sis_fin = date_sis_fin.get_date()

        # Limpiar el tree principal
        tree.delete(*tree.get_children())

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Consulta SQL con rangos de fechas para Fecha_sistema
            query = """
            SELECT Id, Fecha_sistema, Fecha_registro, Cedula, Nombre, Placa, 
                   Valor, Saldos, Tipo, Nombre_cuenta, Referencia, Verificada 
            FROM registros 
            WHERE Fecha_sistema BETWEEN ? AND ?
            """
            cursor.execute(query, (fecha_sis_inicio, fecha_sis_fin))
            registros = cursor.fetchall()

            # Verificar si hay registros, si no, mostrar mensaje
            if not registros:
                messagebox.showinfo("Sin resultados", "No se encontraron registros en el rango de fechas seleccionado.")
                return

            # Insertar registros en el Treeview con formato de moneda
            for reg in registros:
                reg = list(reg)
                reg[6] = f"${int(reg[6]):,}".replace(",", ".")   # Valor
                reg[7] = f"${int(reg[7]):,}".replace(",", ".")   # Saldos
                tree.insert("", "end", values=reg)

            # Actualizar el Treeview auxiliar
            actualizar_totales(registros)

        except sqlite3.Error as e:
            messagebox.showerror("Error de base de datos", f"Ocurrió un error: {e}")

        finally:
            conn.close()

    def actualizar_totales(registros):
        # Limpiar el tree auxiliar
        tree_totales.delete(*tree_totales.get_children())
        cuentas = {}

        # Calcular totales agrupados por Nombre_cuenta
        for reg in registros:
            nombre_cuenta = reg[9]  # Índice de Nombre_cuenta en la tabla
            valor = float(reg[6])   # Índice de Valor en la tabla
            cuentas[nombre_cuenta] = cuentas.get(nombre_cuenta, 0) + valor

        # Insertar totales en el Treeview auxiliar con formato de moneda
        for nombre_cuenta, total in cuentas.items():
            total_formateado = f"${int(total):,}".replace(",", ".")
            tree_totales.insert("", "end", values=(nombre_cuenta, total_formateado))

    # Ventana secundaria (Toplevel)
    ventana = tk.Toplevel()  # Cambiado de Tk() a Toplevel(master)
    ventana.title("Consulta de Registros")
    ventana.geometry("1000x600")

    # Frame de formulario
    frame_form = ttk.Frame(ventana, padding=10)
    frame_form.pack(fill="x")

    # Rango de fechas para Fecha_sistema
    ttk.Label(frame_form, text="Fecha Sistema (Inicio):").grid(row=1, column=0, padx=5, pady=5)
    date_sis_inicio = DateEntry(frame_form, width=12, date_pattern="yyyy-mm-dd")
    date_sis_inicio.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(frame_form, text="Fecha Sistema (Fin):").grid(row=1, column=2, padx=5, pady=5)
    date_sis_fin = DateEntry(frame_form, width=12, date_pattern="yyyy-mm-dd")
    date_sis_fin.grid(row=1, column=3, padx=5, pady=5)

    # Botón de búsqueda
    ttk.Button(frame_form, text="Buscar", command=buscar_registros).grid(row=2, column=0, columnspan=4, pady=10)

    # Frame para los Treeviews
    frame_tree = ttk.Frame(ventana, padding=10)
    frame_tree.pack(fill="both", expand=True)

    # Treeview principal (ahora incluye Fecha_sistema)
    columnas = ["Id", "Fecha_sistema", "Fecha_registro", "Cedula", "Nombre", "Placa", 
                "Valor", "Saldos", "Tipo", "Nombre_cuenta", "Referencia", "Verificada"]

    tree = ttk.Treeview(frame_tree, columns=columnas, show="headings", height=10)

    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor='center')

    tree.pack(side="left", fill="both", expand=True)

    # Barra de desplazamiento vertical para el primer Treeview
    scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Frame para el Treeview auxiliar
    frame_totales = ttk.Frame(ventana, padding=10)
    frame_totales.pack(fill="x")

    # Treeview auxiliar para totales
    tree_totales = ttk.Treeview(frame_totales, columns=["Nombre_cuenta", "Total Valor"], show="headings", height=5)

    # Configuración de encabezados y centrado de columnas
    tree_totales.heading("Nombre_cuenta", text="Nombre_cuenta")
    tree_totales.column("Nombre_cuenta", width=150, anchor='center')

    tree_totales.heading("Total Valor", text="Total Valor")
    tree_totales.column("Total Valor", width=150, anchor='center')

    tree_totales.pack(side="left", fill="both", expand=True)

    # Barra de desplazamiento vertical para el Treeview auxiliar
    scrollbar_totales = ttk.Scrollbar(frame_totales, orient="vertical", command=tree_totales.yview)
    tree_totales.configure(yscroll=scrollbar_totales.set)
    scrollbar_totales.pack(side="right", fill="y")

    ventana.mainloop()

def ui_atrasos(entry_nombre, entry_placa, entry_cedula):

    def cargar_datos():
        try:
            conn = get_connection()
            registros = pd.read_sql("SELECT * FROM registros", conn)
            clientes = pd.read_sql("SELECT * FROM clientes", conn)
            return registros, clientes
        except Exception as e:
            print(f"Error al cargar datos: {e}")
            return pd.DataFrame(), pd.DataFrame()
        finally:
            conn.close()

    # Calcular el riesgo de deuda

    def calcular_cumplimiento_pago(pagos_cliente, valor_cuota, fecha_inicio, fecha_actual=None, dias_maximos=15):
        if fecha_actual is None:
            fecha_actual = datetime.now()

        if pagos_cliente['Fecha_sistema'].dtype == 'O':
            pagos_cliente.loc[:, 'Fecha_sistema'] = pd.to_datetime(pagos_cliente['Fecha_sistema'])

        # Limitar la fecha_inicio a máximo 10 días antes de la fecha_actual
        fecha_limite = fecha_actual - timedelta(days=dias_maximos - 1)
        fecha_desde = max(fecha_inicio, fecha_limite)

        pagos_filtrados = pagos_cliente[
            (pagos_cliente['Fecha_sistema'] >= fecha_desde) &
            (pagos_cliente['Fecha_sistema'] <= fecha_actual)
        ]

        dias_a_evaluar = (fecha_actual.date() - fecha_desde.date()).days + 1  # +1 para incluir hoy

        total_pagado = pagos_filtrados['Valor'].sum()
        #total_esperado = valor_cuota * dias_a_evaluar

        dias_cumplimiento = round((total_pagado / valor_cuota), 1)
        #print(f"Total Pagado: {total_pagado}, Dias:{dias_a_evaluar}, Cobertura: {dias_cumplimiento}")
        return dias_cumplimiento

    def calcular_atraso(registros, clientes):
        # Conexión a la base de datos SQLite
        conn = sqlite3.connect("diccionarios/base_dat.db")
        cursor = conn.cursor()

        fecha_actual = datetime.now()
        atraso_por_placa = []

        for _, cliente in clientes.iterrows():
            cedula = cliente['Cedula']
            nombre = cliente['Nombre']
            plazo = int(cliente['Fecha_final'])
            fecha_inicio = datetime.strptime(cliente['Fecha_inicio'], '%Y-%m-%d')
            valor_cuota = cliente['Valor_cuota']
            dias_transcurridos = (fecha_actual - fecha_inicio).days + 1
            dias_transcurridos = min(dias_transcurridos, plazo)
            monto_adeudado = dias_transcurridos * valor_cuota
            pagos_cliente = registros[registros['Cedula'] == cedula]

            if not pagos_cliente.empty:
                total_pagado = pagos_cliente['Valor'].sum()
                dias_cubiertos = total_pagado / valor_cuota if valor_cuota > 0 else 0
                dias_atraso = dias_transcurridos - dias_cubiertos
                atraso = monto_adeudado - total_pagado
            else:
                total_pagado = 0
                dias_cubiertos = 0
                dias_atraso = dias_transcurridos
                atraso = monto_adeudado

            pagos_por_dia = []
            pagos_ultimos_10_dias = []
            for i in range(10):
                fecha_consulta = fecha_actual - timedelta(days=i)
                pagos_en_fecha = pagos_cliente[pagos_cliente['Fecha_sistema'] == fecha_consulta.strftime('%Y-%m-%d')]
                pago_dia = pagos_en_fecha['Valor'].sum()/1000
                pagos_ultimos_10_dias.append(pago_dia)
                
            
            placa = cliente['Placa']
            # --- Cálculo de Inicial_P ---
            # Paso 1: obtener Otras_deudas
            cursor.execute("SELECT Otras_deudas FROM clientes WHERE Placa = ? AND Nombre = ?", (placa, nombre))
            resultado = cursor.fetchone()
            otras_deudas = resultado[0] if resultado and resultado[0] is not None else 0
            # Paso 2: sumar saldos en registros
            cursor.execute("SELECT SUM(saldos) FROM registros WHERE Placa = ? AND Nombre = ?", (placa, nombre))
            resultado = cursor.fetchone()
            suma_saldos = resultado[0] if resultado and resultado[0] is not None else 0

            try:
                otras_deudas = float(otras_deudas)
            except (ValueError, TypeError):
                otras_deudas = 0.0

            
            inicial_p = round(otras_deudas - suma_saldos, 0)
            # --- Append con Inicial_P al final ---
            cob10 = calcular_cumplimiento_pago(pagos_cliente, valor_cuota, fecha_inicio, fecha_actual)

            atraso_por_placa.append((
                placa, nombre, dias_transcurridos, cob10, round(dias_atraso, 1),
                round(atraso, 0), *pagos_ultimos_10_dias 
            ))

        conn.close()
        atraso_por_placa.sort(key=lambda x: x[4], reverse=True)  # Ordenar por Cob10 (4ta columna)
        return atraso_por_placa

    def copiar_al_portapapeles(event):
        selected_item = tree.selection()  # Obtener el elemento seleccionado
        if selected_item:
            valor = tree.item(selected_item, "values")[0]  # Primera columna
            name = tree.item(selected_item, "values")[1]
            antiguedad = float(tree.item(selected_item, "values")[2])
            rec15 = float(tree.item(selected_item, "values")[3])
            atraso = float(tree.item(selected_item, "values")[4])
            primer_nombre = name.split()[0]

            tope_permitido = antiguedad / 30 * 1.5

            if atraso <= 2:
                mensaje_atraso = "Gracias por estar al día con sus pagos."
            elif atraso > 5 and atraso > tope_permitido:
                mensaje_atraso = (
                    f"Actualmente registra {atraso} días de atraso en los pagos. "
                    f"Este valor supera el límite tolerado según la antigüedad del contrato ({tope_permitido:.1f} días permitidos)."
                )
            else:
                mensaje_atraso = f"Actualmente registra {atraso} días de atraso en los pagos."

            if rec15 >= 10:
                mensaje_recargas = "Se recomienda mantener la frecuencia actual de abonos."
            elif 8 <= rec15 < 10:
                mensaje_recargas = "Se solicita regularizar la frecuencia de los pagos diarios."
            else:
                if atraso > 7:
                    mensaje_recargas = (
                        "Debido a la baja frecuencia de pagos recientes y un atraso superior a 7 días, "
                        "el caso podría ser asignado al equipo de cobros para seguimiento presencial sin previo aviso."
                    )
                else:
                    mensaje_recargas = "Se recomienda normalizar la frecuencia de los pagos diarios."


            mensaje_personalizado = (
                f"{primer_nombre},\n"
                f"{mensaje_atraso}\n"
                f"En los últimos 15 días se han registrado {rec15} abonos.\n"
                f"{mensaje_recargas}"
            )

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT Cedula FROM clientes WHERE Nombre = ?", (name,))
            resultado = cursor.fetchone()
            conn.close()
            cedula = resultado[0] if resultado else None

            # Copiar valor_modificado inmediatamente
            if len(valor) == 6:
                valor_modificado = valor[:3] + '-' + valor[3:]
                root.clipboard_clear()
                root.clipboard_append(valor_modificado)
                root.update()

                # Definir función para copiar mensaje_personalizado
                def copiar_mensaje(event=None):
                    root.clipboard_clear()
                    root.clipboard_append(mensaje_personalizado)
                    root.update()

                # Vincular click derecho en la ventana raíz o en un widget específico
                root.bind('<Button-3>', copiar_mensaje)

            entry_nombre.delete(0, tk.END)
            entry_nombre.insert(0, name)
            entry_placa.delete(0, tk.END)
            entry_placa.insert(0, valor)
            entry_cedula.delete(0, tk.END)
            entry_cedula.insert(0, cedula)

    # Crear la interfaz gráfica para mostrar los datos

    registros, clientes = cargar_datos()
    atraso_por_placa = calcular_atraso(registros, clientes)

    # Crear la ventana principal
    root = tk.Toplevel()
    # Obtener alto de la pantalla
    alto_pantalla = root.winfo_screenheight()
    root.geometry(f"800x{alto_pantalla-100}")
    root.title("Reporte de Atrasos de Pagos")
    # Configurar el redimensionamiento de la ventana
    # Configurar el grid para que se expanda correctamente
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    

    tree = ttk.Treeview(root, columns=(
    "Placa", "Nombre", "Antiguedad","Rec15", "Días de Atraso", "Valor Atraso", 
    "Hoy", "Ayer", "Antier", "Día 4", "Día 5", "Día 6", "Día 7", "Día 8", "Día 9", "Día 10"
    ), show="headings")
    
    # Configurar encabezados
    encabezados = [
        ("Placa", "Placa"),
        ("Nombre", "Nombre"),
        ("Antiguedad", "Antigüedad"),
        ("Rec15", "Recaudo 15"),
        ("Días de Atraso", "Días de Atraso"),
        ("Valor Atraso", "Valor Atraso"),
        ("Hoy", "Hoy"),
        ("Ayer", "Ayer"),
        ("Antier", "Antier"),
        ("Día 4", "Día 4"),
        ("Día 5", "Día 5"),
        ("Día 6", "Día 6"),
        ("Día 7", "Día 7"),
        ("Día 8", "Día 8"),
        ("Día 9", "Día 9"),
        ("Día 10", "Día 10"),
    ]

    for col, text in encabezados:
        tree.heading(col, text=text)
        tree.column(col, anchor="center")
    # Asociar evento de doble clic
    tree.bind("<Double-1>", copiar_al_portapapeles)
    # Cargar el archivo JSON
    with open("diccionarios/black_list.json", "r", encoding="utf-8") as f:
        blacklist_data = json.load(f)
    # Crear un set con los nombres en lista negra
    nombres_en_blacklist = {
        valores["Nombre"] for valores in blacklist_data.values() if valores.get("Black_list") == "Si"
    }

    # Insertar los datos en la tabla
    tree.tag_configure("en_rojo", background="lightcoral")
    for atraso in atraso_por_placa:
        if "**" in atraso[0]:
            continue
        monto_formateado = f"${atraso[5]:,.0f}"
        pagos_formateados = [f"{int(pago):,}" for pago in atraso[6:16]]
        nombre = atraso[1]
        tags = ("en_rojo",) if nombre in nombres_en_blacklist else ()
        tree.insert("", "end", values=(
            atraso[0], atraso[1], atraso[2], atraso[3], atraso[4], monto_formateado, *pagos_formateados
        ), tags=tags)

    for col, text in encabezados:
        tree.heading(col, text=text)
        # Ajustar las columnas de pago a su contenido
        ancho = 100 if "Pago Día" in col else 150
        tree.column(col, anchor="center", width=ancho)
        
    # Insertar una fila en blanco
    tree.insert("", "end", values=("", "", "", ""))
    # Calcular el total de la columna "Valor Atraso"
    total_atraso = sum(atraso[4] for atraso in atraso_por_placa if atraso[4] > 0 and "**" not in atraso[0])

    # Formatear el total en COP
    total_formateado = f"${int(total_atraso):,}"
    # Insertar la fila "TOTAL" en negrita
    tree.insert("", "end", values=("TOTAL", "", "", total_formateado), tags=("total",))
    # Aplicar formato en negrita a la fila "TOTAL"
    tree.tag_configure("total", font=("Arial", 10, "bold"))
    # Colocar el Treeview en la ventana usando grid
    # Scrollbar vertical
    scrollbar_y = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.grid(row=0, column=2, sticky="ns")

    
    #tree.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    tree.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
    # Entry para filtrar
    entry_filtro = tk.Entry(root, font=("Arial", 12))
    entry_filtro.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
    
    # Botón para exportar
    btn_exportar = tk.Button(root, text="Exportar a Excel", command=lambda: export_tree_to_excel(tree))
    btn_exportar.grid(row=2, column=0, sticky="ew", padx=0, pady=5)
    btn_ruta = tk.Button(root, text="Reporte ruta", command=lambda: generar_tree_con_seleccion(tree))
    btn_ruta.grid(row=2, column=1, sticky="ew", padx=0, pady=5)


    def generar_tree_con_seleccion(tree_origen):
        seleccion = tree_origen.selection()
        if not seleccion:
            print("No hay registros seleccionados.")
            return

        # Crear nueva ventana
        nueva_ventana = tk.Toplevel()
        nueva_ventana.title("Registros seleccionados")

        # Crear nuevo Treeview
        tree_destino = ttk.Treeview(nueva_ventana, columns=tree_origen['columns'], show='headings')
        tree_destino.pack(fill="both", expand=True)

        # Añadir scrollbar vertical (opcional pero útil)
        scrollbar = ttk.Scrollbar(nueva_ventana, orient="vertical", command=tree_destino.yview)
        tree_destino.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Configurar columnas centradas
        for col in tree_origen["columns"]:
            tree_destino.heading(col, text=col)
            tree_destino.column(col, anchor="center", stretch=True, width=tree_origen.column(col)["width"])

        # Insertar solo los registros seleccionados
        for item_id in seleccion:
            valores = tree_origen.item(item_id, "values")
            tree_destino.insert("", "end", values=valores)

        return tree_destino

    def obtener_datos_treeview():
        """Obtiene los datos actuales del Treeview y los guarda como referencia."""
        return [tree.item(child)["values"] for child in tree.get_children()]

    # Guardar los datos originales del Treeview para restaurarlos al eliminar el filtro
    datos_originales = obtener_datos_treeview()
    
    def export_tree_to_excel(tree):
        # Obtener los encabezados del Treeview
        columns = [tree.heading(col)["text"] for col in tree["columns"]]

        # Obtener los datos del Treeview
        data = []
        for item in tree.get_children():
            data.append(tree.item(item)["values"])

        # Crear un DataFrame
        df = pd.DataFrame(data, columns=columns)

        # Guardar el archivo en una ubicación elegida por el usuario
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                filetypes=[("Excel files", "*.xlsx")],
                                                title="Guardar como")
        if file_path:
            df.to_excel(file_path, index=False)
            print(f"Exportado a: {file_path}")


    def filtrar_treeview(*args):
        """Filtra dinámicamente el Treeview según el texto en entry_filtro."""
        filtro = entry_filtro.get().strip().lower()  # Convertir a minúsculas

        # Limpiar el Treeview
        for item in tree.get_children():
            tree.delete(item)

        # Si el filtro está vacío, restaurar todos los datos
        if not filtro:
            for fila in datos_originales:
                tree.insert("", "end", values=fila)
            return

        # Índice de la columna a filtrar (AJUSTA según necesidad)
        columna_filtrar = 1  # Cambia el índice según la columna deseada

        # Filtrar y agregar solo las filas que coincidan en la columna específica
        for fila in datos_originales:
            if filtro in str(fila[columna_filtrar]).lower():  # Convertir a string y minúsculas
                tree.insert("", "end", values=fila)
    
    entry_filtro.bind("<KeyRelease>", filtrar_treeview)  # Filtrar al escribir


def calcular_atraso_simple():
    conn = get_connection()
    clientes = pd.read_sql("SELECT * FROM clientes", conn)
    registros = pd.read_sql("SELECT * FROM registros", conn)
    conn.close()

    clientes = clientes[~clientes['Placa'].str.contains(r'\*', regex=True)]
    df = clientes[['Placa', 'Cedula', 'Nombre', 'Fecha_inicio', 'Valor_cuota']].copy()

    hoy = datetime.now()
    df['Fecha_inicio'] = pd.to_datetime(df['Fecha_inicio'])
    df['dias_transcurridos'] = (hoy - df['Fecha_inicio']).dt.days + 1

    dias_atraso = []
    for _, fila in df.iterrows():
        cedula = fila['Cedula']
        placa = fila['Placa']
        valor_cuota = fila['Valor_cuota']

        pagos = registros[(registros['Cedula'] == cedula) & (registros['Placa'] == placa)]
        total_pagado = pagos['Valor'].sum()
        cuotas_pagas = total_pagado / valor_cuota if valor_cuota > 0 else 0
        atraso = fila['dias_transcurridos'] - cuotas_pagas
        dias_atraso.append(round(atraso, 1))

    df['dias_atraso'] = dias_atraso
    return df[['Placa', 'Cedula', 'Nombre', 'dias_atraso']].sort_values(by='dias_atraso', ascending=False)

def mostrar_atrasos_en_tree():
    df = calcular_atraso_simple()

    ventana = tk.Toplevel()
    ventana.title("Reporte de Atrasos")
    ventana.geometry("600x400")

    frame = tk.Frame(ventana)
    frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(frame, columns=list(df.columns), show='headings')
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")

    for _, fila in df.iterrows():
        tree.insert('', 'end', values=list(fila))

    ventana.mainloop()


def gestionar_blacklist():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT Nombre, Placa FROM clientes")
    clientes = cursor.fetchall()
    conn.close()

    if os.path.exists(BLACKLIST_PATH):
        try:
            with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    for nombre, placa in clientes:
        clave = f"{nombre}-{placa}"
        if clave not in data:
            data[clave] = {
                "Nombre": nombre,
                "Placa": placa,
                "Black_list": "No",
                "Observaciones": ""
            }

    with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    crear_ventana_blacklist(data)

def crear_ventana_blacklist(data):
    ventana = tk.Toplevel()
    ventana.title("Lista Negra de Clientes")

    style = ttk.Style()
    style.configure("Treeview.Heading", anchor="center")
    style.configure("Treeview", rowheight=25)

    columnas = ("Nombre", "Placa", "Black_list", "Observaciones")
    tree = ttk.Treeview(ventana, columns=columnas, show="headings")
    tree.grid(row=0, column=0, sticky="nsew")

    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", stretch=True)

    scrollbar = ttk.Scrollbar(ventana, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns")

    tree.tag_configure("marcado", background="lightcoral")

    for clave, valores in data.items():
        fila = (
            valores["Nombre"],
            valores["Placa"],
            valores["Black_list"],
            valores.get("Observaciones", "")
        )
        tags = ("marcado",) if valores["Black_list"] == "Si" else ()
        tree.insert("", "end", iid=clave, values=fila, tags=tags)

    def cambiar_estado(event):
        region = tree.identify_region(event.x, event.y)
        col = tree.identify_column(event.x)
        item = tree.identify_row(event.y)

        if not item:
            return

        col_index = int(col[1:]) - 1
        columnas_lista = list(columnas)

        if columnas_lista[col_index] == "Black_list":
            valores = tree.item(item, "values")
            nuevo_estado = "No" if valores[2] == "Si" else "Si"
            tree.set(item, "Black_list", nuevo_estado)
            data[item]["Black_list"] = nuevo_estado

            if nuevo_estado == "Si":
                tree.item(item, tags=("marcado",))
            else:
                tree.item(item, tags=())

        elif columnas_lista[col_index] == "Observaciones":
            x, y, width, height = tree.bbox(item, col)
            entry = tk.Entry(ventana)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, tree.set(item, "Observaciones"))
            entry.focus()

            def guardar(event):
                nuevo_valor = entry.get()
                tree.set(item, "Observaciones", nuevo_valor)
                data[item]["Observaciones"] = nuevo_valor
                entry.destroy()
                guardar_json()

            entry.bind("<Return>", guardar)
            entry.bind("<FocusOut>", lambda e: entry.destroy())

        guardar_json()

    def guardar_json():
        with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    tree.bind("<Double-1>", cambiar_estado)

    ventana.grid_rowconfigure(0, weight=1)
    ventana.grid_columnconfigure(0, weight=1)

def ordenar_por_columna(tree, col, descendente):
    datos = [(tree.set(k, col), k) for k in tree.get_children('')]

    try:
        datos.sort(key=lambda t: float(t[0]), reverse=descendente)
    except ValueError:
        datos.sort(key=lambda t: t[0], reverse=descendente)

    for index, (val, k) in enumerate(datos):
        tree.move(k, '', index)

    # Cambiar orden para el próximo clic
    tree.heading(col, command=lambda: ordenar_por_columna(tree, col, not descendente))

def abrir_gestion_deudas(parent=None):
    ventana = tk.Toplevel(parent) if parent else tk.Tk()
    ventana.title("Gestión de Deudas")
    ventana.geometry("1200x600")  # Ancho extra para acomodar el segundo TreeView

    # Carga y procesamiento de datos
    def cargar_datos():
        """ Carga y agrupa datos en el TreeView principal """
        for row in tree_principal.get_children():
            tree_principal.delete(row)

        conn = sqlite3.connect(DB_PATH)
        df_otras_deudas = pd.read_sql_query("SELECT * FROM otras_deudas", conn)
        df_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)
        df_registros = pd.read_sql_query("SELECT * FROM registros", conn)

        # Agrupar y totalizar por Cedula y Placa en otras_deudas
        df_agrupado = df_otras_deudas.groupby(['Cedula', 'Placa']).agg({'Valor': 'sum'}).reset_index()

        # 📝 --- Solución para evitar duplicados en el merge ---
        df_clientes_agrupado = df_clientes.groupby(['Cedula', 'Placa']).agg({
            'Nombre': 'first'
        }).reset_index()

        # Merge con el DataFrame de otras_deudas totalizado (para obtener el Nombre)
        df_final = pd.merge(df_agrupado, df_clientes_agrupado,
                            on=['Cedula', 'Placa'], how='left')

        # Obtener el saldo desde la tabla registros (sumado por Cedula y Placa)
        df_saldos = df_registros.groupby(['Cedula', 'Placa']).agg({'Saldos': 'sum'}).reset_index()

        # Merge con los saldos
        df_final = pd.merge(df_final, df_saldos, on=['Cedula', 'Placa'], how='left')

        # Calcular el estado de deuda
        df_final['estado_deuda'] = df_final['Valor'] - df_final['Saldos']
        df_final = df_final[['Cedula', 'Nombre', 'Placa', 'Valor', 'Saldos', 'estado_deuda']]
        conn.close()

        # Insertar datos en el TreeView principal
        for _, row in df_final.iterrows():
            tree_principal.insert("", "end", values=row.tolist())

    def forzar_mayusculas(event):
        contenido = entries["Placa"].get()
        entries["Placa"].delete(0, tk.END)
        entries["Placa"].insert(0, contenido.upper())

    # 📝 --- Interfaz gráfica ---
    form_frame = tk.Frame(ventana)
    form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    fields = ["Cedula", "Nombre", "Placa", "Fecha_deuda", "Descripcion", "Valor"]
    entries = {}
    for idx, field in enumerate(fields):
        tk.Label(form_frame, text=field).grid(row=0, column=idx*2, padx=5, pady=5)

        if field == "Fecha_deuda":
            entry = DateEntry(
                form_frame,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd-mm-yyyy'  # <--- Muestra como tú quieres
            )
        else:
            entry = tk.Entry(form_frame)

        entry.grid(row=0, column=idx*2 + 1, padx=5, pady=5)
        entries[field] = entry
    entries["Placa"].bind("<Return>", lambda event: completar_nombre_y_cedula(entries))
    entries["Placa"].bind("<KeyRelease>", forzar_mayusculas)
    
    def completar_nombre_y_cedula(entries):
        placa = entries["Placa"].get().strip().upper()

        if not placa:
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("SELECT Nombre, Cedula FROM clientes WHERE Placa = ?", (placa,))
            resultado = cursor.fetchone()

            if resultado:
                nombre, cedula = resultado
                entries["Nombre"].delete(0, tk.END)
                entries["Nombre"].insert(0, nombre)

                entries["Cedula"].delete(0, tk.END)
                entries["Cedula"].insert(0, cedula)
            else:
                messagebox.showinfo("Sin coincidencias", f"No se encontró la placa '{placa}' en la base de datos.")

        except Exception as e:
            messagebox.showerror("Error al consultar BD", str(e))
        finally:
            conn.close()

    def agregar_deuda():
        data = {field: entries[field].get().strip() for field in fields}
        
        # Validar cliente primero
        if not validar_cliente(data["Placa"], data["Nombre"], data["Cedula"]):
            messagebox.showerror("Error", "La combinación Placa, Nombre y Cédula no existe o no es única en la tabla clientes.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO otras_deudas (Cedula, Placa, Fecha_deuda, Descripcion, Valor) VALUES (?, ?, ?, ?, ?)",
                (
                    data["Cedula"],
                    data["Placa"],
                    data["Fecha_deuda"],
                    data["Descripcion"],
                    float(data["Valor"])
                )
            )
            conn.commit()
            conn.close()

            print("✅ Deuda agregada correctamente.")
            for entry in entries.values():
                entry.delete(0, tk.END)
            cargar_datos()

        except Exception as e:
            print(f"❌ Error al agregar deuda: {e}")
    
    def validar_cliente(placa, nombre, cedula):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM clientes WHERE Placa = ? AND Nombre = ? AND Cedula = ?",
                (placa, nombre, cedula)
            )
            resultado = cursor.fetchone()
            conn.close()

            return resultado[0] == 1  # True si existe y es único

        except Exception as e:
            print(f"❌ Error validando cliente: {e}")
            return False

    def eliminar_registro():
        """ Elimina el registro seleccionado en el TreeView de la tabla otras_deudas """
        selected_item = tree_principal.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "No hay un registro seleccionado.")
            return

        item_values = tree_principal.item(selected_item, 'values')
        # Ajusta índices según el orden de columnas en tu TreeView
        cedula = item_values[0]
        nombre = item_values[1]   # <- Asumo que Nombre está en la posición 1
        placa = item_values[2]
        valor = item_values[5]    # <- Ajusta si tu valor está en otra posición

        confirmacion = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar la deuda de {valor} para la Placa '{placa}' y Nombre '{nombre}'?"
        )
        if not confirmacion:
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM otras_deudas WHERE Cedula = ? AND Nombre = ? AND Placa = ? AND Valor = ?",
                (cedula, nombre, placa, valor)
            )
            conn.commit()
            conn.close()
            print(f"🗑️ Registro eliminado: {cedula} - {nombre} - {placa}")
            cargar_datos()

        except Exception as e:
            print(f"❌ Error al eliminar registro: {e}")

    def limpiar_campos():
        for entry in entries.values():
            entry.delete(0, tk.END)

    # Botones
    button_frame = tk.Frame(ventana)
    button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="w")
    
    # Configura un estilo para los botones (usa ttk si quieres más estilo)
    style = ttk.Style()
    style.configure("Custom.TButton", padding=6, font=('Segoe UI', 10, 'bold'))

    # Para usar ttk.Button con estilo:
    btn_add = ttk.Button(button_frame, text="Agregar Deuda", command=agregar_deuda, style="Custom.TButton")
    btn_del = ttk.Button(button_frame, text="Eliminar Registros", command=eliminar_registro, style="Custom.TButton")
    btn_limpiar = ttk.Button(button_frame, text="Limpiar", command=limpiar_campos, style="Custom.TButton")

    # Ubicación y estandarización de tamaño con sticky + weight en grid
    btn_add.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    btn_del.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
    btn_limpiar.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

    # Igualamos el tamaño de las columnas del button_frame para que los botones tengan el mismo ancho
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)
    button_frame.grid_columnconfigure(2, weight=1)

    

    tree_frame = tk.Frame(ventana)
    tree_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # Configura la ventana para que crezca y tree_frame también
    ventana.grid_rowconfigure(2, weight=1)
    ventana.grid_columnconfigure(0, weight=1)

    # TreeView Principal
    columns_principal = ("Cedula", "Nombre", "Placa", "Valor", "Saldos", "estado_deuda")
    tree_principal = ttk.Treeview(tree_frame, columns=columns_principal, show='headings')

    for col in columns_principal:
        tree_principal.heading(col, text=col)
        tree_principal.column(col, anchor='center')

    tree_principal.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

    # TreeView Secundario
    columns_secundario = ("Id", "Fecha_deuda", "Descripcion", "Valor")
    tree_secundario = ttk.Treeview(tree_frame, columns=columns_secundario, show='headings')

    for col in columns_secundario:
        tree_secundario.heading(col, text=col)
        tree_secundario.column(col, anchor='center')

    tree_secundario.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    # Que las dos columnas del frame se repartan igual el espacio
    tree_frame.grid_columnconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(1, weight=1)
    tree_frame.grid_rowconfigure(0, weight=1)


    # 🖱️ --- Evento de doble clic para cargar detalles ---
    def cargar_detalles(event):
        selected_item = tree_principal.selection()
        if not selected_item:
            return

        # Limpiar el TreeView secundario
        tree_secundario.delete(*tree_secundario.get_children())

        item_values = tree_principal.item(selected_item, 'values')
        
        if len(item_values) < 3:
            print("⚠️ El item seleccionado no tiene suficientes datos.")
            return

        cedula = item_values[0].strip()
        placa = item_values[2].strip().upper()

        try:
            conn = sqlite3.connect(DB_PATH)
            query = """
                SELECT id, Fecha_deuda, Descripcion, Valor 
                FROM otras_deudas 
                WHERE Cedula = ? AND Placa = ?
            """
            df_detalles = pd.read_sql_query(query, conn, params=(cedula, placa))
            conn.close()

            # Cargar datos en el segundo TreeView (asegúrate de que las columnas coincidan)
            for _, row in df_detalles.iterrows():
                tree_secundario.insert("", "end", values=row.tolist())

            print(f"🔍 {len(df_detalles)} registros encontrados para {cedula} - {placa}")
            
        except Exception as e:
            print(f"❌ Error al cargar detalles: {e}")

    # Asociar el evento de doble clic
    tree_principal.bind("<Double-1>", cargar_detalles)

    # Carga inicial
    cargar_datos()

def cargar_nombres_columnas():
    if not os.path.exists(JSON_PATH):
        columnas = ["Fecha"] + [f"Columna {i}" for i in range(1, 9)] + ["Total"]
        guardar_nombres_columnas(columnas)
    else:
        with open(JSON_PATH, 'r') as file:
            data = json.load(file)
            columnas = data.get("columnas", ["Fecha"] + [f"Columna {i}" for i in range(1, 9)] + ["Total"])
    return columnas

def guardar_nombres_columnas(columnas):
    with open(JSON_PATH, 'w') as file:
        json.dump({"columnas": columnas}, file, indent=4)

def generar_fechas():
    fecha_inicio = datetime(2025, 5, 1)
    fecha_actual = datetime.now()
    delta = fecha_actual - fecha_inicio
    fechas = [(fecha_inicio + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(delta.days + 1)]
    return fechas

def inicializar_excel():
    if not os.path.exists(XLSX_PATH):
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        columnas = cargar_nombres_columnas()
        ws.append(columnas)
        wb.save(XLSX_PATH)

def cargar_datos_desde_excel(tree):
    if os.path.exists(XLSX_PATH):
        df = pd.read_excel(XLSX_PATH, sheet_name="Datos")
        if not df.empty:
            for index, row in df.iterrows():
                valores = row.tolist()
                tree.insert("", "end", values=valores, tags=('par' if index % 2 == 0 else 'impar'))
        else:
            fechas = generar_fechas()
            for i, fecha in enumerate(fechas):
                valores = [fecha] + ["0"] * 8 + ["$0"]
                tree.insert("", "end", values=valores, tags=('par' if i % 2 == 0 else 'impar'))

def guardar_en_excel(tree):
    columnas = cargar_nombres_columnas()
    data = [columnas]

    for item in tree.get_children():
        valores = tree.item(item, 'values')
        data.append(valores)

    df = pd.DataFrame(data[1:], columns=data[0])
    df.to_excel(XLSX_PATH, sheet_name="Datos", index=False)

class EditableTreeview(ttk.Treeview):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.columnas = cargar_nombres_columnas()
        self["columns"] = self.columnas
        self["show"] = "headings"

        # Estilo de encabezados
        style = ttk.Style()
        style.configure("Treeview.Heading", background="#4A90E2", foreground="black", font=("Helvetica", 10, "bold"))
        style.configure("Treeview", rowheight=25)

        # Estilo de filas alternas
        self.tag_configure('par', background="#F0F0F0")
        self.tag_configure('impar', background="#FFFFFF")
        self.tag_configure('negrita', font=('Helvetica', 10, 'bold'))

        for col in self.columnas:
            self.heading(col, text=col)
            ancho = 100 if col != "Fecha" else 120
            self.column(col, width=ancho, anchor='center')
        
        # Estilo para la última columna (Total)
        self.column(self.columnas[-1], anchor='e')
        
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.xview)
        self.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.pack(expand=True, fill='both')
        self.bind("<Double-1>", self.start_edit)

    def start_edit(self, event):
        item = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if not item or column == '#1' or column == f"#{len(self.columnas)}":
            return

        col_index = int(column.replace("#", "")) - 1
        x, y, width, height = self.bbox(item, column)
        entry = tk.Entry(self.parent)
        entry.place(x=x, y=y + self.winfo_rooty() - self.parent.winfo_rooty(), width=width, height=height)
        entry.insert(0, self.item(item, 'values')[col_index])
        entry.focus()

        def on_focus_out(_):
            nuevo_valor = entry.get()
            if nuevo_valor.replace('.', '', 1).isdigit():
                valores = list(self.item(item, 'values'))
                valores[col_index] = nuevo_valor
                self.item(item, values=valores)
                self.actualizar_total(item)
            entry.destroy()

        entry.bind("<FocusOut>", on_focus_out)

    def actualizar_total(self, item):
        valores = list(self.item(item, 'values'))
        try:
            suma = sum(float(valores[i]) for i in range(1, 9))
            valores[-1] = f"${int(suma):,}"
            self.item(item, values=valores, tags=('negrita',))
        except ValueError:
            print("❌ Error al intentar sumar los valores.")

def iniciar_interfaz():
    # Configuración de la ventana principal
    root = tk.Tk()
    root.title("TreeView Editable - Estilo Excel")
    root.geometry("1200x600")

    tree = EditableTreeview(root)

    btn_guardar = tk.Button(root, text="Guardar en Excel", command=lambda: guardar_en_excel(tree))
    btn_guardar.pack(pady=10)

    inicializar_excel()
    cargar_datos_desde_excel(tree)

    root.mainloop()

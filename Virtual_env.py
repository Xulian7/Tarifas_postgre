import os
import subprocess
import sys

def entorno_existe():
    return os.path.isdir("env")

def instalar_pipreqs():
    try:
        import pipreqs
        print("✅ pipreqs ya está instalado.")
    except ImportError:
        print("📦 Instalando pipreqs...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pipreqs"])

def generar_requirements():
    print("📋 Generando requirements.txt desde los import con codificación UTF-8...")
    result = subprocess.run(
        ["pipreqs", ".", "--force", "--encoding", "utf-8"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        print("❌ Error al generar requirements.txt:")
        print(result.stderr)
    else:
        print("✅ requirements.txt generado con éxito.")

def crear_entorno():
    print("🧪 Creando entorno virtual 'env'...")
    subprocess.call([sys.executable, "-m", "venv", "env"])

def instalar_dependencias():
    print("🔧 Instalando dependencias en el entorno virtual...")
    pip_path = os.path.join("env", "Scripts", "pip.exe") if os.name == "nt" else os.path.join("env", "bin", "pip")

    if not os.path.exists("requirements.txt"):
        print("⚠️ No se encontró 'requirements.txt'. Nada que instalar.")
        return

    subprocess.call([pip_path, "install", "-r", "requirements.txt"])

# === MAIN ===
if entorno_existe():
    print("✅ El entorno virtual 'env' ya existe. Nada que hacer.")
else:
    instalar_pipreqs()
    generar_requirements()
    crear_entorno()
    instalar_dependencias()

print("\n🎉 Todo listo. Ahora activá el entorno manualmente con:")
if os.name == "nt":
    print("   PowerShell → .\\env\\Scripts\\Activate.ps1")
    print("   CMD        → env\\Scripts\\activate.bat")
else:
    print("   source env/bin/activate")

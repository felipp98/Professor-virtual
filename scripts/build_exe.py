import os
import subprocess
import sys

def build():
    print("🚀 Iniciando empacotamento do Language Buddy em .exe standalone...")

    # Garante que PyInstaller esteja instalado
    try:
        import PyInstaller
    except ImportError:
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=LanguageBuddy",
        "--onefile",
        "--noconsole",
        "--add-data=docs;docs",
        "--add-data=services;services",
        "app.py"
    ]

    print("Executando PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n✅ Sucesso! O executável foi gerado na pasta 'dist/LanguageBuddy.exe'.")
    else:
        print("\n❌ Ocorreu uma falha durante o empacotamento.")

if __name__ == "__main__":
    build()

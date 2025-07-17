#!/usr/bin/env python3
"""
Script para compilar assets de CKAN con Bootstrap 5
"""

import subprocess
import sys
import os
from pathlib import Path

def run_npm_install():
    """Instalar dependencias npm"""
    print("📦 Instalando dependencias npm...")
    try:
        result = subprocess.run(["npm", "install"], check=True, capture_output=True, text=True)
        print("✅ Dependencias npm instaladas")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def compile_less():
    """Compilar archivos Less"""
    print("🎨 Compilando archivos Less...")
    try:
        result = subprocess.run(["npm", "run", "build"], check=True, capture_output=True, text=True)
        print("✅ Archivos Less compilados")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error compilando Less: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando compilación de assets CKAN con Bootstrap 5")
    print("=" * 60)
    
    # Cambiar al directorio de CKAN
    ckan_dir = Path(__file__).parent
    os.chdir(ckan_dir)
    
    # Instalar dependencias
    if not run_npm_install():
        sys.exit(1)
    
    # Compilar Less
    if not compile_less():
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Compilación completada exitosamente!")
    print("💡 Ahora puedes reiniciar CKAN para ver los cambios")

if __name__ == "__main__":
    main()

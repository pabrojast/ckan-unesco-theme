#!/usr/bin/env python3
"""
Script para regenerar los assets de CKAN después de actualizar Bootstrap
"""

import os
import shutil
import glob
from pathlib import Path

def regenerate_assets():
    """Limpiar y regenerar los assets de CKAN"""
    print("🔄 Regenerando assets de CKAN...")
    
    project_root = Path(__file__).parent
    
    # Directorios donde CKAN guarda los assets compilados
    asset_dirs = [
        project_root / "ckanext" / "theme_ejemplo" / "public" / "base" / "gen",
        project_root / "ckanext" / "theme_ejemplo" / "public" / "gen",
    ]
    
    # Limpiar assets compilados existentes
    for asset_dir in asset_dirs:
        if asset_dir.exists():
            print(f"🗑️  Limpiando assets existentes en: {asset_dir}")
            shutil.rmtree(asset_dir)
    
    # También limpiar archivos de cache de webassets
    cache_files = [
        project_root / "ckanext" / "theme_ejemplo" / "public" / ".webassets-cache",
        project_root / ".webassets-cache"
    ]
    
    for cache_file in cache_files:
        if cache_file.exists():
            print(f"🗑️  Limpiando cache: {cache_file}")
            if cache_file.is_file():
                cache_file.unlink()
            else:
                shutil.rmtree(cache_file)
    
    print("✅ Assets limpiados. Reinicia CKAN para regenerar los assets.")
    print("💡 Comando: ckan run")

if __name__ == "__main__":
    regenerate_assets()

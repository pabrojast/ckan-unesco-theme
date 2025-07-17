#!/usr/bin/env python3
"""
Script de verificación post-actualización
Verifica que las actualizaciones de seguridad se aplicaron correctamente
"""

import os
import re
from pathlib import Path

def check_moment_version():
    """Verificar versión de Moment.js"""
    moment_path = Path("ckanext/theme_ejemplo/public/base/vendor/moment-with-locales.js")
    
    if not moment_path.exists():
        return False, "Archivo moment-with-locales.js no encontrado"
    
    try:
        with open(moment_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar versión
        version_match = re.search(r'M\.version="([^"]+)"', content)
        if version_match:
            version = version_match.group(1)
            if version >= "2.29.4":
                return True, f"✅ Moment.js v{version} - SEGURO"
            else:
                return False, f"❌ Moment.js v{version} - VULNERABLE"
        else:
            return False, "❌ No se pudo determinar la versión de Moment.js"
    
    except Exception as e:
        return False, f"❌ Error leyendo Moment.js: {e}"

def check_bootstrap_version():
    """Verificar versión de Bootstrap"""
    bootstrap_css_path = Path("ckanext/theme_ejemplo/public/base/vendor/bootstrap/css/bootstrap.css")
    bootstrap_js_path = Path("ckanext/theme_ejemplo/public/base/vendor/bootstrap.js")
    
    results = []
    
    # Verificar CSS
    if bootstrap_css_path.exists():
        try:
            with open(bootstrap_css_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar versión
            if "Bootstrap  v5.3.3" in content:
                results.append((True, "✅ Bootstrap CSS v5.3.3 - SEGURO"))
            elif "Bootstrap v3.4.1" in content:
                results.append((False, "❌ Bootstrap CSS v3.4.1 - VULNERABLE"))
            else:
                results.append((False, "❌ No se pudo determinar la versión de Bootstrap CSS"))
        
        except Exception as e:
            results.append((False, f"❌ Error leyendo Bootstrap CSS: {e}"))
    else:
        results.append((False, "❌ Archivo bootstrap.css no encontrado"))
    
    # Verificar JS
    if bootstrap_js_path.exists():
        try:
            with open(bootstrap_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar versión
            if "Bootstrap v5.3.3" in content:
                results.append((True, "✅ Bootstrap JS v5.3.3 - SEGURO"))
            elif "bootstrap-transition.js v2.0.3" in content:
                results.append((False, "❌ Bootstrap JS v2.0.3 - VULNERABLE"))
            else:
                results.append((False, "❌ No se pudo determinar la versión de Bootstrap JS"))
        
        except Exception as e:
            results.append((False, f"❌ Error leyendo Bootstrap JS: {e}"))
    else:
        results.append((False, "❌ Archivo bootstrap.js no encontrado"))
    
    return results

def check_backups():
    """Verificar que existen los backups"""
    backup_files = [
        "ckanext/theme_ejemplo/public/base/vendor/moment-with-locales.js.backup",
        "ckanext/theme_ejemplo/public/base/vendor/bootstrap.js.backup",
        "ckanext/theme_ejemplo/public/base/vendor/bootstrap/css/bootstrap.css.backup"
    ]
    
    results = []
    for backup_file in backup_files:
        path = Path(backup_file)
        if path.exists():
            results.append((True, f"✅ Backup existe: {backup_file}"))
        else:
            results.append((False, f"❌ Backup falta: {backup_file}"))
    
    return results

def main():
    """Función principal de verificación"""
    print("🔍 VERIFICACIÓN POST-ACTUALIZACIÓN DE SEGURIDAD")
    print("=" * 50)
    
    # Verificar Moment.js
    print("\n📅 Verificando Moment.js...")
    moment_ok, moment_msg = check_moment_version()
    print(f"   {moment_msg}")
    
    # Verificar Bootstrap
    print("\n🎨 Verificando Bootstrap...")
    bootstrap_results = check_bootstrap_version()
    bootstrap_ok = True
    for ok, msg in bootstrap_results:
        print(f"   {msg}")
        if not ok:
            bootstrap_ok = False
    
    # Verificar backups
    print("\n💾 Verificando backups...")
    backup_results = check_backups()
    backup_ok = True
    for ok, msg in backup_results:
        print(f"   {msg}")
        if not ok:
            backup_ok = False
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 50)
    
    vulnerabilities_fixed = 0
    total_vulnerabilities = 3
    
    if moment_ok:
        vulnerabilities_fixed += 1
        print("✅ Moment.js ReDoS vulnerability - RESUELTO")
    else:
        print("❌ Moment.js ReDoS vulnerability - PENDIENTE")
    
    if bootstrap_ok:
        vulnerabilities_fixed += 2
        print("✅ Bootstrap XSS vulnerabilities - RESUELTO")
        print("✅ Bootstrap Prototype pollution - RESUELTO")
    else:
        print("❌ Bootstrap vulnerabilities - PENDIENTE")
    
    print(f"\n🎯 Estado de seguridad: {vulnerabilities_fixed}/{total_vulnerabilities} vulnerabilidades resueltas")
    
    if vulnerabilities_fixed == total_vulnerabilities:
        print("🎉 ¡TODAS LAS VULNERABILIDADES CRÍTICAS HAN SIDO RESUELTAS!")
        print("✅ El proyecto está ahora SEGURO")
    else:
        print("⚠️  Algunas vulnerabilidades siguen pendientes")
        print("🔴 Acción requerida para completar la actualización")
    
    print("\n📋 Próximos pasos:")
    if vulnerabilities_fixed == total_vulnerabilities:
        print("1. 🧪 Ejecutar pruebas de la aplicación")
        print("2. 🌐 Verificar compatibilidad en navegadores")
        print("3. 📱 Probar responsive design")
        print("4. 🚀 Desplegar en producción")
    else:
        print("1. 🔧 Completar actualizaciones pendientes")
        print("2. 🔄 Volver a ejecutar este script")
        print("3. 📖 Consultar SECURITY_UPDATE_REPORT.md")

if __name__ == "__main__":
    main()

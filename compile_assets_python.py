#!/usr/bin/env python3
"""
Script alternativo para compilar assets de CKAN con Bootstrap 5
Sin dependencias de Node.js
"""

import os
import shutil
from pathlib import Path
import re

class CKANAssetCompiler:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.base_dir = self.project_root / "ckanext" / "theme_ejemplo" / "public" / "base"
        self.less_dir = self.base_dir / "less"
        self.css_dir = self.base_dir / "css"
        self.vendor_dir = self.base_dir / "vendor"
        
    def compile_bootstrap5_css(self):
        """Compilar Bootstrap 5 CSS directamente"""
        print("🎨 Compilando Bootstrap 5 CSS...")
        
        # Leer Bootstrap 5 CSS
        bootstrap_css_path = self.vendor_dir / "bootstrap" / "css" / "bootstrap.css"
        if not bootstrap_css_path.exists():
            print("  ❌ Bootstrap 5 CSS no encontrado")
            return False
            
        try:
            with open(bootstrap_css_path, 'r', encoding='utf-8') as f:
                bootstrap_css = f.read()
            
            # Leer CSS personalizado del theme si existe
            theme_css_path = self.project_root / "ckanext" / "theme_ejemplo" / "public" / "theme_ejemplo.css"
            theme_css = ""
            if theme_css_path.exists():
                with open(theme_css_path, 'r', encoding='utf-8') as f:
                    theme_css = f.read()
            
            # Combinar CSS
            combined_css = f"""/* Bootstrap 5.3.3 + CKAN UNESCO Theme */
/* Compiled: {os.path.basename(__file__)} */

/* Bootstrap 5.3.3 Core */
{bootstrap_css}

/* Bootstrap 3 Compatibility Classes */
.form-group {{
  margin-bottom: 1rem;
}}

.control-label {{
  font-weight: 500;
  margin-bottom: 0.5rem;
  display: block;
}}

.help-block {{
  margin-top: 0.25rem;
  font-size: 0.875em;
  color: #6c757d;
}}

.btn-default {{
  color: #212529;
  background-color: #f8f9fa;
  border-color: #dee2e6;
}}

.btn-default:hover {{
  color: #212529;
  background-color: #e9ecef;
  border-color: #dee2e6;
}}

.panel {{
  margin-bottom: 1rem;
  background-color: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}}

.panel-heading {{
  padding: 0.75rem 1.25rem;
  margin-bottom: 0;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  border-top-left-radius: 0.375rem;
  border-top-right-radius: 0.375rem;
}}

.panel-body {{
  padding: 1.25rem;
}}

.panel-footer {{
  padding: 0.75rem 1.25rem;
  background-color: #f8f9fa;
  border-top: 1px solid #dee2e6;
  border-bottom-left-radius: 0.375rem;
  border-bottom-right-radius: 0.375rem;
}}

/* Text alignment compatibility */
.text-left {{
  text-align: left !important;
}}

.text-right {{
  text-align: right !important;
}}

.pull-left {{
  float: left !important;
}}

.pull-right {{
  float: right !important;
}}

/* Grid system compatibility */
.col-xs-1, .col-xs-2, .col-xs-3, .col-xs-4, .col-xs-5, .col-xs-6,
.col-xs-7, .col-xs-8, .col-xs-9, .col-xs-10, .col-xs-11, .col-xs-12 {{
  position: relative;
  min-height: 1px;
  padding-left: 15px;
  padding-right: 15px;
  float: left;
}}

.col-xs-1 {{ width: 8.33333333%; }}
.col-xs-2 {{ width: 16.66666667%; }}
.col-xs-3 {{ width: 25%; }}
.col-xs-4 {{ width: 33.33333333%; }}
.col-xs-5 {{ width: 41.66666667%; }}
.col-xs-6 {{ width: 50%; }}
.col-xs-7 {{ width: 58.33333333%; }}
.col-xs-8 {{ width: 66.66666667%; }}
.col-xs-9 {{ width: 75%; }}
.col-xs-10 {{ width: 83.33333333%; }}
.col-xs-11 {{ width: 91.66666667%; }}
.col-xs-12 {{ width: 100%; }}

/* CKAN UNESCO Theme Styles */
{theme_css}

/* Custom overrides para mantener compatibilidad */
.navbar-default {{
  background-color: #f8f9fa;
  border-color: #dee2e6;
}}

.navbar-inverse {{
  background-color: #212529;
  border-color: #000;
}}

.alert-dismissible {{
  padding-right: 4rem;
}}

.alert-dismissible .btn-close {{
  position: absolute;
  top: 0;
  right: 0;
  z-index: 2;
  padding: 0.75rem 1.25rem;
}}
"""
            
            # Escribir CSS compilado
            main_css_path = self.css_dir / "main.css"
            with open(main_css_path, 'w', encoding='utf-8') as f:
                f.write(combined_css)
            
            print(f"  ✅ CSS compilado: {main_css_path}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error compilando CSS: {e}")
            return False
    
    def update_javascript_references(self):
        """Actualizar referencias JavaScript"""
        print("🔧 Actualizando referencias JavaScript...")
        
        try:
            # Copiar bootstrap.js al directorio JavaScript principal
            bootstrap_js_src = self.vendor_dir / "bootstrap.js"
            if bootstrap_js_src.exists():
                # Ya está en el lugar correcto
                print("  ✅ Bootstrap JS ya está en la ubicación correcta")
            else:
                print("  ⚠️  Bootstrap JS no encontrado")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error actualizando JavaScript: {e}")
            return False
    
    def create_webassets_config(self):
        """Crear configuración de webassets actualizada"""
        print("📋 Actualizando configuración de webassets...")
        
        try:
            # Actualizar webassets.yml del vendor
            vendor_webassets = self.vendor_dir / "webassets.yml"
            if vendor_webassets.exists():
                with open(vendor_webassets, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Asegurar que bootstrap-css esté configurado
                if 'bootstrap-css:' not in content:
                    # Agregar configuración de bootstrap-css
                    bootstrap_css_config = """
bootstrap-css:
  output: vendor/%(version)s_bootstrap.css
  filters: cssrewrite
  contents:
    - bootstrap/css/bootstrap.css
"""
                    content = content.replace('bootstrap:', f'{bootstrap_css_config}\nbootstrap:')
                
                # Asegurar que bootstrap JS preload incluya CSS
                content = re.sub(
                    r'(bootstrap:.*?preload:.*?)(\n      - vendor/jquery)',
                    r'\1\2\n      - vendor/bootstrap-css',
                    content,
                    flags=re.DOTALL
                )
                
                with open(vendor_webassets, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✅ Webassets actualizado")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error actualizando webassets: {e}")
            return False
    
    def cleanup_old_assets(self):
        """Limpiar assets antiguos"""
        print("🧹 Limpiando assets antiguos...")
        
        try:
            # Limpiar archivos compilados antiguos
            for pattern in ['*.min.css', '*_main.css', '*_bootstrap.css']:
                for file in self.css_dir.glob(pattern):
                    if file.name != 'main.css':
                        file.unlink()
                        print(f"  🗑️  Eliminado: {file.name}")
            
            print("  ✅ Assets antiguos limpiados")
            return True
            
        except Exception as e:
            print(f"  ❌ Error limpiando assets: {e}")
            return False
    
    def run_compilation(self):
        """Ejecutar compilación completa"""
        print("🚀 Iniciando compilación de assets CKAN con Bootstrap 5")
        print("=" * 60)
        
        steps = [
            ("Limpiar assets antiguos", self.cleanup_old_assets),
            ("Compilar Bootstrap 5 CSS", self.compile_bootstrap5_css),
            ("Actualizar JavaScript", self.update_javascript_references),
            ("Configurar webassets", self.create_webassets_config),
        ]
        
        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"❌ Error en: {step_name}")
                return False
        
        print("=" * 60)
        print("✅ Compilación completada exitosamente!")
        print("\n📋 Próximos pasos:")
        print("1. Reiniciar CKAN")
        print("2. Verificar que Bootstrap 5 se cargue correctamente")
        print("3. Probar componentes en el navegador")
        print("4. Ejecutar script de verificación: python verify_security_updates.py")
        
        return True

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    compiler = CKANAssetCompiler(project_root)
    
    print("Este script compilará los assets de CKAN con Bootstrap 5")
    print("¿Deseas continuar? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        compiler.run_compilation()
    else:
        print("Compilación cancelada.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script para integrar Bootstrap 5 correctamente con el sistema de compilación de CKAN 2.9.9
"""

import os
import shutil
from pathlib import Path
import json

class CKANBootstrapIntegrator:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.public_dir = self.project_root / "ckanext" / "theme_ejemplo" / "public"
        self.base_dir = self.public_dir / "base"
        self.less_dir = self.base_dir / "less"
        self.css_dir = self.base_dir / "css"
        self.vendor_dir = self.base_dir / "vendor"
        self.javascript_dir = self.base_dir / "javascript"
        
    def backup_original_files(self):
        """Crear backup de archivos originales"""
        print("📦 Creando backup de archivos originales...")
        
        backup_files = [
            self.less_dir / "main.less",
            self.css_dir / "main.css",
            self.vendor_dir / "bootstrap",
            self.javascript_dir / "main.js"
        ]
        
        try:
            for file_path in backup_files:
                if file_path.exists():
                    backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                    if file_path.is_dir():
                        if backup_path.exists():
                            shutil.rmtree(backup_path)
                        shutil.copytree(file_path, backup_path)
                    else:
                        shutil.copy2(file_path, backup_path)
                    print(f"  ✅ Backup creado: {backup_path}")
                else:
                    print(f"  ⚠️  Archivo no encontrado: {file_path}")
            return True
        except Exception as e:
            print(f"  ❌ Error creando backup: {e}")
            return False
    
    def update_bootstrap_vendor(self):
        """Actualizar archivos vendor de Bootstrap 5"""
        print("🔄 Actualizando archivos vendor de Bootstrap 5...")
        
        # Verificar que Bootstrap 5 esté en el directorio vendor
        bootstrap_css = self.vendor_dir / "bootstrap" / "css" / "bootstrap.css"
        bootstrap_js = self.vendor_dir / "bootstrap.js"
        
        if not bootstrap_css.exists():
            print("  ❌ Error: Bootstrap 5 CSS no encontrado en vendor/bootstrap/css/")
            return False
            
        if not bootstrap_js.exists():
            print("  ❌ Error: Bootstrap 5 JS no encontrado en vendor/")
            return False
            
        print("  ✅ Bootstrap 5 archivos vendor verificados")
        return True
    
    def update_main_less(self):
        """Actualizar main.less para importar Bootstrap 5"""
        print("🎨 Actualizando main.less para Bootstrap 5...")
        
        main_less_path = self.less_dir / "main.less"
        
        # Contenido actualizado para Bootstrap 5
        bootstrap5_less_content = """// Bootstrap 5.3.3 - Importado como CSS compilado
// CKAN Theme Bootstrap 5 Integration

// Importar Bootstrap 5 CSS compilado
@import (inline) "../vendor/bootstrap/css/bootstrap.css";

// Importar estilos específicos de CKAN
@import "ckan.less";

// Variables y overrides personalizados
@import "variables.less";

// Componentes personalizados del theme
@import "components.less";

// Responsive overrides
@import "responsive.less";

// Utilidades adicionales
@import "utilities.less";

// Theme específico UNESCO
@import "theme-unesco.less";
"""
        
        try:
            with open(main_less_path, 'w', encoding='utf-8') as f:
                f.write(bootstrap5_less_content)
            print(f"  ✅ {main_less_path} actualizado")
            return True
        except Exception as e:
            print(f"  ❌ Error actualizando main.less: {e}")
            return False
    
    def create_bootstrap5_overrides(self):
        """Crear archivos Less para overrides de Bootstrap 5"""
        print("🔧 Creando archivos de overrides para Bootstrap 5...")
        
        # Crear components.less para componentes personalizados
        components_less = self.less_dir / "components.less"
        components_content = """// Componentes personalizados para Bootstrap 5
// Overrides específicos para CKAN con Bootstrap 5

// Formularios - Compatibilidad con Bootstrap 5
.form-group {
  margin-bottom: 1rem;
}

// Botones - Mantener compatibilidad
.btn-default {
  @extend .btn-secondary;
}

// Paneles convertidos a Cards
.panel {
  @extend .card;
}

.panel-heading {
  @extend .card-header;
}

.panel-body {
  @extend .card-body;
}

.panel-footer {
  @extend .card-footer;
}

// Compatibilidad con clases de texto
.text-left {
  text-align: left !important;
}

.text-right {
  text-align: right !important;
}

.pull-left {
  float: left !important;
}

.pull-right {
  float: right !important;
}

// Grid system compatibility
.col-xs-1, .col-xs-2, .col-xs-3, .col-xs-4, .col-xs-5, .col-xs-6,
.col-xs-7, .col-xs-8, .col-xs-9, .col-xs-10, .col-xs-11, .col-xs-12 {
  position: relative;
  min-height: 1px;
  padding-left: 15px;
  padding-right: 15px;
}

@media (min-width: 576px) {
  .col-xs-1 { width: 8.33333333%; }
  .col-xs-2 { width: 16.66666667%; }
  .col-xs-3 { width: 25%; }
  .col-xs-4 { width: 33.33333333%; }
  .col-xs-5 { width: 41.66666667%; }
  .col-xs-6 { width: 50%; }
  .col-xs-7 { width: 58.33333333%; }
  .col-xs-8 { width: 66.66666667%; }
  .col-xs-9 { width: 75%; }
  .col-xs-10 { width: 83.33333333%; }
  .col-xs-11 { width: 91.66666667%; }
  .col-xs-12 { width: 100%; }
}
"""
        
        try:
            with open(components_less, 'w', encoding='utf-8') as f:
                f.write(components_content)
            print(f"  ✅ {components_less} creado")
        except Exception as e:
            print(f"  ❌ Error creando components.less: {e}")
            return False
            
        # Crear theme-unesco.less para estilos específicos del theme
        theme_less = self.less_dir / "theme-unesco.less"
        theme_content = """// Estilos específicos del theme UNESCO
// Mantener todas las personalizaciones existentes

// Importar estilos personalizados existentes del theme
// Esto preservará todas las customizaciones visuales actuales

// Si tienes un theme_ejemplo.css, sus estilos deben migrarse aquí
"""
        
        try:
            with open(theme_less, 'w', encoding='utf-8') as f:
                f.write(theme_content)
            print(f"  ✅ {theme_less} creado")
        except Exception as e:
            print(f"  ❌ Error creando theme-unesco.less: {e}")
            return False
            
        return True
    
    def update_javascript_modules(self):
        """Actualizar módulos JavaScript para Bootstrap 5"""
        print("🔧 Actualizando módulos JavaScript para Bootstrap 5...")
        
        # Crear un módulo para inicializar Bootstrap 5
        bootstrap5_module = self.javascript_dir / "bootstrap5-init.js"
        bootstrap5_content = """// Bootstrap 5 Initialization Module
// Inicialización de componentes Bootstrap 5 para CKAN

(function (ckan, jQuery) {
  'use strict';

  // Inicializar tooltips de Bootstrap 5
  function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // Inicializar popovers de Bootstrap 5
  function initPopovers() {
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
      return new bootstrap.Popover(popoverTriggerEl);
    });
  }

  // Inicializar cuando el DOM esté listo
  jQuery(document).ready(function() {
    initTooltips();
    initPopovers();
  });

  // Exponer funciones para uso en módulos
  ckan.bootstrap5 = {
    initTooltips: initTooltips,
    initPopovers: initPopovers
  };

})(this.ckan, this.jQuery);
"""
        
        try:
            with open(bootstrap5_module, 'w', encoding='utf-8') as f:
                f.write(bootstrap5_content)
            print(f"  ✅ {bootstrap5_module} creado")
        except Exception as e:
            print(f"  ❌ Error creando bootstrap5-init.js: {e}")
            return False
            
        return True
    
    def create_build_script(self):
        """Crear script de compilación para CKAN"""
        print("📋 Creando script de compilación...")
        
        build_script = self.project_root / "build_assets.py"
        build_content = """#!/usr/bin/env python3
\"\"\"
Script para compilar assets de CKAN con Bootstrap 5
\"\"\"

import subprocess
import sys
import os
from pathlib import Path

def run_npm_install():
    \"\"\"Instalar dependencias npm\"\"\"
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
    \"\"\"Compilar archivos Less\"\"\"
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
    \"\"\"Función principal\"\"\"
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
"""
        
        try:
            with open(build_script, 'w', encoding='utf-8') as f:
                f.write(build_content)
            
            # Hacer el script ejecutable
            os.chmod(build_script, 0o755)
            
            print(f"  ✅ {build_script} creado")
            return True
        except Exception as e:
            print(f"  ❌ Error creando build_assets.py: {e}")
            return False
    
    def run_integration(self):
        """Ejecutar integración completa"""
        print("🚀 Iniciando integración de Bootstrap 5 con CKAN 2.9.9")
        print("=" * 60)
        
        steps = [
            ("Crear backup", self.backup_original_files),
            ("Verificar Bootstrap 5", self.update_bootstrap_vendor),
            ("Actualizar main.less", self.update_main_less),
            ("Crear overrides", self.create_bootstrap5_overrides),
            ("Actualizar JavaScript", self.update_javascript_modules),
            ("Crear script de compilación", self.create_build_script),
        ]
        
        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"❌ Error en: {step_name}")
                return False
        
        print("=" * 60)
        print("✅ Integración completada exitosamente!")
        print("\n📋 Próximos pasos:")
        print("1. Ejecutar: python build_assets.py")
        print("2. Reiniciar CKAN")
        print("3. Verificar que Bootstrap 5 se cargue correctamente")
        print("4. Probar componentes en el navegador")
        
        return True

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    integrator = CKANBootstrapIntegrator(project_root)
    
    print("Este script integrará Bootstrap 5 con el sistema de compilación de CKAN 2.9.9")
    print("¿Deseas continuar? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        integrator.run_integration()
    else:
        print("Integración cancelada.")

if __name__ == "__main__":
    main()

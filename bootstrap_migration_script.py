#!/usr/bin/env python3
"""
Script de migración automática de Bootstrap 3 a Bootstrap 5
para CKAN UNESCO Theme

Este script automatiza los cambios más comunes en templates HTML
"""

import os
import re
import shutil
import glob
from pathlib import Path

class BootstrapMigrator:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "ckanext" / "theme_ejemplo" / "templates"
        self.backup_dir = self.project_root / "bootstrap_migration_backup"
        
        # Leer CSS personalizado para identificar clases que NO deben cambiarse
        self.custom_css_classes = self._analyze_custom_css()
        
        # Mapeo de clases Bootstrap 3 -> Bootstrap 5
        self.class_mappings = {
            # Sistema de Grid
            r'col-xs-(\d+)': r'col-\1',
            r'col-xs-offset-(\d+)': r'offset-\1',
            r'col-sm-offset-(\d+)': r'offset-sm-\1',
            r'col-md-offset-(\d+)': r'offset-md-\1',
            r'col-lg-offset-(\d+)': r'offset-lg-\1',
            
            # Utilidades de texto
            r'text-left': 'text-start',
            r'text-right': 'text-end',
            r'pull-left': 'float-start',
            r'pull-right': 'float-end',
            
            # Componentes
            r'panel(\s|")': r'card\1',
            r'panel-heading': 'card-header',
            r'panel-body': 'card-body',
            r'panel-footer': 'card-footer',
            r'panel-title': 'card-title',
            
            # Botones
            r'btn-default': 'btn-secondary',
            
            # Formularios
            r'form-group': 'mb-3',
            r'control-label': 'form-label',
            r'help-block': 'form-text',
            
            # Navegación
            r'navbar-default': 'navbar-light bg-light',
            r'navbar-inverse': 'navbar-dark bg-dark',
            
            # Alerts
            r'alert-dismissible': 'alert-dismissible fade show',
            
            # Modals
            r'modal-dialog-sm': 'modal-sm',
            r'modal-dialog-lg': 'modal-lg',
        }
        
        # Atributos JavaScript que necesitan actualización
        self.js_attributes = {
            r'data-toggle="modal"': 'data-bs-toggle="modal"',
            r'data-target="([^"]*)"': r'data-bs-target="\1"',
            r'data-toggle="dropdown"': 'data-bs-toggle="dropdown"',
            r'data-toggle="collapse"': 'data-bs-toggle="collapse"',
            r'data-toggle="tooltip"': 'data-bs-toggle="tooltip"',
            r'data-placement="([^"]*)"': r'data-bs-placement="\1"',
            r'data-dismiss="modal"': 'data-bs-dismiss="modal"',
            r'data-dismiss="alert"': 'data-bs-dismiss="alert"',
        }
    
    def _analyze_custom_css(self):
        """Analizar CSS personalizado para identificar clases que NO deben cambiarse"""
        custom_css_classes = set()
        css_path = self.project_root / "ckanext" / "theme_ejemplo" / "public" / "theme_ejemplo.css"
        
        if css_path.exists():
            try:
                with open(css_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Buscar selectores CSS que contengan clases de Bootstrap 3
                # Esto incluye selectores como .col-xs-1, .col-sm-1, etc.
                patterns = [
                    r'\.col-xs-\d+',
                    r'\.col-sm-\d+',
                    r'\.col-md-\d+',
                    r'\.col-lg-\d+',
                    r'\.pull-left',
                    r'\.pull-right',
                    r'\.text-left',
                    r'\.text-right',
                    r'\.panel',
                    r'\.btn-default'
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        custom_css_classes.add(match.group().replace('.', ''))
                
                if custom_css_classes:
                    print(f"⚠️  Clases encontradas en CSS personalizado (NO serán cambiadas): {custom_css_classes}")
                
            except Exception as e:
                print(f"⚠️  Error analizando CSS personalizado: {e}")
        
        return custom_css_classes
    
    def _is_protected_class(self, class_name):
        """Verificar si una clase está protegida por el CSS personalizado"""
        # Verificar si la clase exacta está en el CSS personalizado
        if class_name in self.custom_css_classes:
            return True
        
        # Verificar patrones específicos para clases con números
        for protected_class in self.custom_css_classes:
            if re.match(r'col-xs-\d+', protected_class) and re.match(r'col-xs-\d+', class_name):
                return True
            if re.match(r'col-sm-\d+', protected_class) and re.match(r'col-sm-\d+', class_name):
                return True
            if re.match(r'col-md-\d+', protected_class) and re.match(r'col-md-\d+', class_name):
                return True
            if re.match(r'col-lg-\d+', protected_class) and re.match(r'col-lg-\d+', class_name):
                return True
        
        return False
    
    def create_backup(self):
        """Crear backup de los templates antes de la migración"""
        print("Creando backup de templates...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        shutil.copytree(self.templates_dir, self.backup_dir)
        print(f"Backup creado en: {self.backup_dir}")
    
    def find_html_files(self):
        """Encontrar todos los archivos HTML en el directorio de templates"""
        return list(self.templates_dir.rglob("*.html"))
    
    def update_css_classes(self, content):
        """Actualizar clases CSS de Bootstrap 3 a Bootstrap 5 (respetando CSS personalizado)"""
        updated_content = content
        
        for old_pattern, new_class in self.class_mappings.items():
            # Encontrar todas las coincidencias del patrón
            matches = list(re.finditer(old_pattern, updated_content))
            
            # Procesar coincidencias en orden inverso para evitar problemas de índices
            for match in reversed(matches):
                matched_text = match.group()
                
                # Extraer el nombre de la clase para verificar si está protegida
                class_name = matched_text.strip().replace('"', '').replace("'", '')
                
                # Verificar si la clase está protegida por el CSS personalizado
                if self._is_protected_class(class_name):
                    print(f"    🔒 Clase protegida encontrada, NO se cambiará: {class_name}")
                    continue
                
                # Si no está protegida, aplicar el cambio
                if r'(\d+)' in old_pattern:
                    # Patrón con grupos de captura
                    new_text = re.sub(old_pattern, new_class, matched_text)
                else:
                    # Reemplazo simple
                    new_text = matched_text.replace(old_pattern, new_class)
                
                # Reemplazar en el contenido
                start, end = match.span()
                updated_content = updated_content[:start] + new_text + updated_content[end:]
        
        return updated_content
    
    def update_js_attributes(self, content):
        """Actualizar atributos JavaScript de Bootstrap 3 a Bootstrap 5"""
        updated_content = content
        
        for old_pattern, new_attr in self.js_attributes.items():
            updated_content = re.sub(old_pattern, new_attr, updated_content)
        
        return updated_content
    
    def update_icons(self, content):
        """Reemplazar Glyphicons con iconos modernos"""
        # Mapeo básico de glyphicons comunes
        icon_mappings = {
            r'<span class="glyphicon glyphicon-search"[^>]*></span>': '<i class="fas fa-search"></i>',
            r'<span class="glyphicon glyphicon-user"[^>]*></span>': '<i class="fas fa-user"></i>',
            r'<span class="glyphicon glyphicon-home"[^>]*></span>': '<i class="fas fa-home"></i>',
            r'<span class="glyphicon glyphicon-plus"[^>]*></span>': '<i class="fas fa-plus"></i>',
            r'<span class="glyphicon glyphicon-minus"[^>]*></span>': '<i class="fas fa-minus"></i>',
            r'<span class="glyphicon glyphicon-edit"[^>]*></span>': '<i class="fas fa-edit"></i>',
            r'<span class="glyphicon glyphicon-remove"[^>]*></span>': '<i class="fas fa-times"></i>',
            r'<span class="glyphicon glyphicon-ok"[^>]*></span>': '<i class="fas fa-check"></i>',
        }
        
        updated_content = content
        for old_icon, new_icon in icon_mappings.items():
            updated_content = re.sub(old_icon, new_icon, updated_content)
        
        return updated_content
    
    def process_file(self, file_path):
        """Procesar un archivo HTML individual"""
        print(f"Procesando: {file_path}")
        
        changes_made = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Aplicar transformaciones y recopilar cambios
            original_content = content
            
            # Actualizar clases CSS
            new_content = self.update_css_classes(content)
            if new_content != content:
                changes_made.append("CSS classes")
                content = new_content
            
            # Actualizar atributos JavaScript
            new_content = self.update_js_attributes(content)
            if new_content != content:
                changes_made.append("JavaScript attributes")
                content = new_content
            
            # Actualizar iconos
            new_content = self.update_icons(content)
            if new_content != content:
                changes_made.append("Icons")
                content = new_content
            
            # Solo escribir si hay cambios
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ Actualizado: {file_path}")
                print(f"     Cambios: {', '.join(changes_made)}")
                return True
            else:
                print(f"  ⚪ Sin cambios: {file_path}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error procesando {file_path}: {e}")
            return False
    
    def update_webassets(self):
        """Actualizar archivos webassets.yml para Bootstrap 5"""
        webassets_path = self.project_root / "ckanext" / "theme_ejemplo" / "public" / "base" / "vendor" / "webassets.yml"
        
        if webassets_path.exists():
            print(f"Actualizando {webassets_path}")
            
            try:
                with open(webassets_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Actualizar referencias a Bootstrap
                content = content.replace('bootstrap/js/bootstrap.js', 'bootstrap.js')
                content = content.replace('bootstrap/css/bootstrap.css', 'bootstrap.css')
                
                with open(webassets_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✅ webassets.yml actualizado")
                
            except Exception as e:
                print(f"  ❌ Error actualizando webassets.yml: {e}")
    
    def run_migration(self):
        """Ejecutar la migración completa"""
        print("🚀 Iniciando migración de Bootstrap 3 a Bootstrap 5")
        print("=" * 50)
        
        # Mostrar información sobre CSS personalizado
        if self.custom_css_classes:
            print(f"🔍 CSS personalizado detectado con {len(self.custom_css_classes)} clases protegidas")
            print("   Estas clases NO serán modificadas en los templates")
        else:
            print("✅ No se detectaron conflictos con CSS personalizado")
        
        print("=" * 50)
        
        # Crear backup
        self.create_backup()
        
        # Encontrar archivos HTML
        html_files = self.find_html_files()
        print(f"Encontrados {len(html_files)} archivos HTML")
        
        # Procesar archivos
        updated_files = 0
        for file_path in html_files:
            if self.process_file(file_path):
                updated_files += 1
        
        # Actualizar webassets
        self.update_webassets()
        
        print("=" * 50)
        print(f"✅ Migración completada!")
        print(f"   - Archivos procesados: {len(html_files)}")
        print(f"   - Archivos actualizados: {updated_files}")
        print(f"   - Backup guardado en: {self.backup_dir}")
        
        print("\n🔍 Próximos pasos:")
        print("1. Revisar los cambios manualmente")
        print("2. Probar la aplicación en el navegador")
        print("3. Verificar componentes JavaScript")
        print("4. Ajustar CSS personalizado si es necesario")
        print("5. Ejecutar las pruebas")
        
        print("\n🔄 Para revertir cambios:")
        print(f"   cp -r {self.backup_dir}/* {self.templates_dir}/")

def main():
    """Función principal"""
    project_root = Path(__file__).parent
    migrator = BootstrapMigrator(project_root)
    
    print("¿Deseas continuar con la migración de Bootstrap? (y/N): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        migrator.run_migration()
    else:
        print("Migración cancelada.")

if __name__ == "__main__":
    main()

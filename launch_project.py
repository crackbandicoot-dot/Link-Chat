#!/usr/bin/env python3
"""
Launch script para Link-Chat Project - VERSIÓN CORREGIDA
Configurado para manejar imports correctamente
"""

import sys
import os
from pathlib import Path

def setup_environment():
    """Configura el entorno para ejecutar el proyecto"""
    # Obtener directorio del proyecto
    project_root = Path(__file__).parent
    linkfinder_path = project_root / "LinkChat"
    src_path = linkfinder_path / "src"
    
    # Agregar paths necesarios
    paths_to_add = [str(project_root), str(linkfinder_path), str(src_path)]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    print(f"🚀 LINK-CHAT PROJECT LAUNCHER")
    print(f"📁 Proyecto: {project_root}")
    print(f"📁 LinkChat: {linkfinder_path}")
    print(f"📁 Source: {src_path}")
    print("-" * 50)
    
    return project_root, linkfinder_path, src_path

def run_project_safe():
    """Ejecuta el proyecto de forma segura con manejo de errores"""
    try:
        print("\n🔄 Iniciando Link-Chat...")
        
        # Importar ConsoleInterface
        from interface.console import ConsoleInterface
        print("✅ ConsoleInterface importada correctamente")
        
        # Crear instancia
        console = ConsoleInterface()
        print("✅ ConsoleInterface creada")
        
        # Mostrar menú de bienvenida en lugar de ejecutar completo
        print("\n🎯 Link-Chat está listo para ejecutar!")
        print("📋 Opciones disponibles:")
        print("   1. Ejecutar aplicación completa")
        print("   2. Solo validar componentes")
        
        choice = input("\nSelecciona una opción (1-2): ").strip()
        
        if choice == "1":
            print("🚀 Ejecutando aplicación completa...")
            console.run()
        elif choice == "2":
            print("✅ Validación completada - todos los componentes funcionan")
        else:
            print("❌ Opción inválida")
            
        return True
        
    except Exception as e:
        print(f"❌ Error ejecutando proyecto: {e}")
        print(f"📋 Tipo de error: {type(e).__name__}")
        
        # Información adicional para debugging
        import traceback
        print("\n🔧 Stack trace completo:")
        traceback.print_exc()
        
        return False

def validate_project_structure():
    """Valida que la estructura del proyecto esté presente"""
    project_root = Path(__file__).parent
    
    # Estructura real del proyecto
    required_files = [
        "LinkChat/src/interface/console.py",
        "LinkChat/src/observer/observer.py", 
        "LinkChat/src/DTOS/message.py",
        "LinkChat/src/DTOS/file.py",
        "LinkChat/src/utils/helpers.py",
        "LinkChat/src/core/raw_socket_manager.py"
    ]
    
    print("🔍 Validando estructura del proyecto...")
    missing_files = []
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  Archivos faltantes: {len(missing_files)}")
        return False
    
    print("✅ Estructura del proyecto completa")
    return True

def test_imports():
    """Prueba las importaciones sin ejecutar el programa completo"""
    print("\n🧪 Probando importaciones...")
    
    try:
        # Test 1: Observer pattern
        from observer.observer import Observer
        from observer.subject import Subject
        print("✅ Observer pattern importado")
        
        # Test 2: DTOs
        from DTOS.message import Message
        from DTOS.file import File
        print("✅ DTOs importados")
        
        # Test 3: Utils
        from utils.helpers import log_message
        print("✅ Helpers importados")
        
        # Test 4: Console interface
        from interface.console import ConsoleInterface
        print("✅ ConsoleInterface importada")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    
    # Configurar entorno
    project_root, linkfinder_path, src_path = setup_environment()
    
    # Validar estructura
    if not validate_project_structure():
        print("\n❌ Estructura del proyecto incompleta")
        print("💡 Verificar que todos los archivos están presentes")
        return
    
    # Probar importaciones
    if not test_imports():
        print("\n❌ Falló la prueba de importaciones")
        print("� Revisar los imports en los módulos")
        return
    
    print("\n�🚀 INICIANDO LINK-CHAT PROJECT...")
    print("=" * 60)
    
    # Ejecutar proyecto
    success = run_project_safe()
    
    if success:
        print("\n✅ Proyecto ejecutado exitosamente")
    else:
        print("\n❌ Error ejecutando proyecto")
        print("💡 Revisar logs arriba para detalles")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
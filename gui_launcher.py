#!/usr/bin/env python3
"""
Launcher para la interfaz gráfica de Link-Chat
Ejecuta la aplicación GUI basada en Tkinter

NOTA: Este script ejecuta el módulo como paquete de Python 
para resolver los imports relativos correctamente.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_requirements():
    """Verifica que se cumplan los requisitos para ejecutar la GUI"""
    import platform
    
    print("=" * 60)
    print("🚀 Link-Chat GUI Launcher")
    print("=" * 60)
    
    # Verificar sistema operativo
    os_name = platform.system()
    print(f"📋 Sistema operativo: {os_name}")
    
    # Verificar permisos
    if os_name != "Windows":
        import os as os_module
        if os_module.geteuid() != 0:
            print("⚠️  ADVERTENCIA: Se requieren permisos de root/administrador")
            print("   Ejecuta con: sudo python gui_launcher.py")
            response = input("\n¿Continuar de todos modos? (s/n): ")
            if response.lower() != 's':
                print("👋 Saliendo...")
                sys.exit(0)
    
    # Verificar Tkinter
    try:
        import tkinter
        print("✅ Tkinter disponible")
    except ImportError:
        print("❌ Error: Tkinter no está instalado")
        print("   Instala con: sudo apt-get install python3-tk (Linux)")
        sys.exit(1)
    
    print("✅ Requisitos verificados")
    print("-" * 60)

def main():
    """Función principal"""
    check_requirements()
    
    try:
        # Obtener paths
        project_root = Path(__file__).parent
        src_path = project_root / "src"
        
        # Verificar que existe el módulo GUI
        gui_module = src_path / "interface" / "gui" / "main_window.py"
        if not gui_module.exists():
            print(f"❌ Error: No se encuentra el módulo GUI en {gui_module}")
            sys.exit(1)
        
        print("🎨 Iniciando interfaz gráfica...")
        print("-" * 60)
        
        # Ejecutar el entry point de la GUI
        gui_entry_point = project_root / "gui_main.py"
        
        if not gui_entry_point.exists():
            print(f"❌ Error: No se encuentra {gui_entry_point}")
            sys.exit(1)
        
        # Ejecutar el script que configura correctamente los imports
        cmd = [sys.executable, str(gui_entry_point)]
        
        result = subprocess.run(cmd, cwd=str(project_root))
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n\n👋 Aplicación cerrada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error ejecutando la GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

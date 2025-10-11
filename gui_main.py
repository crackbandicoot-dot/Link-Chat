#!/usr/bin/env python3
"""
Entry point para la GUI de Link-Chat  
Este script debe ejecutarse desde la raíz del proyecto
"""
import sys
from pathlib import Path

# Este archivo debe ejecutarse como: python -m src.gui_main
# O desde la raíz: python src/gui_main.py

# Asegurarse de que el paquete src esté en el path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Importar desde src como paquete
    from src.interface.gui.main_window import main
    main()

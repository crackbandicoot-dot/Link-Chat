#!/usr/bin/env python3
"""
Link-Chat - Punto de entrada principal
Sistema de comunicación peer-to-peer usando raw sockets Ethernet
"""

import sys
import os





def main():
    """Función principal de Link-Chat"""
    try:
        from src.interface.console import ConsoleInterface
        
        print("Iniciando Link-Chat...")
        print("=" * 50)
        
        # Crear y ejecutar la interfaz de consola
        console = ConsoleInterface()
        console.start()
        console.main_menu()
        
    except KeyboardInterrupt:
        print("\nLink-Chat cerrado por el usuario")
        sys.exit(0)
    except ImportError as e:
        print(f"[ERROR] Error de importacion: {e}")
        print("Verifique que todas las dependencias estén instaladas")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
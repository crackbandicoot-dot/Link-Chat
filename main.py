import sys
import os

def main():
    """Función principal de Link-Chat"""
    # Diagnostic logging for Docker environment
    print("=== LINK-CHAT STARTUP DIAGNOSTICS ===")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Directory contents: {os.listdir('.')}")
    print(f"Platform: {sys.platform}")
    print(f"User: {os.getenv('USER', 'unknown')}")
    print("=" * 50)
    
    try:
        print("[DEBUG] Attempting to import ConsoleInterface...")
        from src.interface.console import ConsoleInterface
        print("[DEBUG] Import successful!")
        
        print("\nIniciando Link-Chat...")
        print("=" * 50)
        
        # Crear y ejecutar la interfaz de consola
        print("[DEBUG] Creating ConsoleInterface instance...")
        console = ConsoleInterface()
        print("[DEBUG] Starting console interface...")
        console.start()
    
    except KeyboardInterrupt:
        print("\nLink-Chat cerrado por el usuario")
        sys.exit(0)
    except ImportError as e:
        print(f"[ERROR] Error de importacion: {e}")
        print(f"[DEBUG] Import error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("\nVerifique que todas las dependencias estén instaladas")
        sys.exit(1)
    except PermissionError as e:
        print(f"[ERROR] Error de permisos: {e}")
        print("[DEBUG] Raw sockets require root/admin privileges")
        print("Tip: Run container with --privileged flag or CAP_NET_RAW capability")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
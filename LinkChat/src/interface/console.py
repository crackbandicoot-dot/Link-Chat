import os
import sys
import threading
import time
from typing import Optional, List, Dict
from utils.helpers import log_message, get_network_interfaces, format_file_size
from utils.constants import *
from core.raw_socket import RawSocketManager
from networking.discovery import DeviceDiscovery
from networking.messaging import MessageManager
from networking.file_transfer import FileTransferManager


class ConsoleInterface:
    """
    Interfaz de consola principal para Link-Chat
    """
    
    def __init__(self):
        """Inicializa la interfaz de consola"""
        self.socket_manager = None
        self.device_discovery = None
        self.message_manager = None
        self.file_manager = None
        self.is_running = False
        self.input_thread = None
        self.discovered_devices = {}
        
    def start(self) -> None:
        """Inicia la interfaz de consola"""
        self.show_welcome()
        
        # Seleccionar interfaz de red
        interface = self.select_network_interface()
        if not interface:
            print("❌ No se pudo seleccionar una interfaz de red.")
            return
        
        # Inicializar componentes
        if not self.initialize_components(interface):
            print("❌ Error inicializando componentes de red.")
            return
        
        # Mostrar menú principal
        self.main_menu()
    
    def show_welcome(self) -> None:
        """Muestra la pantalla de bienvenida"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*48 + "╗")
        print("║          LINK-CHAT             ║")
        print("║      Mensajería y Transferencia de Archivos ║")
        print("╚" + "="*48 + "╝")
        print()
        print("🚀 Iniciando Link-Chat...")
        print("⚠️  Nota: Esta aplicación requiere permisos de administrador")
        print()
    
    def select_network_interface(self) -> Optional[str]:
        """
        Permite al usuario seleccionar una interfaz de red
        
        Returns:
            Optional[str]: Nombre de la interfaz seleccionada
        """
        interfaces = get_network_interfaces()
        
        if not interfaces:
            print("❌ No se encontraron interfaces de red disponibles.")
            return None
        
        print("🔌 Interfaces de red disponibles:")
        print()
        
        for i, interface in enumerate(interfaces, 1):
            print(f"  {i}. {interface}")
        
        print()
        
        while True:
            try:
                choice = input(f"Seleccione una interfaz (1-{len(interfaces)}) [1]: ").strip()
                
                if not choice:
                    choice = "1"
                
                index = int(choice) - 1
                
                if 0 <= index < len(interfaces):
                    selected = interfaces[index]
                    print(f"✅ Interfaz seleccionada: {selected}")
                    return selected
                else:
                    print(f"❌ Opción inválida. Seleccione entre 1 y {len(interfaces)}")
                    
            except ValueError:
                print("❌ Por favor ingrese un número válido.")
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                sys.exit(0)
    
    def initialize_components(self, interface: str) -> bool:
        """
        Inicializa todos los componentes de red
        
        Args:
            interface: Interfaz de red a usar
            
        Returns:
            bool: True si se inicializó correctamente
        """
        try:
            print(f"\n🔧 Inicializando componentes en {interface}...")
            
            # Inicializar socket manager
            self.socket_manager = RawSocketManager(interface)
            if not self.socket_manager.start():
                return False
            
            # Inicializar descubrimiento de dispositivos
            self.device_discovery = DeviceDiscovery(self.socket_manager)
            self.device_discovery.start()
            
            # Registrar callback para dispositivos descubiertos
            self.device_discovery.register_callback(
                "console_update", 
                self._on_device_discovered
            )
            
            # Inicializar gestor de mensajes
            self.message_manager = MessageManager(self.socket_manager)
            self.message_manager.start()
            
            # Registrar callback para mensajes recibidos
            self.message_manager.register_callback(
                "console_display",
                self._on_message_received
            )
            
            # Inicializar gestor de archivos
            self.file_manager = FileTransferManager(self.socket_manager)
            self.file_manager.start()
            
            # Registrar callbacks para transferencia de archivos
            self.file_manager.register_callback(
                "console_progress",
                self._on_file_progress
            )
            
            self.is_running = True
            
            print("✅ Componentes inicializados correctamente")
            print(f"📡 MAC local: {self.socket_manager.local_mac}")
            print()
            
            # Iniciar descubrimiento automático
            self.device_discovery.start_discovery()
            
            return True
            
        except Exception as e:
            log_message("ERROR", f"Error inicializando componentes: {e}")
            return False
    
    def main_menu(self) -> None:
        """Muestra y maneja el menú principal"""
        while self.is_running:
            try:
                self.show_main_menu()
                choice = input("\nSeleccione una opción: ").strip()
                
                if choice == "1":
                    self.messaging_menu()
                elif choice == "2":
                    self.file_transfer_menu()
                elif choice == "3":
                    self.show_discovered_devices()
                elif choice == "4":
                    self.show_network_info()
                elif choice == "5":
                    self.settings_menu()
                elif choice == "0":
                    self.shutdown()
                    break
                else:
                    print("❌ Opción inválida. Intente de nuevo.")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                self.shutdown()
                break
            except Exception as e:
                log_message("ERROR", f"Error en menú principal: {e}")
                time.sleep(2)
    
    def show_main_menu(self) -> None:
        """Muestra el menú principal"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("╔" + "="*50 + "╗")
        print("║                LINK-CHAT MENÚ                 ║")
        print("╠" + "="*50 + "╣")
        print("║  1. 💬 Mensajería                            ║")
        print("║  2. 📁 Transferencia de Archivos             ║")
        print("║  3. 🔍 Dispositivos Descubiertos             ║")
        print("║  4. 🌐 Información de Red                    ║")
        print("║  5. ⚙️  Configuración                        ║")
        print("║  0. 🚪 Salir                                 ║")
        print("╚" + "="*50 + "╝")
        
        # Mostrar estado
        device_count = len(self.discovered_devices)
        print(f"\n📊 Estado: {device_count} dispositivos descubiertos")
        
        if self.socket_manager and self.socket_manager.local_mac:
            print(f"📡 MAC local: {self.socket_manager.local_mac}")
    
    def messaging_menu(self) -> None:
        """Menú de mensajería"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("╔" + "="*40 + "╗")
            print("║           MENSAJERÍA                 ║")
            print("╚" + "="*40 + "╝")
            print()
            
            print("1. 📤 Enviar mensaje a dispositivo")
            print("2. 📢 Enviar mensaje broadcast")
            print("3. 📥 Ver mensajes recibidos")
            print("0. ⬅️  Volver al menú principal")
            print()
            
            choice = input("Seleccione una opción: ").strip()
            
            if choice == "1":
                self.send_message_to_device()
            elif choice == "2":
                self.send_broadcast_message()
            elif choice == "3":
                self.show_received_messages()
            elif choice == "0":
                break
            else:
                print("❌ Opción inválida")
                time.sleep(1)
    
    def file_transfer_menu(self) -> None:
        """Menú de transferencia de archivos"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("╔" + "="*45 + "╗")
            print("║         TRANSFERENCIA DE ARCHIVOS        ║")
            print("╚" + "="*45 + "╝")
            print()
            
            print("1. 📤 Enviar archivo")
            print("2. 📥 Ver transferencias en progreso")
            print("3. 📋 Historial de transferencias")
            print("0. ⬅️  Volver al menú principal")
            print()
            
            choice = input("Seleccione una opción: ").strip()
            
            if choice == "1":
                self.send_file()
            elif choice == "2":
                self.show_transfer_progress()
            elif choice == "3":
                self.show_transfer_history()
            elif choice == "0":
                break
            else:
                print("❌ Opción inválida")
                time.sleep(1)
    
    def show_discovered_devices(self) -> None:
        """Muestra los dispositivos descubiertos"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║           DISPOSITIVOS DESCUBIERTOS           ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.discovered_devices:
            print("🔍 No se han descubierto dispositivos aún...")
            print("   El descubrimiento automático está en progreso.")
        else:
            print(f"📱 {len(self.discovered_devices)} dispositivos encontrados:")
            print()
            
            for i, (mac, info) in enumerate(self.discovered_devices.items(), 1):
                status = "🟢 Activo" if info.get('active', False) else "🔴 Inactivo"
                last_seen = info.get('last_seen', 'Desconocido')
                print(f"  {i}. MAC: {mac}")
                print(f"     Estado: {status}")
                print(f"     Última vez visto: {last_seen}")
                print()
        
        input("\nPresione Enter para continuar...")
    
    def show_network_info(self) -> None:
        """Muestra información de la red"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*45 + "╗")
        print("║          INFORMACIÓN DE RED              ║")
        print("╚" + "="*45 + "╝")
        print()
        
        if self.socket_manager:
            print(f"🔌 Interfaz: {self.socket_manager.interface}")
            print(f"📡 MAC local: {self.socket_manager.local_mac}")
            print(f"🌐 Protocolo: Link-Chat v{PROTOCOL_VERSION}")
            print(f"🔢 EtherType: 0x{ETHERTYPE_LINKCHAT:04X}")
        
        print()
        print("📊 Estadísticas:")
        # Aquí se pueden agregar estadísticas de red
        print("   - Mensajes enviados: N/A")
        print("   - Mensajes recibidos: N/A")
        print("   - Archivos transferidos: N/A")
        
        input("\nPresione Enter para continuar...")
    
    def settings_menu(self) -> None:
        """Menú de configuración"""
        print("⚙️ Configuración - En desarrollo...")
        time.sleep(2)
    
    def send_message_to_device(self) -> None:
        """Envía un mensaje a un dispositivo específico"""
        if not self.discovered_devices:
            print("❌ No hay dispositivos descubiertos para enviar mensajes.")
            input("Presione Enter para continuar...")
            return
        
        # Mostrar dispositivos disponibles
        print("📱 Dispositivos disponibles:")
        devices = list(self.discovered_devices.keys())
        
        for i, mac in enumerate(devices, 1):
            info = self.discovered_devices[mac]
            status = "🟢" if info.get('active', False) else "🔴"
            print(f"  {i}. {mac} {status}")
        
        try:
            choice = int(input(f"\nSeleccione dispositivo (1-{len(devices)}): ")) - 1
            if 0 <= choice < len(devices):
                target_mac = devices[choice]
                message = input("Ingrese el mensaje: ")
                
                if message.strip():
                    # Enviar mensaje usando MessageManager
                    success = self.message_manager.send_message(target_mac, message)
                    if success:
                        print("✅ Mensaje enviado correctamente")
                    else:
                        print("❌ Error enviando mensaje")
                else:
                    print("❌ Mensaje vacío")
            else:
                print("❌ Selección inválida")
                
        except ValueError:
            print("❌ Ingrese un número válido")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("Presione Enter para continuar...")
    
    def send_broadcast_message(self) -> None:
        """Envía un mensaje broadcast a todos los dispositivos"""
        message = input("Ingrese el mensaje broadcast: ")
        
        if message.strip():
            success = self.message_manager.send_broadcast_message(message)
            if success:
                print("✅ Mensaje broadcast enviado")
            else:
                print("❌ Error enviando mensaje broadcast")
        else:
            print("❌ Mensaje vacío")
        
        input("Presione Enter para continuar...")
    
    def send_file(self) -> None:
        """Envía un archivo a un dispositivo"""
        if not self.discovered_devices:
            print("❌ No hay dispositivos descubiertos.")
            input("Presione Enter para continuar...")
            return
        
        # Seleccionar archivo
        filepath = input("Ingrese la ruta del archivo: ").strip().strip('"')
        
        if not os.path.exists(filepath):
            print("❌ El archivo no existe")
            input("Presione Enter para continuar...")
            return
        
        if not os.path.isfile(filepath):
            print("❌ La ruta no es un archivo válido")
            input("Presione Enter para continuar...")
            return
        
        # Mostrar información del archivo
        file_size = os.path.getsize(filepath)
        print(f"📁 Archivo: {os.path.basename(filepath)}")
        print(f"📏 Tamaño: {format_file_size(file_size)}")
        
        # Seleccionar dispositivo destino
        print("\n📱 Dispositivos disponibles:")
        devices = list(self.discovered_devices.keys())
        
        for i, mac in enumerate(devices, 1):
            info = self.discovered_devices[mac]
            status = "🟢" if info.get('active', False) else "🔴"
            print(f"  {i}. {mac} {status}")
        
        try:
            choice = int(input(f"\nSeleccione dispositivo (1-{len(devices)}): ")) - 1
            if 0 <= choice < len(devices):
                target_mac = devices[choice]
                
                print(f"\n📤 Iniciando transferencia a {target_mac}...")
                success = self.file_manager.send_file(target_mac, filepath)
                
                if success:
                    print("✅ Transferencia iniciada")
                else:
                    print("❌ Error iniciando transferencia")
            else:
                print("❌ Selección inválida")
                
        except ValueError:
            print("❌ Ingrese un número válido")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("Presione Enter para continuar...")
    
    def show_received_messages(self) -> None:
        """Muestra los mensajes recibidos"""
        print("📥 Mensajes recibidos - En desarrollo...")
        time.sleep(2)
    
    def show_transfer_progress(self) -> None:
        """Muestra el progreso de transferencias"""
        print("📊 Progreso de transferencias - En desarrollo...")
        time.sleep(2)
    
    def show_transfer_history(self) -> None:
        """Muestra el historial de transferencias"""
        print("📋 Historial de transferencias - En desarrollo...")
        time.sleep(2)
    
    def _on_device_discovered(self, mac: str, info: Dict) -> None:
        """
        Callback llamado cuando se descubre un nuevo dispositivo
        
        Args:
            mac: Dirección MAC del dispositivo
            info: Información del dispositivo
        """
        self.discovered_devices[mac] = info
        # No imprimir aquí para evitar interferir con la interfaz
    
    def _on_message_received(self, sender_mac: str, message: str) -> None:
        """
        Callback llamado cuando se recibe un mensaje
        
        Args:
            sender_mac: MAC del remitente
            message: Contenido del mensaje
        """
        # En una implementación completa, esto se mostraría en una ventana separada
        # o se guardaría para mostrar en el menú de mensajes
        pass
    
    def _on_file_progress(self, transfer_id: str, progress: Dict) -> None:
        """
        Callback llamado para reportar progreso de transferencia
        
        Args:
            transfer_id: ID de la transferencia
            progress: Información de progreso
        """
        # Actualizar progreso de transferencias
        pass
    
    def shutdown(self) -> None:
        """Cierra la aplicación limpiamente"""
        print("\n🛑 Cerrando Link-Chat...")
        
        self.is_running = False
        
        # Detener componentes
        if self.device_discovery:
            self.device_discovery.stop()
        
        if self.message_manager:
            self.message_manager.stop()
        
        if self.file_manager:
            self.file_manager.stop()
        
        if self.socket_manager:
            self.socket_manager.stop()
        
        print("✅ Link-Chat cerrado correctamente")

import os
import sys
import threading
import time
import asyncio
from typing import Optional, List, Dict
from utils.helpers import log_message, get_network_interfaces, format_file_size
from utils.constants import *
from core.raw_socket_manager import raw_socket_manager
from networking.discovery import DeviceDiscovery
from networking.messaging import MessageService
from networking.file_transfer import FileTransferService
from observer.observer import Observer
from DTOS.message import Message
from DTOS.file import File


class ConsoleInterface(Observer[Dict], Observer[Message], Observer[File]):
    """
    Interfaz de consola principal para Link-Chat
    Implementa el patrón Observer para recibir notificaciones de dispositivos, mensajes y archivos
    """
    
    def __init__(self):
        """Inicializa la interfaz de consola"""
        self.socket_manager = None
        self.device_discovery = None
        self.message_service = None
        self.file_service = None
        self.is_running = False
        self.input_thread = None
        self.discovered_devices = {}
        self.received_messages = []
        self.received_files = []
        self.display_lock = threading.Lock()  # Para thread-safe console updates
        
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
            self.socket_manager = raw_socket_manager(interface)
            self.socket_manager.start_reciving()
               
            # Inicializar descubrimiento de dispositivos
            self.device_discovery = DeviceDiscovery(self.socket_manager)
            self.device_discovery.attach(self)  # Console observa cambios de dispositivos
            self.device_discovery.start_discovery()
            
            # Inicializar servicio de mensajes
            self.message_service = MessageService()
            self.socket_manager.attach(self.message_service)  # MessageService observa tramas
            self.message_service.attach(self)  # Console observa mensajes recibidos
            
            # Inicializar servicio de archivos
            self.file_service = FileTransferService()
            self.socket_manager.attach(self.file_service)  # FileService observa tramas
            self.file_service.attach(self)  # Console observa archivos recibidos

            self.is_running = True
            
            print("✅ Componentes inicializados correctamente")
            print(f"📡 MAC local: {getattr(self.socket_manager, 'local_mac', 'N/A')}")
            print()
            
            return True
            
        except Exception as e:
            log_message("INFO", "Hilo de heartbeat detenido")
    
    # Observer pattern implementation
    def update(self, data) -> None:
        """
        Implementación del patrón Observer para recibir notificaciones
        de dispositivos, mensajes y archivos
        
        Args:
            data: Puede ser Dict (dispositivos), Message (mensajes) o File (archivos)
        """
        with self.display_lock:
            if isinstance(data, dict) and 'mac' in data:
                # Notificación de dispositivo
                self._handle_device_update(data)
            elif isinstance(data, Message):
                # Notificación de mensaje
                self._handle_message_update(data)
            elif isinstance(data, File):
                # Notificación de archivo
                self._handle_file_update(data)
    
    def _handle_device_update(self, device_data: Dict) -> None:
        """Maneja actualizaciones de dispositivos"""
        mac = device_data['mac']
        info = device_data['info']
        action = device_data['action']
        
        if action == 'discovered':
            self.discovered_devices[mac] = info
            self._show_notification(f"🔍 Nuevo dispositivo descubierto: {mac}")
        elif action == 'updated':
            self.discovered_devices[mac] = info
        elif action == 'disconnected':
            if mac in self.discovered_devices:
                self.discovered_devices[mac]['active'] = False
            self._show_notification(f"📴 Dispositivo desconectado: {mac}")
    
    def _handle_message_update(self, message: Message) -> None:
        """Maneja mensajes recibidos"""
        self.received_messages.append(message)
        self._show_notification(f"💬 Mensaje de {message.sender_mac}: {message.text[:50]}...")
    
    def _handle_file_update(self, file: File) -> None:
        """Maneja archivos recibidos"""
        self.received_files.append(file)
        self._show_notification(f"📁 Archivo recibido: {file.name}")
    
    def _show_notification(self, message: str) -> None:
        """Muestra notificaciones en tiempo real"""
        # Solo mostrar si no estamos en un menú activo
        print(f"\n{message}")
        print("Presione Enter para continuar...")
    
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
                    # Enviar mensaje usando MessageService
                    import asyncio
                    success = asyncio.run(self.message_service.send_message(target_mac, message))
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
            import asyncio
            # Enviar a todos los dispositivos descubiertos
            success_count = 0
            for mac in self.discovered_devices.keys():
                if asyncio.run(self.message_service.send_message(mac, message)):
                    success_count += 1
            
            print(f"✅ Mensaje enviado a {success_count} dispositivos")
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
                try:
                    success = asyncio.run(self.file_transfer_service.send_file(target_mac, filepath))
                    
                    if success:
                        print("✅ Transferencia iniciada")
                    else:
                        print("❌ Error iniciando transferencia")
                except Exception as e:
                    print(f"❌ Error en transferencia: {e}")
            else:
                print("❌ Selección inválida")
                
        except ValueError:
            print("❌ Ingrese un número válido")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("Presione Enter para continuar...")
    
    def show_received_messages(self) -> None:
        """Muestra los mensajes recibidos"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║           MENSAJES RECIBIDOS                  ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.received_messages:
            print("📭 No hay mensajes recibidos aún...")
        else:
            print(f"📬 {len(self.received_messages)} mensajes recibidos:")
            print()
            
            for i, message in enumerate(self.received_messages[-10:], 1):  # Mostrar últimos 10
                print(f"  {i}. De: {message.sender_mac}")
                print(f"     📝 {message.text}")
                print()
        
        input("Presione Enter para continuar...")
    
    def show_transfer_progress(self) -> None:
        """Muestra el progreso de transferencias"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║        ARCHIVOS RECIBIDOS                     ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.received_files:
            print("📭 No hay archivos recibidos aún...")
        else:
            print(f"📬 {len(self.received_files)} archivos recibidos:")
            print()
            
            for i, file in enumerate(self.received_files, 1):
                print(f"  {i}. 📁 {file.name}")
            print()
        
        input("Presione Enter para continuar...")
    
    def show_transfer_history(self) -> None:
        """Muestra el historial de transferencias"""
        self.show_transfer_progress()  # Por ahora, mostrar lo mismo
    

    def shutdown(self) -> None:
        """Cierra la aplicación limpiamente"""
        print("\n� Cerrando Link-Chat...")
        
        self.is_running = False
        
        # Detener servicios
        if self.device_discovery:
            self.device_discovery.stop()
        
        # Cerrar socket manager
        if self.socket_manager:
            if hasattr(self.socket_manager, 'close_socket'):
                self.socket_manager.close_socket()
        
        print("✅ Link-Chat cerrado correctamente")
        sys.exit(0)


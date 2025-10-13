import os
import sys
import threading
import time
from typing import Optional, List, Dict, Union
from ..utils.helpers import log_message, get_network_interfaces
from ..utils.constants import *
from ..core.raw_socket_manager import raw_socket_manager
from ..networking.discovery import DeviceDiscovery
from ..networking.messaging import MessageManager  
from ..networking.file_transfer import FileTransferManager 
from ..observer.observer import Observer
from ..DTOS.message import Message
from ..DTOS.file import FileInfo
from .main_menu import MainMenu


class ConsoleInterface(Observer):
    """
    Main console interface for Link-Chat
    Implements Observer pattern to receive notifications from devices, messages and files
    """
    
    def __init__(self):
        """Initialize console interface"""
        self.socket_manager = None
        self.device_discovery = None
        self.message_service = None
        self.file_service = None
        self.is_running = False
        self.input_thread = None
        self.received_files = []
        self.display_lock = threading.Lock()
        self.waiting_for_input = False
        self.pending_notifications = []
        self.main_menu = None
        
    def start(self) -> None:
        """Start console interface"""
        self.show_welcome()
        
        # Select network interface
        interface = self.select_network_interface()
        if not interface:
            print("❌ No se pudo seleccionar una interfaz de red.")
            return
        
        # Initialize components
        if not self.initialize_components(interface):
            print("❌ Error inicializando componentes de red.")
            return
        
        # Initialize and show main menu
        self.main_menu = MainMenu(self)
        self.main_menu.main_menu_loop()
    
    def show_welcome(self) -> None:
        """Show welcome screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("LINK-CHAT")
        print("="*48)
        print("Mensajeria y Transferencia de Archivos")
        print("="*48)
        print()
        print("🚀 Iniciando Link-Chat...")
        print("⚠️  Nota: Esta aplicación requiere permisos de administrador")
        print()
    
    def select_network_interface(self) -> Optional[str]:
        """
        Allow user to select a network interface
        
        Returns:
            Optional[str]: Selected interface name
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
        Initialize all network components
        
        Args:
            interface: Network interface to use
            
        Returns:
            bool: True if initialized correctly
        """
        print(f"\n🔧 Inicializando componentes en {interface}...")
        
        # Initialize socket manager
        self.socket_manager = raw_socket_manager(interface)
        self.socket_manager.start_reciving()
           
        # Initialize device discovery
        self.device_discovery = DeviceDiscovery(self.socket_manager)
        self.device_discovery.attach(self)
        self.device_discovery.start_discovery()
        
        # Initialize message manager
        self.message_manager = MessageManager(self.socket_manager)
        self.message_manager.start()
        self.message_manager.attach(self)  # ConsoleInterface como observer de mensajes

        # Initialize file manager
        self.file_manager = FileTransferManager(self.socket_manager)
        self.file_manager.start()
        self.file_manager.attach(self)  
        
        self.is_running = True
        
        print("✅ Componentes inicializados correctamente")
        print(f"📡 MAC local: {self.socket_manager.get_local_mac()}")
        print()
        
        return True
        
    # Observer pattern implementation
    def update(self, data: Union[dict, Message, File]) -> None:
        """
        Observer pattern implementation to receive notifications
        from devices, messages and files

        Args:
            data: Can be Dict (devices), Message (messages) or File (files)
        """
        with self.display_lock:
            if isinstance(data, dict) and 'mac' in data:
                self._handle_device_update(data)
            elif isinstance(data, Message):
                self._handle_message_update(data)
            elif isinstance(data, File):
                self._handle_file_update(data)
    
    def _handle_device_update(self, device_data: Dict) -> None:
        """Handle device updates"""
        mac = device_data['mac']
        action = device_data['action']
        
        if action == 'discovered':
            self._show_notification(f"🔍 Nuevo dispositivo descubierto: {mac}")
        elif action == 'disconnected':
            self._show_notification(f"📴 Dispositivo desconectado: {mac}")
    
    def _handle_message_update(self, message: Message) -> None:
        """Handle received messages"""
        self._show_notification(f"💬 Mensaje de {message.sender_mac}: {message.content}")
    
    def _handle_file_update(self, file: FileInfo) -> None:
        """Handle received files"""
        self.received_files.append(file)
        self._show_notification(f"📁 Archivo recibido: {file.name}")
    
    def _show_notification(self, message: str) -> None:
        """Show notifications"""
        if self.waiting_for_input:
            self.pending_notifications.append(message)
        else:
            print(f"\n{message}")
            print("Presione Enter para continuar...")

    def get_received_messages(self) -> List[Message]:
        """Get last received messages"""
        if self.message_manager:
            return self.message_manager.get_received_messages()
        return []
    
    def shutdown(self) -> None:
        """Close application cleanly"""
        print("\n🔄 Cerrando Link-Chat...")

        self.is_running = False

        try:
            
            if self.device_discovery:
                self.device_discovery.detach(self)  
                self.device_discovery.stop()

            if self.message_manager: 
                self.message_manager.detach(self)
                self.message_manager.stop()

            if self.file_manager:  
                self.file_manager.detach(self)
                self.file_manager.stop()

            if self.socket_manager:
                self.socket_manager.stop_receiving() 
                self.socket_manager.close_socket()

            print("✅ Link-Chat cerrado correctamente")

        except Exception as e:
            log_message("ERROR", f"Error durante shutdown: {e}")
            print(f"⚠️ Error al cerrar: {e}")

        sys.exit(0)
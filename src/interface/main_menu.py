import os
import sys
import time
import asyncio
from typing import Optional, List
from ..utils.helpers import format_file_size
from ..utils.constants import BROADCAST_MAC,ETHERTYPE_LINKCHAT,PROTOCOL_VERSION


class MainMenu:
    """
    Handles all menu operations and user interactions
    """
    
    def __init__(self, console_interface):
        """
        Args:
            console_interface: Reference to ConsoleInterface for accessing services
        """
        self.console = console_interface
        
    def show_main_menu(self) -> None:
        """Shows the main menu"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("LINK-CHAT MENU")
        print("="*50)
        print("1. Mensajeria")
        print("2. Transferencia de Archivos")
        print("3. Dispositivos Descubiertos")
        print("4. Informacion de Red")
        print("0. Salir")
        print("="*50)
        
        # Show status
        device_count = len(self.console.device_discovery.discovered_devices) if self.console.device_discovery else 0
        print(f"\n📊 Estado: {device_count} dispositivos descubiertos")
    
    def main_menu_loop(self) -> None:
        """Main menu loop"""
        while self.console.is_running:
            try:
                self.show_main_menu()
                choice = self.safe_input("\nSeleccione una opción: ").strip()
                
                if choice == "1":
                    self.messaging_menu()
                elif choice == "2":
                    self.file_transfer_menu()
                elif choice == "3":
                    self.show_discovered_devices()
                elif choice == "4":
                    self.show_network_info()
                elif choice == "0":
                    self.console.shutdown()
                    break
                else:
                    print("❌ Opción inválida. Intente de nuevo.")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                self.console.shutdown()
                break
            except Exception as e:
                print(f"❌ Error en menú principal: {e}")
                time.sleep(2)
    
    def messaging_menu(self) -> None:
        """Messaging menu"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("╔" + "="*40 + "╗")
            print("║           MENSAJERÍA                   ║")
            print("╚" + "="*40 + "╝")
            print()
            
            print("1. 📤 Enviar mensaje a dispositivo")
            print("2. 📢 Enviar mensaje broadcast")
            print("3. 📥 Ver mensajes recibidos")
            print("0. ⬅️  Volver al menú principal")
            print()
            
            choice = self.safe_input("Seleccione una opción: ").strip()
            
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
        """File transfer menu"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("╔" + "="*45 + "╗")
            print("║         TRANSFERENCIA DE ARCHIVOS        ║")
            print("╚" + "="*45 + "╝")
            print()
            
            print("1. 📤 Enviar archivo")
            print("2. 📥 Ver historial de transferencias")
            print("0. ⬅️  Volver al menú principal")
            print()
            
            choice = self.safe_input("Seleccione una opción: ").strip()
            
            if choice == "1":
                self.send_file()
            elif choice == "2":
                self.show_transfer_historial()
            elif choice == "0":
                break
            else:
                print("❌ Opción inválida")
                time.sleep(1)
    
    def show_discovered_devices(self) -> None:
        """Shows discovered devices"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║           DISPOSITIVOS DESCUBIERTOS              ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.console.device_discovery or not self.console.device_discovery.discovered_devices:
            print("🔍 No se han descubierto dispositivos aún...")
            print("   El descubrimiento automático está en progreso.")
        else:
            devices = self.console.device_discovery.discovered_devices
            print(f"📱 {len(devices)} dispositivos encontrados:")
            print()
            
            for i, (mac, info) in enumerate(devices.items(), 1):
                status = "🟢 Activo" if info.get('active', False) else "🔴 Inactivo"
                last_seen = info.get('last_seen', 'Desconocido')
                print(f"  {i}. MAC: {mac}")
                print(f"     Estado: {status}")
                print(f"     Última vez visto: {last_seen}")
                print()
        
        input("\nPresione Enter para continuar...")
    
    def show_network_info(self) -> None:
        """Shows network information"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*45 + "╗")
        print("║          INFORMACIÓN DE RED              ║")
        print("╚" + "="*45 + "╝")
        print()
        
        if self.console.socket_manager:
            print(f"🔌 Interfaz: {self.console.socket_manager.interface}")
            print(f"📡 MAC local: {self.console.socket_manager.get_local_mac()}")
            print(f"🌐 Protocolo: Link-Chat v{PROTOCOL_VERSION}")
            print(f"🔢 EtherType: 0x{ETHERTYPE_LINKCHAT:04x}")
        
        print()  
        input("\nPresione Enter para continuar...")
    
    def send_message_to_device(self) -> None:
        """Sends a message to a specific device"""
        if not self.console.device_discovery or not self.console.device_discovery.discovered_devices:
            print("❌ No hay dispositivos descubiertos para enviar mensajes.")
            input("Presione Enter para continuar...")
            return
        devices = list(self.console.device_discovery.discovered_devices.keys())
        
        print("📱 Dispositivos disponibles:")
        for i, mac in enumerate(devices, 1):
            info = self.console.device_discovery.discovered_devices[mac]
            status = "🟢" if info.get('active', False) else "🔴"
            print(f"  {i}. {mac} {status}")
        
        try:
            choice = int(input(f"\nSeleccione dispositivo (1-{len(devices)}): ")) - 1
            if 0 <= choice < len(devices):
                target_mac = devices[choice]
                message = self.safe_input("Ingrese el mensaje: ")
                
                if message.strip():
                    success = asyncio.run(self.console.message_service.send_message(target_mac, message))
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
        """Sends a broadcast message to all devices"""
        message = self.safe_input("Ingrese el mensaje broadcast: ")
        
        if message.strip():
            if asyncio.run(self.console.message_service.send_message(BROADCAST_MAC, message)):
                print(f"✅ Mensaje enviado")
            else:
                print("❌ Error enviando mensaje broadcast")
        else:
            print("❌ Mensaje vacío")
        
        input("Presione Enter para continuar...")
    
    def send_file(self) -> None:
        """Sends a file to a device"""
        if not self.console.device_discovery or not self.console.device_discovery.discovered_devices:
            print("❌ No hay dispositivos descubiertos.")
            input("Presione Enter para continuar...")
            return

        filepath = self.safe_input("Ingrese la ruta del archivo: ").strip().strip('"')

        if not os.path.exists(filepath):
            print("❌ El archivo no existe")
            input("Presione Enter para continuar...")
            return
        
        if not os.path.isfile(filepath):
            print("❌ La ruta no es un archivo válido")
            input("Presione Enter para continuar...")
            return
        
        file_size = os.path.getsize(filepath)
        print(f"📁 Archivo: {os.path.basename(filepath)}")
        print(f"📏 Tamaño: {format_file_size(file_size)}")
        
        devices = list(self.console.device_discovery.discovered_devices.keys())
        
        print("\n📱 Dispositivos disponibles:")
        for i, mac in enumerate(devices, 1):
            info = self.console.device_discovery.discovered_devices[mac]
            status = "🟢" if info.get('active', False) else "🔴"
            print(f"  {i}. {mac} {status}")
        
        try:
            choice = int(input(f"\nSeleccione dispositivo (1-{len(devices)}): ")) - 1
            if 0 <= choice < len(devices):
                target_mac = devices[choice]
                
                print(f"\n📤 Iniciando transferencia a {target_mac}...")
                try:
                    success = asyncio.run(self.console.file_service.send_file(target_mac, filepath))
                    
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
        """Shows received messages"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║           MENSAJES RECIBIDOS                  ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.console.received_messages:
            print("📭 No hay mensajes recibidos aún...")
        else:
            print(f"📬 {len(self.console.get_received_messages())} mensajes recibidos:")
            print()
            
            for i, message in enumerate(self.console.received_messages[-10:], 1):
                print(f"  {i}. De: {message.sender_mac}")
                print(f"     📝 {message.text}")
                print()
        
        input("Presione Enter para continuar...")
    
    def show_transfer_historial(self) -> None:
        """Shows transfer history"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔" + "="*50 + "╗")
        print("║        ARCHIVOS RECIBIDOS                     ║")
        print("╚" + "="*50 + "╝")
        print()
        
        if not self.console.received_files:
            print("📭 No hay archivos recibidos aún...")
        else:
            print(f"📬 {len(self.console.received_files)} archivos recibidos:")
            print()
            
            for i, file in enumerate(self.console.received_files, 1):
                print(f"  {i}. 📁 {file.name}")
            print()
        
        input("Presione Enter para continuar...")
        
    def safe_input(self, prompt: str) -> str:
        """Input that blocks notifications"""
        
        self.console.waiting_for_input = True
        try:
            result = input(prompt)
        finally:
            self.console.waiting_for_input = False
            if self.console.pending_notifications:
                print(f"\n📱 {len(self.console.pending_notifications)} notificaciones:")
                for notification in self.console.pending_notifications:
                    print(f"  {notification}")
                self.console.pending_notifications.clear()
        return result
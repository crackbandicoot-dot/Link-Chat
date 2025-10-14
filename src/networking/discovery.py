import threading
import time
import json
from typing import Dict, List, Optional, Set
from ..utils.constants import *
from ..utils.helpers import log_message, create_message_id, get_timestamp
from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import raw_socket_manager
from ..observer.subject import Subject
from ..observer.observer import Observer


class DeviceDiscovery(Subject[Dict], Observer[LinkChatFrame]):
    """
    Maneja el descubrimiento automático de dispositivos Link-Chat en la red
    Implementa el patrón Observer para notificar cambios en dispositivos descubiertos
    y recibir tramas del raw_socket_manager
    """
    
    def __init__(self, socket_manager: raw_socket_manager):
        """
        Inicializa el sistema de descubrimiento
        
        Args:
            socket_manager: Manejador de raw sockets
        """
        
        self.socket_manager = socket_manager
        self.discovered_devices = {}
        self.discovery_thread = None
        self.heartbeat_thread = None
        self.is_running = False
        self.local_mac = socket_manager.get_local_mac()
        self.observers: Set[Observer[Dict]] = set()
        
        # Registrarse como observador del socket manager
        socket_manager.attach(self)
        
        
    def start_discovery(self) -> None:
        """Inicia el proceso de descubrimiento automático"""
         
        self.is_running = True

        if not self.discovery_thread or not self.discovery_thread.is_alive():
            self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
            self.discovery_thread.start()
        
        if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
        
        #log_message("INFO", "Descubrimiento automático iniciado")
    
    def stop(self) -> None:
        """Detiene el sistema de descubrimiento"""
        self.is_running = False
        
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.discovery_thread.join()
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        
        # Desregistrarse del socket manager
        self.socket_manager.detach(self)
        
        #log_message("INFO", "Sistema de descubrimiento detenido")
        
    def send_discovery_request(self) -> bool:
        """
        Envía una solicitud de descubrimiento broadcast
        
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear mensaje de descubrimiento
            discovery_data = {
                "type": "discovery_request",
                "timestamp": get_timestamp(),
            }
            
            data_bytes = json.dumps(discovery_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                BROADCAST_MAC,
                self.local_mac,
                MSG_TYPE_DISCOVERY,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                #log_message("DEBUG", "Solicitud de descubrimiento enviada")
                pass
            else:
                log_message("ERROR", "Error enviando solicitud de descubrimiento")
            
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de descubrimiento: {e}")
            return False
    
    def send_discovery_reply(self, target_mac: str) -> bool:
        """
        Envía una respuesta de descubrimiento a un dispositivo específico
        
        Args:
            target_mac: MAC del dispositivo al que responder
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear mensaje de respuesta
            reply_data = {
                "type": "discovery_reply",
                "timestamp": get_timestamp(),
            }
            
            data_bytes = json.dumps(reply_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                target_mac,
                self.local_mac,
                MSG_TYPE_DISCOVERY_REPLY,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                #log_message("DEBUG", f"Respuesta de descubrimiento enviada a {target_mac}")
                pass
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error enviando respuesta de descubrimiento: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """
        Envía un heartbeat para mantener la presencia activa
        
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear mensaje de heartbeat
            heartbeat_data = {
                "type": "heartbeat",
                "timestamp": get_timestamp()
            }
            
            data_bytes = json.dumps(heartbeat_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                BROADCAST_MAC,
                self.local_mac,
                MSG_TYPE_HEARTBEAT,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            return self.socket_manager.send_frame(frame)
            
        except Exception as e:
            log_message("ERROR", f"Error enviando heartbeat: {e}")
            return False
    
    def get_discovered_devices(self) -> Dict:
        """
        Obtiene la lista de dispositivos descubiertos
        
        Returns:
            Dict: Diccionario con dispositivos descubiertos
        """
        # Filtrar dispositivos inactivos
        current_time = get_timestamp()
        active_devices = {}
        
        for mac, info in self.discovered_devices.items():
            last_seen = info.get('last_seen', 0)
            was_active = info.get('active', True)
            
            if current_time - last_seen < DEVICE_TIMEOUT * 1000:  # Convertir a ms
                info['active'] = True
                active_devices[mac] = info
            elif mac in self.discovered_devices:
                info['active'] = False
                active_devices[mac] = info
                
                # Notificar si el dispositivo se volvió inactivo
                if was_active:
                    device_info = {
                        'mac': mac,
                        'info': info,
                        'action': 'disconnected'
                    }
                    self.notify(device_info)
        
        return active_devices
    
    # Observer[LinkChatFrame] implementation
    def update(self, frame: LinkChatFrame) -> None:
        self._handle_frame(frame)

    def _handle_frame(self, frame: LinkChatFrame) -> None:
        """
        Maneja tramas recibidas relacionadas con descubrimiento
        
        Args:
            frame: Trama Link-Chat recibida
        """
        try:
            # Procesar según el tipo de mensaje
            if frame.msg_type == MSG_TYPE_DISCOVERY:
                self._handle_discovery_request(frame)
            elif frame.msg_type == MSG_TYPE_DISCOVERY_REPLY:
                self._handle_discovery_reply(frame)
            elif frame.msg_type == MSG_TYPE_HEARTBEAT:
                self._handle_heartbeat(frame)
                
        except Exception as e:
            log_message("ERROR", f"Error procesando trama de descubrimiento: {e}")
    
    def _handle_discovery_request(self, frame: LinkChatFrame) -> None:
        """
        Maneja solicitudes de descubrimiento
        
        Args:
            src_mac: MAC del dispositivo que solicita
            frame: Trama Link-Chat recibida
        """
        try:            
            #log_message("INFO", f"Solicitud de descubrimiento de {frame.src_mac}")
            
            # Agregar dispositivo a la lista
            self._add_device(frame.src_mac, {
                "type": "discovery_request",
                "last_seen": get_timestamp(),
                "active": True
            })
            
            # Enviar respuesta
            self.send_discovery_reply(frame.src_mac)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando solicitud de descubrimiento: {e}")
    
    def _handle_discovery_reply(self, frame: LinkChatFrame) -> None:
        """
        Maneja respuestas de descubrimiento
        
        Args:
            src_mac: MAC del dispositivo que responde
            frame: Trama Link-Chat recibida
        """
        try:       
            #log_message("INFO", f"Respuesta de descubrimiento de {frame.src_mac}")
            
            # Agregar dispositivo a la lista
            self._add_device(frame.src_mac, {
                "type": "discovery_reply",
                "last_seen": get_timestamp(),
                "active": True
            })
            
        except Exception as e:
            log_message("ERROR", f"Error procesando respuesta de descubrimiento: {e}")
    
    def _handle_heartbeat(self, frame: LinkChatFrame) -> None:
        """
        Maneja mensajes de heartbeat
        
        Args:
            src_mac: MAC del dispositivo
            frame: Trama Link-Chat recibida
        """
        try:
            # Actualizar última vez visto
            if frame.src_mac in self.discovered_devices:
                self.discovered_devices[frame.src_mac]['last_seen'] = get_timestamp()
                self.discovered_devices[frame.src_mac]['active'] = True
                
                #log_message("DEBUG", f"Heartbeat recibido de {frame.src_mac}")
            
        except Exception as e:
            log_message("ERROR", f"Error procesando heartbeat: {e}")
    
    def _add_device(self, mac: str, info: Dict) -> None:
        """
        Agrega un dispositivo a la lista de descubiertos
        
        Args:
            mac: Dirección MAC del dispositivo
            info: Información del dispositivo
        """
        if mac == self.local_mac:
            return  # No agregar a nosotros mismos
        
        is_new = mac not in self.discovered_devices
        self.discovered_devices[mac] = info
        
        if is_new:
            log_message("INFO", f"Nuevo dispositivo descubierto: {mac}")
            pass
        
        # Notificar a observadores usando patrón Observer
        device_info = {
            'mac': mac,
            'info': info,
            'action': 'discovered' if is_new else 'updated'
        }
        self.notify(device_info)
    
    def _discovery_loop(self) -> None:
        """Hilo principal para envío periódico de descubrimiento"""
        #log_message("INFO", "Hilo de descubrimiento iniciado")
        
        while self.is_running:
            try:
                self.send_discovery_request()
                time.sleep(DISCOVERY_INTERVAL)
            except Exception as e:
                log_message("ERROR", f"Error en loop de descubrimiento: {e}")
                time.sleep(5)
        
        #log_message("INFO", "Hilo de descubrimiento detenido")
    
    def _heartbeat_loop(self) -> None:
        """Hilo principal para envío periódico de heartbeat"""
        #log_message("INFO", "Hilo de heartbeat iniciado")
        
        while self.is_running:
            try:
                self.send_heartbeat()
                time.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                log_message("ERROR", f"Error en loop de heartbeat: {e}")
                time.sleep(5)
        
    
    # Observer pattern implementation
    def attach(self, observer: Observer[Dict]) -> None:
        self.observers.add(observer)
    
    def detach(self, observer: Observer[Dict]) -> None:
        self.observers.discard(observer)
    
    def notify(self, device_data: Dict) -> None:
        for observer in self.observers:
            observer.update(device_data)
            
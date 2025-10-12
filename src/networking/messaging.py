"""
Sistema de mensajería para Link-Chat
"""

import json
import threading
import time
from typing import Dict, List, Callable, Optional
from utils.constants import *
from utils.helpers import log_message, create_message_id, get_timestamp
from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import RawSocketManager


class Message:
    """Representa un mensaje en el sistema"""
    
    def __init__(self, msg_id: int, sender_mac: str, content: str, 
                 timestamp: int, is_broadcast: bool = False):
        self.msg_id = msg_id
        self.sender_mac = sender_mac
        self.content = content
        self.timestamp = timestamp
        self.is_broadcast = is_broadcast
        self.acknowledged = False


class MessageManager:
    """
    Maneja el envío y recepción de mensajes de texto
    """
    
    def __init__(self, socket_manager: RawSocketManager):
        """
        Inicializa el gestor de mensajes
        
        Args:
            socket_manager: Manejador de raw sockets
        """
        self.socket_manager = socket_manager
        self.local_mac = socket_manager.get_local_mac()
        
        # Almacenamiento de mensajes
        self.sent_messages = {}      # ID -> Message
        self.received_messages = {}  # ID -> Message
        self.message_queue = []      # Lista de mensajes recibidos ordenados
        
        # Callbacks para notificaciones
        self.callbacks = {}
        
        # Control de hilos
        self.is_running = False
        self.ack_timeout_thread = None
    
    def start(self) -> None:
        """Inicia el gestor de mensajes"""
        self.is_running = True
        
        # Iniciar hilo para manejo de timeouts de ACK
        self.ack_timeout_thread = threading.Thread(target=self._ack_timeout_loop, daemon=True)
        self.ack_timeout_thread.start()
        
        log_message("INFO", "Gestor de mensajes iniciado")
    
    def stop(self) -> None:
        """Detiene el gestor de mensajes"""
        self.is_running = False
        
        if self.ack_timeout_thread and self.ack_timeout_thread.is_alive():
            self.ack_timeout_thread.join(timeout=2)
        
        # Desregistrar callback
        self.socket_manager.unregister_callback("messaging")
        
        log_message("INFO", "Gestor de mensajes detenido")
    
    def send_message(self, target_mac: str, content: str) -> bool:
        """
        Envía un mensaje de texto a un dispositivo específico
        
        Args:
            target_mac: MAC del dispositivo destino
            content: Contenido del mensaje
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Validar contenido
            if len(content.encode('utf-8')) > MAX_MESSAGE_SIZE:
                log_message("ERROR", "Mensaje demasiado largo")
                return False
            
            # Crear ID único para el mensaje
            msg_id = create_message_id()
            
            # Crear datos del mensaje
            message_data = {
                "type": "text_message",
                "content": content,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac,
                "msg_id": msg_id
            }
            
            data_bytes = json.dumps(message_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                target_mac,
                self.local_mac,
                MSG_TYPE_MESSAGE,
                msg_id,
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                # Guardar mensaje enviado
                message = Message(
                    msg_id, self.local_mac, content, 
                    get_timestamp(), False
                )
                self.sent_messages[msg_id] = message
                
                log_message("INFO", f"Mensaje enviado a {target_mac}: {content[:50]}...")
            else:
                log_message("ERROR", "Error enviando mensaje")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de mensaje: {e}")
            return False
    
    def send_broadcast_message(self, content: str) -> bool:
        """
        Envía un mensaje broadcast a todos los dispositivos
        
        Args:
            content: Contenido del mensaje
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Validar contenido
            if len(content.encode('utf-8')) > MAX_MESSAGE_SIZE:
                log_message("ERROR", "Mensaje demasiado largo")
                return False
            
            # Crear ID único para el mensaje
            msg_id = create_message_id()
            
            # Crear datos del mensaje
            message_data = {
                "type": "broadcast_message",
                "content": content,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac,
                "msg_id": msg_id
            }
            
            data_bytes = json.dumps(message_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                BROADCAST_MAC,
                self.local_mac,
                MSG_TYPE_BROADCAST,
                msg_id,
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                # Guardar mensaje enviado
                message = Message(
                    msg_id, self.local_mac, content,
                    get_timestamp(), True
                )
                self.sent_messages[msg_id] = message
                
                log_message("INFO", f"Mensaje broadcast enviado: {content[:50]}...")
            else:
                log_message("ERROR", "Error enviando mensaje broadcast")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de mensaje broadcast: {e}")
            return False
    
    def send_message_ack(self, target_mac: str, original_msg_id: int) -> bool:
        """
        Envía un acknowledgment de mensaje
        
        Args:
            target_mac: MAC del dispositivo que envió el mensaje original
            original_msg_id: ID del mensaje original
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear datos del ACK
            ack_data = {
                "type": "message_ack",
                "original_msg_id": original_msg_id,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac
            }
            
            data_bytes = json.dumps(ack_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                target_mac,
                self.local_mac,
                MSG_TYPE_MESSAGE_ACK,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                log_message("DEBUG", f"ACK enviado a {target_mac} para mensaje {original_msg_id}")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error enviando ACK: {e}")
            return False
    
    def get_received_messages(self, limit: int = 50) -> List[Message]:
        """
        Obtiene los mensajes recibidos más recientes
        
        Args:
            limit: Número máximo de mensajes a retornar
            
        Returns:
            List[Message]: Lista de mensajes recibidos
        """
        return self.message_queue[-limit:] if self.message_queue else []
    
    def get_sent_messages(self) -> Dict[int, Message]:
        """
        Obtiene los mensajes enviados
        
        Returns:
            Dict[int, Message]: Diccionario de mensajes enviados
        """
        return self.sent_messages.copy()
    
    def register_callback(self, name: str, callback: Callable) -> None:
        """
        Registra un callback para notificaciones de mensajes
        
        Args:
            name: Nombre del callback
            callback: Función a llamar cuando se reciba un mensaje
        """
        self.callbacks[name] = callback
    
    def unregister_callback(self, name: str) -> None:
        """
        Desregistra un callback
        
        Args:
            name: Nombre del callback a eliminar
        """
        if name in self.callbacks:
            del self.callbacks[name]
    
    def _handle_frame(self, frame: LinkChatFrame, addr) -> None:
        """
        Maneja tramas recibidas relacionadas con mensajería
        
        Args:
            frame: Trama Ethernet recibida
            addr: Dirección del remitente
        """
        try:
            # La trama ya está parseada como LinkChatFrame
            # Procesar según el tipo de mensaje
            if frame.msg_type == MSG_TYPE_MESSAGE:
                self._handle_text_message(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_BROADCAST:
                self._handle_broadcast_message(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_MESSAGE_ACK:
                self._handle_message_ack(frame.src_mac, frame)
                
        except Exception as e:
            log_message("ERROR", f"Error procesando trama de mensaje: {e}")
    
    def _handle_text_message(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja mensajes de texto recibidos
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            
            content = data.get("content", "")
            msg_id = data.get("msg_id", frame.msg_id)
            timestamp = data.get("timestamp", get_timestamp())
            
            # Verificar si ya recibimos este mensaje
            if msg_id in self.received_messages:
                log_message("DEBUG", f"Mensaje duplicado ignorado: {msg_id}")
                return
            
            # Crear objeto mensaje
            message = Message(msg_id, src_mac, content, timestamp, False)
            self.received_messages[msg_id] = message
            self.message_queue.append(message)
            
            # Mantener solo los últimos 1000 mensajes
            if len(self.message_queue) > 1000:
                old_msg = self.message_queue.pop(0)
                if old_msg.msg_id in self.received_messages:
                    del self.received_messages[old_msg.msg_id]
            
            log_message("INFO", f"Mensaje recibido de {src_mac}: {content[:50]}...")
            
            # Enviar ACK
            self.send_message_ack(src_mac, msg_id)
            
            # Notificar a callbacks
            self._notify_message_received(src_mac, content, message)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando mensaje de texto: {e}")
    
    def _handle_broadcast_message(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja mensajes broadcast recibidos
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            
            content = data.get("content", "")
            msg_id = data.get("msg_id", frame.msg_id)
            timestamp = data.get("timestamp", get_timestamp())
            
            # Verificar si ya recibimos este mensaje
            if msg_id in self.received_messages:
                log_message("DEBUG", f"Mensaje broadcast duplicado ignorado: {msg_id}")
                return
            
            # Crear objeto mensaje
            message = Message(msg_id, src_mac, content, timestamp, True)
            self.received_messages[msg_id] = message
            self.message_queue.append(message)
            
            # Mantener solo los últimos 1000 mensajes
            if len(self.message_queue) > 1000:
                old_msg = self.message_queue.pop(0)
                if old_msg.msg_id in self.received_messages:
                    del self.received_messages[old_msg.msg_id]
            
            log_message("INFO", f"Mensaje broadcast recibido de {src_mac}: {content[:50]}...")
            
            # No enviar ACK para mensajes broadcast
            
            # Notificar a callbacks
            self._notify_message_received(src_mac, content, message)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando mensaje broadcast: {e}")
    
    def _handle_message_ack(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja acknowledgments de mensajes
        
        Args:
            src_mac: MAC del remitente del ACK
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            original_msg_id = data.get("original_msg_id")
            
            if original_msg_id and original_msg_id in self.sent_messages:
                self.sent_messages[original_msg_id].acknowledged = True
                log_message("INFO", f"ACK recibido de {src_mac} para mensaje {original_msg_id}")
            
        except Exception as e:
            log_message("ERROR", f"Error procesando ACK: {e}")
    
    def _notify_message_received(self, sender_mac: str, content: str, message: Message) -> None:
        """
        Notifica a los callbacks sobre un mensaje recibido
        
        Args:
            sender_mac: MAC del remitente
            content: Contenido del mensaje
            message: Objeto mensaje completo
        """
        for callback in self.callbacks.values():
            try:
                callback(sender_mac, content, message)
            except Exception as e:
                log_message("ERROR", f"Error en callback de mensaje: {e}")
    
    def _ack_timeout_loop(self) -> None:
        """
        Hilo para manejar timeouts de ACK y reenvíos
        """
        log_message("INFO", "Hilo de timeout de ACK iniciado")
        
        while self.is_running:
            try:
                current_time = get_timestamp()
                
                # Revisar mensajes enviados sin ACK
                for msg_id, message in list(self.sent_messages.items()):
                    if not message.acknowledged and not message.is_broadcast:
                        # Verificar timeout (30 segundos)
                        if current_time - message.timestamp > 30000:
                            log_message("WARNING", f"Timeout de ACK para mensaje {msg_id}")
                            # Aquí se podría implementar reenvío automático
                
                time.sleep(5)  # Revisar cada 5 segundos
                
            except Exception as e:
                log_message("ERROR", f"Error en loop de timeout de ACK: {e}")
                time.sleep(5)
        
        log_message("INFO", "Hilo de timeout de ACK detenido")

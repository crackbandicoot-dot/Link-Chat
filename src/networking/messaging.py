import json
import threading
import time
from typing import Dict, List, Callable, Optional
from utils.constants import *
from utils.helpers import log_message, create_message_id, get_timestamp
from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import RawSocketManager
from ..DTOS.message import Message
from ..observer.observer import Observer
from ..observer.subject import Subject

class MessageManager(Observer[LinkChatFrame], Subject[Message]):
    """
    Maneja el envío y recepción de mensajes de texto
    
    Implementa el patrón Observer:
    - Como Observer: Observa al RawSocketManager para recibir frames
    - Como Subject: Es observado por la interfaz de usuario para notificar nuevos mensajes
    """
    
    def __init__(self, socket_manager: RawSocketManager):
        """
        Inicializa el gestor de mensajes
        
        Args:
            socket_manager: Manejador de raw sockets
        """
        self.socket_manager = socket_manager
        self.local_mac = socket_manager.get_local_mac()
        
        # Almacenamiento separado de mensajes enviados
        self.pending_messages = {}      # ID -> Message (esperando ACK)
        self.confirmed_messages = {}    # ID -> Message (ya confirmados)
        self.received_messages = {}     # ID -> Message
        self.message_queue = []         # Lista de mensajes recibidos ordenados
        
        # Observer pattern - como Subject
        self._observers: List[Observer[Message]] = []
        
        # Control de hilos
        self.is_running = False
        self.ack_timeout_thread = None
        
    def start(self) -> None:
        """Inicia el gestor de mensajes"""
        self.is_running = True
        
        # Registrarse como observer del socket manager
        self.socket_manager.attach(self)
           
        # Iniciar hilo para manejo de timeouts de ACK
        self.ack_timeout_thread = threading.Thread(target=self._ack_timeout_loop, daemon=True)
        self.ack_timeout_thread.start()
        
        log_message("INFO", "Gestor de mensajes iniciado")
    
    def stop(self) -> None:
        """Detiene el gestor de mensajes"""
        self.is_running = False
        
        # Desregistrarse del socket manager
        self.socket_manager.detach(self)
        
        if self.ack_timeout_thread and self.ack_timeout_thread.is_alive():
            self.ack_timeout_thread.join(timeout=2)
        
        log_message("INFO", "Gestor de mensajes detenido")
    
    def send_message(self, target_mac: str, content: str, is_broadcast: bool = False) -> bool:
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
                "timestamp": get_timestamp()
            }
            
            data_bytes = json.dumps(message_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                target_mac,
                self.local_mac,
                MSG_TYPE_BROADCAST if is_broadcast else MSG_TYPE_MESSAGE,
                msg_id,
                data_bytes
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                # Crear mensaje
                message = Message(
                    msg_id, self.local_mac, target_mac, 
                    content, get_timestamp(), is_broadcast
                )
                
                # Almacenar según el tipo
                if is_broadcast:
                    # Los broadcasts no necesitan ACK, van directo a confirmados
                    self.confirmed_messages[msg_id] = message
                else:
                    # Los mensajes directos van a pendientes hasta recibir ACK
                    self.pending_messages[msg_id] = message
                
                log_message("INFO", f"Mensaje enviado a {target_mac}: {content[:50]}...")
            else:
                log_message("ERROR", "Error enviando mensaje")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de mensaje: {e}")
            return False
    
    def resend_message(self, message: Message) -> bool:
        """
        Reenvía un mensaje que no ha recibido confirmación (ACK)
                
        Args:
            message: Objeto Message a reenviar (debe estar en pending_messages)
            
        Returns:
            bool: True si se reenvió correctamente, False en caso de error
            
        Notes:
            - Solo reenvía mensajes que están en pending_messages
            - Mantiene el mismo msg_id del mensaje original
            - Actualiza timestamp para evitar reenvíos continuos
            - Los broadcasts no se reenvían (van directo a confirmed)
        """
        try:
            # Validar que el mensaje esté pendiente
            if message.msg_id not in self.pending_messages:
                log_message("WARNING", f"Intento de reenvío de mensaje no pendiente: {message.msg_id}")
                return False
            
            # Validar que no sea broadcast (los broadcasts no se reenvían)
            if message.is_broadcast:
                log_message("WARNING", f"Intento de reenvío de mensaje broadcast: {message.msg_id}")
                return False
            
            # Crear datos del mensaje (mantener formato original)
            message_data = {
                "type": "text_message",
                "content": message.content,
                "timestamp": message.timestamp  # Mantener timestamp original del contenido
            }
            
            data_bytes = json.dumps(message_data).encode('utf-8')
            
            # Crear trama Link-Chat con el mismo msg_id
            frame = LinkChatFrame(
                message.target_mac,
                message.sender_mac,
                MSG_TYPE_MESSAGE,  # Los reenvíos siempre son mensajes directos
                message.msg_id,    # IMPORTANTE: Mantener el mismo ID
                data_bytes
            )

            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                # Actualizar timestamp del mensaje para control de timeouts
                message.timestamp = get_timestamp()
                
                # Incrementar contador de reenvíos si existe
                message.retry_count += 1

                log_message("INFO", f"Mensaje {message.msg_id} reenviado a {message.target_mac} "
                                  f"(intento #{message.retry_count})")
            else:
                log_message("ERROR", f"Error reenviando mensaje {message.msg_id}")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en reenvío de mensaje {message.msg_id}: {e}")
            return False
    
    
    def send_broadcast_message(self, content: str) -> bool:
        return self.send_message(BROADCAST_MAC, content, True)
    
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
    
    
    def attach(self, observer: Observer[Message]) -> None:
        """
        Registra un observer para recibir notificaciones de nuevos mensajes
        
        Args:
            observer: Observer que recibirá notificaciones de mensajes
        """
        if observer not in self._observers:
            self._observers.append(observer)
            log_message("DEBUG", f"Observer registrado en MessageManager: {type(observer).__name__}")
    
    def detach(self, observer: Observer[Message]) -> None:
        """
        Desregistra un observer
        
        Args:
            observer: Observer a desregistrar
        """
        if observer in self._observers:
            self._observers.remove(observer)
            log_message("DEBUG", f"Observer desregistrado de MessageManager: {type(observer).__name__}")
    
    def notify(self, message: Message) -> None:
        """
        Notifica a todos los observers registrados sobre un nuevo mensaje
        
        Args:
            message: Mensaje a notificar
        """
        for observer in self._observers:
            try:
                observer.update(message)
            except Exception as e:
                log_message("ERROR", f"Error notificando observer {type(observer).__name__}: {e}")
    
   
    def update(self, frame: LinkChatFrame) -> None:
        """
        Método del patrón Observer - recibe notificaciones del RawSocketManager
        
        Args:
            frame: Trama Ethernet recibida del socket manager
        """
        try:
            # Procesar solo frames relacionados con mensajería
            if frame.msg_type in [MSG_TYPE_MESSAGE, MSG_TYPE_BROADCAST, MSG_TYPE_MESSAGE_ACK]:
                self._handle_frame(frame)
                
        except Exception as e:
            log_message("ERROR", f"Error en update del MessageManager: {e}")
    
    def _handle_frame(self, frame: LinkChatFrame) -> None:
        """
        Maneja tramas recibidas relacionadas con mensajería
        
        Args:
            frame: Trama Ethernet recibida
        """
        try:
            # Procesar según el tipo de mensaje
            if frame.msg_type == MSG_TYPE_MESSAGE:
                self._handle_text_message(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_BROADCAST:
                self._handle_broadcast_message(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_MESSAGE_ACK:
                self._handle_message_ack(frame.src_mac, frame)
                
        except Exception as e:
            log_message("ERROR", f"Error procesando trama de mensaje: {e}")
    
    def _handle_text_message(self, src_mac: str, frame: LinkChatFrame, is_broadcast: bool = False) -> None:
        """
        Maneja mensajes de texto recibidos
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            
            content = data.get("content", "")
            timestamp = data.get("timestamp", get_timestamp())
            msg_id = frame.msg_id
            
            # Verificar si ya recibimos este mensaje
            if msg_id in self.received_messages:
                log_message("DEBUG", f"Mensaje duplicado ignorado: {msg_id}")
                return
            
            # Crear objeto mensaje
            message = Message(
            msg_id, 
            src_mac, 
            self.local_mac,  
            content, 
            timestamp, 
            is_broadcast
        )
            self.received_messages[msg_id] = message
            self.message_queue.append(message)
            
            # Mantener solo los últimos 1000 mensajes
            if len(self.message_queue) > 1000:
                old_msg = self.message_queue.pop(0)
                if old_msg.msg_id in self.received_messages:
                    del self.received_messages[old_msg.msg_id]
            
            log_message("INFO", f"Mensaje recibido de {src_mac}: {content[:50]}...")
            
            # Enviar ACK
            if not is_broadcast:
                self.send_message_ack(src_mac, msg_id)
            
            # Notificar a los observers (UI) sobre el nuevo mensaje
            self.notify(message)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando mensaje de texto: {e}")
    
    def _handle_broadcast_message(self, src_mac: str, frame: LinkChatFrame) -> None:
        self._handle_text_message(src_mac, frame, True)
        
        
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
            
            # Buscar mensaje en pendientes
            if original_msg_id and original_msg_id in self.pending_messages:
                # Mover de pendientes a confirmados
                message = self.pending_messages.pop(original_msg_id)
                message.acknowledged = True
                self.confirmed_messages[original_msg_id] = message
                
                log_message("INFO", f"ACK recibido de {src_mac} para mensaje {original_msg_id}")
                log_message("DEBUG", f"Mensaje {original_msg_id} confirmado y movido a storage")
            else:
                log_message("WARNING", f"ACK recibido para mensaje no encontrado: {original_msg_id}")
            
        except Exception as e:
            log_message("ERROR", f"Error procesando ACK: {e}")
    
   
    def _ack_timeout_loop(self) -> None:
        """
        Hilo para manejar timeouts de ACK y reenvíos automáticos
        """
        log_message("INFO", "Hilo de timeout de ACK iniciado")

        MAX_RETRIES = 3
        TIMEOUT_MS = 3000

        while self.is_running:
            try:
                current_time = get_timestamp()
                messages_to_retry = []  
                messages_to_fail = []

                #Hacer copia para evitar modificación durante iteración
                pending_copy = dict(self.pending_messages)

                for msg_id, message in pending_copy.items():
                    # Verificar que el mensaje aún esté pendiente
                    if msg_id not in self.pending_messages:
                        continue

                    time_elapsed = current_time - message.timestamp

                    if time_elapsed > TIMEOUT_MS: 
                        if message.retry_count < MAX_RETRIES:
                            messages_to_retry.append(message)
                        else:
                            messages_to_fail.append(message)
                            log_message("WARNING", 
                                      f"Mensaje {msg_id} falló después de {message.retry_count} intentos")

                # Procesar reenvíos
                for message in messages_to_retry:
                    if message.msg_id in self.pending_messages:  # Double check
                        if self.resend_message(message):
                            log_message("DEBUG", f"Mensaje {message.msg_id} reenviado automáticamente")

                # Procesar mensajes fallidos
                for message in messages_to_fail:
                    failed_msg = self.pending_messages.pop(message.msg_id, None)
                    if failed_msg:
                        log_message("ERROR", 
                                  f"Mensaje {message.msg_id} marcado como fallido definitivamente")

                time.sleep(2)  # Revisar cada 2 segundos

            except Exception as e:
                log_message("ERROR", f"Error en loop de timeout de ACK: {e}")
                time.sleep(5)

        log_message("INFO", "Hilo de timeout de ACK detenido")
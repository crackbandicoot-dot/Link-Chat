# Sistema de mensajería con arquitectura basada en cola y threading
import threading
import time
import uuid
from queue import Queue, Empty
from typing import Dict, Optional, Tuple

from ..observer.observer import Observer
from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import raw_socket_manager
from ..observer.subject import Subject
from ..utils.constants import MSG_TYPE_MESSAGE, MSG_TYPE_MESSAGE_ACK, MAX_RETRIES
from ..DTOS.message import Message


class PendingMessage:
    """Representa un mensaje pendiente de confirmación"""
    def __init__(self, frame: LinkChatFrame, max_retries: int = MAX_RETRIES):
        self.frame = frame
        self.max_retries = max_retries
        self.attempts = 0
        self.confirmed = False
        self.timestamp = time.time()
        self.last_send_time = 0.0


class MessageService(Observer[LinkChatFrame], Subject[Message]):
    """
    Servicio de mensajería robusto con:
    - Cola de mensajes para envío asíncrono
    - Thread dedicado para procesamiento de cola
    - Generación de IDs únicos para mensajes
    - Sistema de confirmación con reintentos
    - Implementación de patrones Observer y Subject
    """
    
    def __init__(self, socket_manager: raw_socket_manager):
        # Subject implementation
        self.observers = set()
        
        # Socket manager
        self.socket_manager = socket_manager
        
        # Queue and threading
        self.send_queue: Queue[Tuple[str, str]] = Queue()
        self.sending_thread: Optional[threading.Thread] = None
        self.running = False
        
        
        # Message tracking with unique IDs
        self.pending_messages: Dict[int, PendingMessage] = {}
        self.message_id_counter = 0
        
        # Configuration
        self.retry_interval = 0.5  # seconds between retries
        self.confirmation_timeout = 5.0  # seconds to wait for confirmation
    
    def _generate_message_id(self) -> int:
        """
        Genera un ID único para cada mensaje
        
        Returns:
            int: ID único del mensaje
        """
        
        self.message_id_counter += 1
        # Wrap around at 32-bit limit to fit in msg_id field
        if self.message_id_counter > 0xFFFFFFFF:
            self.message_id_counter = 1
        return self.message_id_counter
    
    def start(self) -> None:
        """
        Inicia el thread de envío de mensajes
        """
    
        if self.running:
            print("MessageService: Thread already running")
            return
        
        self.running = True
        self.sending_thread = threading.Thread(
            target=self._sending_worker,
            daemon=True,
            name="MessageSendingThread"
        )
        self.sending_thread.start()
        print("MessageService: Sending thread started")
    
    def stop(self) -> None:
        """
        Detiene el thread de envío de mensajes de forma segura
        """
        if not self.running:
            print("MessageService: Thread not running")
            return

        self.running = False

        # Signal thread to wake up and exit
        self.send_queue.put(("", ""))  # Sentinel value

        if self.sending_thread and self.sending_thread.is_alive():
            self.sending_thread.join(timeout=2.0)

        print("MessageService: Sending thread stopped")
    
    def _sending_worker(self) -> None:
        """
        Worker thread que procesa la cola de mensajes y maneja reintentos
        """
        print("MessageService: Worker thread started")
        
        while self.running:
            try:
                # Process new messages from queue (non-blocking with timeout)
                try:
                    target_mac, message_text = self.send_queue.get(timeout=0.1)
                    
                    # Check for sentinel value (stop signal)
                    if not target_mac and not message_text:
                        break
                    
                    # Create and send new message
                    self._create_and_send_message(target_mac, message_text)
                    
                except Empty:
                    pass  # No new messages, continue to retry logic
                
                # Process pending messages (retries)
                self._process_pending_messages()
                
                # Small sleep to prevent CPU spinning
                time.sleep(1)
                
            except Exception as e:
                print(f"MessageService: Error in sending worker: {e}")
        
        print("MessageService: Worker thread exiting")
    
    def _create_and_send_message(self, target_mac: str, message_text: str) -> None:
        """
        Crea un nuevo mensaje con ID único y lo envía
        
        Args:
            target_mac: MAC address del destinatario
            message_text: Texto del mensaje
        """
        # Generate unique message ID
        msg_id = self._generate_message_id()
        
        # Create frame
        message_bytes = message_text.encode('utf-8')
        frame = LinkChatFrame(
            target_mac,
            self.socket_manager.get_local_mac(),
            MSG_TYPE_MESSAGE,
            msg_id,
            message_bytes
        )
        
        # Track pending message
        
        self.pending_messages[msg_id] = PendingMessage(frame)
        
        # Send immediately
        self._send_frame(msg_id)
        print(f"MessageService: Created and sent message ID {msg_id} to {target_mac}")
    
    def _process_pending_messages(self) -> None:
        """
        Procesa mensajes pendientes de confirmación y maneja reintentos
        """
        current_time = time.time()
        messages_to_remove = []
        
    
        for msg_id, pending_msg in self.pending_messages.items():
            # Skip confirmed messages
            if pending_msg.confirmed:
                messages_to_remove.append(msg_id)
                continue
            
            # Check if message has timed out
            if current_time - pending_msg.timestamp > self.confirmation_timeout:
                if pending_msg.attempts >= pending_msg.max_retries:
                    print(f"MessageService: Message ID {msg_id} failed after {pending_msg.attempts} attempts")
                    messages_to_remove.append(msg_id)
                    continue
                
                # Retry if enough time has passed since last send
                if current_time - pending_msg.last_send_time >= self.retry_interval:
                    self._send_frame(msg_id)
    
        # Clean up completed/failed messages
    
        for msg_id in messages_to_remove:
            del self.pending_messages[msg_id]
    
    def _send_frame(self, msg_id: int) -> None:
        """
        Envía un frame y actualiza el tracking
        
        Args:
            msg_id: ID del mensaje a enviar
        """
        
        if msg_id not in self.pending_messages:
            return
        
        pending_msg = self.pending_messages[msg_id]
        pending_msg.attempts += 1
        pending_msg.last_send_time = time.time()
        
        try:
            self.socket_manager.send_frame(pending_msg.frame)
            print(f"MessageService: Sent message ID {msg_id} (attempt {pending_msg.attempts})")
        except Exception as e:
            print(f"MessageService: Error sending message ID {msg_id}: {e}")
    
    def send_message(self, target_mac: str, message: str) -> bool:
        """
        Envía un mensaje de forma síncrona (no async) agregándolo a la cola
        
        Args:
            target_mac: MAC address del destinatario
            message: Texto del mensaje a enviar
            
        Returns:
            bool: True si el mensaje fue agregado a la cola exitosamente
        """
        if not self.running:
            print("MessageService: Cannot send message - service not started")
            return False
        
        try:
            self.send_queue.put((target_mac, message))
            print(f"MessageService: Message queued for {target_mac}")
            return True
        except Exception as e:
            print(f"MessageService: Error queuing message: {e}")
            return False
    
    # Observer implementation
    def update(self, data: LinkChatFrame) -> None:
        """
        Maneja frames recibidos (mensajes y confirmaciones)
        
        Args:
            data: Frame recibido
        """
        if data.msg_type == MSG_TYPE_MESSAGE:
            # Received a message - send ACK and notify observers
            message_text = data.data.decode('utf-8')
            message = Message(message_text, data.src_mac)
            
            print(f"MessageService: Received message from {data.src_mac}")
            
            # Send acknowledgment
            ack_frame = LinkChatFrame(
                data.src_mac,
                self.socket_manager.get_local_mac(),
                MSG_TYPE_MESSAGE_ACK,
                data.msg_id,  # Use same message ID for ACK
                b''
            )
            self.socket_manager.send_frame(ack_frame)
            
            # Notify observers
            self.notify(message)
        
        elif data.msg_type == MSG_TYPE_MESSAGE_ACK:
            # Received acknowledgment - mark message as confirmed
            msg_id = data.msg_id
            
            with self.message_lock:
                if msg_id in self.pending_messages:
                    self.pending_messages[msg_id].confirmed = True
                    print(f"MessageService: Message ID {msg_id} confirmed by {data.src_mac}")
    
    # Subject implementation
    def attach(self, observer: Observer[Message]) -> None:
        """
        Registra un observer para recibir notificaciones de mensajes
        
        Args:
            observer: Observer a registrar
        """
        self.observers.add(observer)
    
    def detach(self, observer: Observer[Message]) -> None:
        """
        Remueve un observer
        
        Args:
            observer: Observer a remover
        """
        self.observers.discard(observer)
    
    def notify(self, notification: Message) -> None:
        """
        Notifica a todos los observers sobre un nuevo mensaje
        
        Args:
            notification: Mensaje recibido
        """
        for observer in self.observers:
            try:
                observer.update(notification)
            except Exception as e:
                print(f"MessageService: Error notifying observer: {e}")
    
    def get_pending_count(self) -> int:
        """
        Obtiene el número de mensajes pendientes de confirmación
        
        Returns:
            int: Número de mensajes pendientes
        """
        
        return len(self.pending_messages)
    
    def is_running(self) -> bool:
        """
        Verifica si el servicio está activo
        
        Returns:
            bool: True si el thread de envío está activo
        """
        return self.running

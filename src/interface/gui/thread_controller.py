"""
Thread-Safe Controller para conectar Observer pattern con Tkinter
Maneja la comunicación entre threads de red y el thread principal de Tkinter
"""
import queue
import threading
from typing import Callable, Any, Dict
from src.observer.observer import Observer
from src.DTOS.message import Message
from src.DTOS.file_info import FileInfo


class ThreadSafeController:
    """
    Controlador thread-safe que actúa como puente entre:
    - Los servicios de red (threads secundarios)
    - La interfaz Tkinter (thread principal)
    
    Usa Queue para comunicación segura entre threads
    """
    
    def __init__(self):
        """Inicializa el controlador con colas para cada tipo de evento"""
        self.device_queue = queue.Queue()
        self.message_queue = queue.Queue()
        self.file_queue = queue.Queue()
        self.event_callbacks = {
            'device': [],
            'message': [],
            'file': []
        }
        self._lock = threading.Lock()
    
    def register_callback(self, event_type: str, callback: Callable[[Any], None]):
        """
        Registra un callback para un tipo de evento
        
        Args:
            event_type: 'device', 'message', o 'file'
            callback: Función a llamar cuando ocurra el evento
        """
        with self._lock:
            if event_type in self.event_callbacks:
                self.event_callbacks[event_type].append(callback)
    
    def update(self, data: Any) -> None:
        """
        Implementación del patrón Observer
        Clasifica los datos y los pone en la cola correspondiente
        
        Args:
            data: Puede ser Dict (dispositivos), Message o File
        """
        if isinstance(data, dict) and 'mac' in data:
            # Evento de dispositivo
            self.device_queue.put(data)
        elif isinstance(data, Message):
            # Evento de mensaje
            self.message_queue.put(data)
        elif isinstance(data, FileInfo):
            # Evento de archivo
            self.file_queue.put(data)
    
    def process_queues(self, root):
        """
        Procesa todas las colas y dispara callbacks
        Debe ser llamado periódicamente desde el thread principal de Tkinter
        
        Args:
            root: Ventana raíz de Tkinter para programar siguiente llamada
        """
        # Procesar dispositivos
        try:
            while True:
                device_data = self.device_queue.get_nowait()
                with self._lock:
                    for callback in self.event_callbacks['device']:
                        callback(device_data)
        except queue.Empty:
            pass
        
        # Procesar mensajes
        try:
            while True:
                message = self.message_queue.get_nowait()
                with self._lock:
                    for callback in self.event_callbacks['message']:
                        callback(message)
        except queue.Empty:
            pass
        
        # Procesar archivos
        try:
            while True:
                file_data = self.file_queue.get_nowait()
                with self._lock:
                    for callback in self.event_callbacks['file']:
                        callback(file_data)
        except queue.Empty:
            pass
        
        # Programar siguiente procesamiento
        root.after(100, lambda: self.process_queues(root))

import hashlib
import os  
from typing import Dict, List, Callable, Optional, BinaryIO
from ..utils.helpers import log_message, get_timestamp  
from ..utils.constants import MAX_CHUNK_SIZE 


class FileTransfer:
    """Representa una transferencia de archivo en progreso"""
    
    def __init__(self, transfer_id: str, file_path: str, target_mac: str, 
                 is_sender: bool = True):
        
        self.transfer_id = transfer_id
        self.file_path = file_path
        self.target_mac = target_mac
        self.is_sender = is_sender
        
        # Información del archivo
        self.filename = os.path.basename(file_path)
        self.file_size = 0
        self.file_hash = ""
        
        # Estado de la transferencia
        self.status = "pending"  # pending, active, completed, failed, cancelled
        self.chunks_sent = 0
        self.chunks_received = 0
        self.total_chunks = 0
        self.bytes_transferred = 0
        self.start_time = get_timestamp()
        self.last_activity = get_timestamp()
        
        # Control de chunks
        self.chunks_data = {}  # chunk_number -> data
        self.chunks_acked = set()
        self.missing_chunks = set()
        
        # Archivo temporal para recepción
        self.temp_file_path = None
        
        if is_sender and os.path.exists(file_path):
            self.file_size = os.path.getsize(file_path)
            self.total_chunks = (self.file_size + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE
            # Calcular hash del archivo
            self._calculate_file_hash()


    def _calculate_file_hash(self):
        """Calcula el hash MD5 del archivo completo"""
        try:
            with open(self.file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                self.file_hash = file_hash.hexdigest()
        except Exception as e:
            log_message("ERROR", f"Error calculando hash: {e}")
            self.file_hash = ""

    def is_complete(self) -> bool:
        """Verifica si la transferencia está completa"""
        if self.is_sender:
            return len(self.chunks_acked) == self.total_chunks
        else:
            return self.chunks_received == self.total_chunks


import os
import json
import threading
import time
import hashlib
from typing import Dict, List, Callable, Optional, BinaryIO
from ..utils.constants import *  
from ..utils.helpers import (log_message, create_message_id, get_timestamp, format_file_size)
from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import raw_socket_manager
from ..core.file_transfer import FileTransfer  
from ..observer.observer import Observer
from ..observer.subject import Subject


class FileTransferManager(Subject[FileTransfer], Observer[LinkChatFrame]):
    """
    Maneja la transferencia de archivos entre dispositivos
    """
    
    def __init__(self, socket_manager: raw_socket_manager):
        super().__init__()
        """
        Inicializa el gestor de transferencia de archivos
        
        Args:
            socket_manager: Manejador de raw sockets
        """
        self.socket_manager = socket_manager
        self.local_mac = socket_manager.get_local_mac()
        
        # Transferencias activas
        self.active_transfers = {}  # transfer_id -> FileTransfer
        self.completed_transfers = {}  # transfer_id -> FileTransfer 
        # Control de hilos
        self.is_running = False
        self.transfer_thread = None
        
        socket_manager.attach(self)
        self.observers = set()
        # Directorio de recepción
        self.download_dir = os.path.join(os.getcwd(), "Downloads")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
         
    def start(self) -> None:
        """Inicia el gestor de transferencia de archivos"""
        self.is_running = True
        
        # Iniciar hilo para manejo de transferencias
        self.transfer_thread = threading.Thread(target=self._transfer_management_loop, daemon=True)
        self.transfer_thread.start()
        
        log_message("INFO", "Gestor de transferencia de archivos iniciado")
    
    def stop(self) -> None:
        """Detiene el gestor de transferencia de archivos"""
        self.is_running = False
        
        if self.transfer_thread and self.transfer_thread.is_alive():
            self.transfer_thread.join(timeout=2)
          
        log_message("INFO", "Gestor de transferencia de archivos detenido")
    
    def send_file(self, target_mac: str, file_path: str) -> bool:
        """
        Inicia el envío de un archivo a un dispositivo
        
        Args:
            target_mac: MAC del dispositivo destino
            file_path: Ruta del archivo a enviar
            
        Returns:
            bool: True si se inició la transferencia correctamente
        """
        try:
            # Validar archivo
            if not os.path.exists(file_path):
                log_message("ERROR", f"Archivo no encontrado: {file_path}")
                return False
            
            if not os.path.isfile(file_path):
                log_message("ERROR", f"La ruta no es un archivo: {file_path}")
                return False
            
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                log_message("ERROR", "No se pueden enviar archivos vacíos")
                return False
            
            # Crear ID único para la transferencia
            transfer_id = f"{self.local_mac}_{target_mac}_{get_timestamp()}"
            
            # Crear objeto de transferencia
            transfer = FileTransfer(transfer_id, file_path, target_mac, True)
            self.active_transfers[transfer_id] = transfer
            
            # Enviar solicitud de inicio de transferencia
            success = self._send_file_start(transfer)
            
            if success:
                transfer.status = "active"
                log_message("INFO", f"Transferencia iniciada: {filename} -> {target_mac}")
            else:
                del self.active_transfers[transfer_id]
                log_message("ERROR", f"Error iniciando transferencia de {filename}")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de archivo: {e}")
            return False
    
    
    def _send_file_start(self, transfer: FileTransfer) -> bool:
        """
        Envía la solicitud de inicio de transferencia de archivo
        
        Args:
            transfer: Objeto de transferencia
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear datos de inicio
            start_data = {
                "type": "file_start",
                "transfer_id": transfer.transfer_id,
                "filename": transfer.filename,
                "file_size": transfer.file_size,
                "file_hash": transfer.file_hash,
                "total_chunks": transfer.total_chunks,
                "chunk_size": MAX_CHUNK_SIZE,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac
            }
            
            data_bytes = json.dumps(start_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                transfer.target_mac,
                self.local_mac,
                MSG_TYPE_FILE_START,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            return self.socket_manager.send_frame(frame)
            
        except Exception as e:
            log_message("ERROR", f"Error enviando inicio de archivo: {e}")
            return False
    
    def _send_file_chunk(self, transfer: FileTransfer, chunk_number: int) -> bool:
        """
        Envía un fragmento de archivo
        
        Args:
            transfer: Objeto de transferencia
            chunk_number: Número del fragmento
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Leer fragmento del archivo
            chunk_start = chunk_number * MAX_CHUNK_SIZE
            chunk_end = min(chunk_start + MAX_CHUNK_SIZE, transfer.file_size)
            chunk_size = chunk_end - chunk_start
            
            with open(transfer.file_path, 'rb') as f:
                f.seek(chunk_start)
                chunk_data = f.read(chunk_size)
            
            # Crear datos del fragmento
            chunk_info = {
                "type": "file_chunk",
                "transfer_id": transfer.transfer_id,
                "chunk_number": chunk_number,
                "chunk_size": chunk_size,
                "total_chunks": transfer.total_chunks,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac
            }
            
            # Combinar información y datos
            info_bytes = json.dumps(chunk_info).encode('utf-8')
            info_length = len(info_bytes)
            
            # Formato: [info_length:4][info][data]
            payload = (info_length.to_bytes(4, 'big') + 
                      info_bytes + chunk_data)
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                transfer.target_mac,
                self.local_mac,
                MSG_TYPE_FILE_CHUNK,
                create_message_id(),
                payload
            )
            
            # Enviar trama
            success = self.socket_manager.send_frame(frame)
            
            if success:
                transfer.chunks_sent += 1
                transfer.bytes_transferred += chunk_size
                transfer.last_activity = get_timestamp()
                
                # log_message("DEBUG", f"Fragmento {chunk_number}/{transfer.total_chunks} enviado")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error enviando fragmento: {e}")
            return False
    
    def _send_file_chunk_ack(self, target_mac: str, transfer_id: str, chunk_number: int) -> bool:
        """
        Envía acknowledgment de fragmento de archivo
        
        Args:
            target_mac: MAC del dispositivo remitente
            transfer_id: ID de la transferencia
            chunk_number: Número del fragmento confirmado
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear datos del ACK
            ack_data = {
                "type": "file_chunk_ack",
                "transfer_id": transfer_id,
                "chunk_number": chunk_number,
                "timestamp": get_timestamp(),
                "sender_mac": self.local_mac
            }
            
            data_bytes = json.dumps(ack_data).encode('utf-8')
            
            # Crear trama Link-Chat completa
            frame = LinkChatFrame(
                target_mac,
                self.local_mac,
                MSG_TYPE_FILE_CHUNK_ACK,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            return self.socket_manager.send_frame(frame)
            
        except Exception as e:
            log_message("ERROR", f"Error enviando ACK de archivo: {e}")
            return False
    
    def _handle_frame(self, frame: LinkChatFrame) -> None:
        """
        Maneja tramas recibidas relacionadas con transferencia de archivos
        
        Args:
            frame: Trama Ethernet recibida
            addr: Dirección del remitente
        """
        try:
            # Ignorar tramas propias
            if frame.src_mac == self.local_mac:
                return
            # Procesar según el tipo de mensaje
            if frame.msg_type == MSG_TYPE_FILE_START:
                self._handle_file_start(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_FILE_CHUNK:
                self._handle_file_chunk(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_FILE_CHUNK_ACK:
                self._handle_file_chunk_ack(frame.src_mac, frame)
        except Exception as e:
            log_message("ERROR", f"Error procesando trama de archivo: {e}")
    
    def _handle_file_start(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja solicitudes de inicio de transferencia de archivo
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            
            transfer_id = data.get("transfer_id")
            filename = data.get("filename")
            file_size = data.get("file_size")
            file_hash = data.get("file_hash")
            total_chunks = data.get("total_chunks")
            
            log_message("INFO", f"Solicitud de archivo de {src_mac}: {filename} ({format_file_size(file_size)})")
            
            # Crear ruta de archivo temporal
            temp_path = os.path.join(self.download_dir, f"temp_{transfer_id}_{filename}")
            final_path = os.path.join(self.download_dir, filename)
            
            # Crear objeto de transferencia para recepción
            transfer = FileTransfer(transfer_id, final_path, src_mac, False)
            transfer.filename = filename
            transfer.file_size = file_size
            transfer.file_hash = file_hash
            transfer.total_chunks = total_chunks
            transfer.temp_file_path = temp_path
            transfer.status = "active"
            
            self.active_transfers[transfer_id] = transfer
            
            log_message("INFO", f"Transferencia de archivo aceptada: {filename}")
            
            
        except Exception as e:
            log_message("ERROR", f"Error procesando inicio de archivo: {e}")
    
    def _handle_file_chunk(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja fragmentos de archivo recibidos
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            # Extraer información y datos del fragmento
            payload = frame.data
            info_length = int.from_bytes(payload[:4], 'big')
            info_bytes = payload[4:4+info_length]
            chunk_data = payload[4+info_length:]
            
            info = json.loads(info_bytes.decode('utf-8'))
            
            transfer_id = info.get("transfer_id")
            chunk_number = info.get("chunk_number")
            chunk_size = info.get("chunk_size")
            
            if transfer_id not in self.active_transfers:
                log_message("WARNING", f"Fragmento recibido para transferencia desconocida: {transfer_id}")
                return
            
            transfer = self.active_transfers[transfer_id]
            
            # Guardar fragmento
            transfer.chunks_data[chunk_number] = chunk_data
            transfer.chunks_received += 1
            transfer.bytes_transferred += chunk_size
            transfer.last_activity = get_timestamp()
            
            # log_message("DEBUG", f"Fragmento {chunk_number}/{transfer.total_chunks} recibido")
            
            # Enviar ACK
            self._send_file_chunk_ack(src_mac, transfer_id, chunk_number)
            
            # Verificar si está completo
            if transfer.is_complete():
                self._complete_file_transfer(transfer)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando fragmento de archivo: {e}")
    
    def _handle_file_chunk_ack(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja acknowledgments de fragmentos de archivo
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        try:
            data = json.loads(frame.data.decode('utf-8'))
            
            transfer_id = data.get("transfer_id")
            chunk_number = data.get("chunk_number")
            
            if transfer_id not in self.active_transfers:
                return
            
            transfer = self.active_transfers[transfer_id]
            transfer.chunks_acked.add(chunk_number)
            transfer.last_activity = get_timestamp()
            
            # log_message("DEBUG", f"ACK recibido para fragmento {chunk_number}")
            
            # Verificar si está completo
            if transfer.is_complete():
                self._complete_file_transfer(transfer)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando ACK de archivo: {e}")  
    
    def _complete_file_transfer(self, transfer: FileTransfer) -> None:
        """
        Completa una transferencia de archivo
        
        Args:
            transfer: Objeto de transferencia
        """
        try:
            if not transfer.is_sender:
                # Ensamblar archivo desde fragmentos
                
                with open(transfer.temp_file_path, 'wb') as f:
                    for chunk_num in range(transfer.total_chunks):
                        if chunk_num in transfer.chunks_data:
                            f.write(transfer.chunks_data[chunk_num])
                
                # Verificar integridad
                if transfer.file_hash:
                    with open(transfer.temp_file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if file_hash == transfer.file_hash:
                        # Mover archivo a ubicación final
                        os.rename(transfer.temp_file_path, transfer.file_path)
                        transfer.status = "completed"
                        log_message("INFO", f"Archivo recibido correctamente: {transfer.filename}")
                    else:
                        transfer.status = "failed"
                        log_message("ERROR", f"Error de integridad en archivo: {transfer.filename}")
                else:
                    # Sin verificación de hash
                    os.rename(transfer.temp_file_path, transfer.file_path)
                    transfer.status = "completed"
                    log_message("INFO", f"Archivo recibido: {transfer.filename}")
            else:
                transfer.status = "completed"
                log_message("INFO", f"Archivo enviado completamente: {transfer.filename}")
            
            # Mover a completadas
            self.completed_transfers[transfer.transfer_id] = transfer
            del self.active_transfers[transfer.transfer_id]
            
            self.notify(transfer)
            
        except Exception as e:
            log_message("ERROR", f"Error completando transferencia: {e}")
            transfer.status = "failed"
            self.completed_transfers[transfer.transfer_id] = transfer
            del self.active_transfers[transfer.transfer_id]
            self._notify_transfer_completed(transfer)
    
    def _transfer_management_loop(self) -> None:
        """
        Hilo principal para gestión de transferencias
        """
        log_message("INFO", "Hilo de gestión de transferencias iniciado")
        
        while self.is_running:
            try:
                current_time = get_timestamp()
                
                # Procesar transferencias activas
                for transfer_id, transfer in list(self.active_transfers.items()):
                    # Verificar timeout
                    if current_time - transfer.last_activity > FILE_TIMEOUT * 1000:
                        log_message("WARNING", f"Timeout en transferencia: {transfer.filename}")
                        transfer.status = "failed"
                        self.completed_transfers[transfer_id] = transfer
                        del self.active_transfers[transfer_id]
                        self.notify(transfer)
                        continue
                    
                    # Enviar fragmentos pendientes para transferencias de envío
                    if transfer.is_sender and transfer.status == "active":
                        self._process_sender_transfer(transfer)
                
                time.sleep(0.5)  # Revisar cada segundo
                
            except Exception as e:
                log_message("ERROR", f"Error en loop de gestión de transferencias: {e}")
                time.sleep(1)
        
        log_message("INFO", "Hilo de gestión de transferencias detenido")
    
    def _process_sender_transfer(self, transfer: FileTransfer) -> None:
        """
        Procesa una transferencia de envío
        
        Args:
            transfer: Objeto de transferencia
        """
        # Enviar fragmentos no confirmados
        for chunk_num in range(transfer.total_chunks):
            if chunk_num not in transfer.chunks_acked:
                # Limitar número de fragmentos no confirmados simultáneos
                unacked_chunks = transfer.chunks_sent - len(transfer.chunks_acked)
                if unacked_chunks < 10:  # Máximo 10 fragmentos sin ACK
                    self._send_file_chunk(transfer, chunk_num)
                    

    def update(self, frame: LinkChatFrame) -> None:
        self._handle_frame(frame)    
    def attach(self, observer: Observer[FileTransfer]) -> None:
        """Registra un observer"""
        if observer not in self.observers:
            self.observers.add(observer)

    def detach(self, observer: Observer[FileTransfer]) -> None:
        """Desregistra un observer"""
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self, notification: FileTransfer) -> None:
        """Notifica a todos los observers"""
        for observer in self.observers:
            try:
                observer.update(notification)
            except Exception as e:
                log_message("ERROR", f"Error notificando observer: {e}")

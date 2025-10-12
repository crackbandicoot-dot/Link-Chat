"""
Sistema de transferencia de archivos para Link-Chat
"""

import os
import json
import threading
import time
import hashlib
from typing import Dict, List, Callable, Optional, BinaryIO
from utils.constants import *
from utils.helpers import (log_message, create_message_id, get_timestamp, 
                         calculate_checksum, format_file_size, safe_file_write, 
                         safe_file_read, validate_filename)
from core.unified_frame import LinkChatFrame
from core.raw_socket import RawSocketManager


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

    def get_progress_percentage(self) -> float:
        """Obtiene el porcentaje de progreso de la transferencia"""
        if self.total_chunks == 0:
            return 0.0
        
        if self.is_sender:
            completed_chunks = len(self.chunks_acked)
        else:
            completed_chunks = self.chunks_received
        
        return (completed_chunks / self.total_chunks) * 100.0

    def get_transfer_speed(self) -> float:
        """Obtiene la velocidad de transferencia en bytes/segundo"""
        elapsed_time = (get_timestamp() - self.start_time) / 1000.0  # Convertir a segundos
        if elapsed_time <= 0:
            return 0.0
        
        return self.bytes_transferred / elapsed_time

    def is_complete(self) -> bool:
        """Verifica si la transferencia está completa"""
        if self.is_sender:
            return len(self.chunks_acked) == self.total_chunks
        else:
            return self.chunks_received == self.total_chunks


class FileTransferManager:
    """
    Maneja la transferencia de archivos entre dispositivos
    """
    
    def __init__(self, socket_manager: RawSocketManager):
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
        
        # Callbacks para notificaciones
        self.callbacks = {}
        
        # Control de hilos
        self.is_running = False
        self.transfer_thread = None
        
        # Directorio de recepción
        self.download_dir = os.path.join(os.getcwd(), "received_files")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        # Registrar callback en el socket manager
        socket_manager.register_callback("file_transfer", self._handle_frame)
    
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
        
        # Desregistrar callback
        self.socket_manager.unregister_callback("file_transfer")
        
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
            if not validate_filename(filename):
                log_message("ERROR", f"Nombre de archivo inválido: {filename}")
                return False
            
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
                self._notify_transfer_started(transfer)
            else:
                del self.active_transfers[transfer_id]
                log_message("ERROR", f"Error iniciando transferencia de {filename}")
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error en envío de archivo: {e}")
            return False
    
    def get_active_transfers(self) -> Dict[str, FileTransfer]:
        """
        Obtiene las transferencias activas
        
        Returns:
            Dict[str, FileTransfer]: Diccionario de transferencias activas
        """
        return self.active_transfers.copy()
    
    def get_completed_transfers(self) -> Dict[str, FileTransfer]:
        """
        Obtiene las transferencias completadas
        
        Returns:
            Dict[str, FileTransfer]: Diccionario de transferencias completadas
        """
        return self.completed_transfers.copy()
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        """
        Cancela una transferencia activa
        
        Args:
            transfer_id: ID de la transferencia a cancelar
            
        Returns:
            bool: True si se canceló correctamente
        """
        if transfer_id in self.active_transfers:
            transfer = self.active_transfers[transfer_id]
            transfer.status = "cancelled"
            
            # Mover a completadas
            self.completed_transfers[transfer_id] = transfer
            del self.active_transfers[transfer_id]
            
            log_message("INFO", f"Transferencia cancelada: {transfer.filename}")
            self._notify_transfer_completed(transfer)
            
            return True
        
        return False
    
    def register_callback(self, name: str, callback: Callable) -> None:
        """
        Registra un callback para notificaciones de transferencia
        
        Args:
            name: Nombre del callback
            callback: Función a llamar para notificaciones
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
                
                log_message("DEBUG", f"Fragmento {chunk_number}/{transfer.total_chunks} enviado")
                self._notify_transfer_progress(transfer)
            
            return success
            
        except Exception as e:
            log_message("ERROR", f"Error enviando fragmento: {e}")
            return False
    
    def _send_file_ack(self, target_mac: str, transfer_id: str, chunk_number: int) -> bool:
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
                MSG_TYPE_FILE_ACK,
                create_message_id(),
                data_bytes
            )
            
            # Enviar trama
            return self.socket_manager.send_frame(frame)
            
        except Exception as e:
            log_message("ERROR", f"Error enviando ACK de archivo: {e}")
            return False
    
    def _handle_frame(self, frame: LinkChatFrame, addr) -> None:
        """
        Maneja tramas recibidas relacionadas con transferencia de archivos
        
        Args:
            frame: Trama Ethernet recibida
            addr: Dirección del remitente
        """
        try:
            # La trama ya está parseada como LinkChatFrame
            # Procesar según el tipo de mensaje
            if frame.msg_type == MSG_TYPE_FILE_START:
                self._handle_file_start(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_FILE_CHUNK:
                self._handle_file_chunk(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_FILE_ACK:
                self._handle_file_ack(frame.src_mac, frame)
            elif frame.msg_type == MSG_TYPE_FILE_END:
                self._handle_file_end(frame.src_mac, frame)
                
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
            safe_filename = "".join(c for c in filename if c.isalnum() or c in '._-')
            temp_path = os.path.join(self.download_dir, f"temp_{transfer_id}_{safe_filename}")
            final_path = os.path.join(self.download_dir, safe_filename)
            
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
            self._notify_transfer_started(transfer)
            
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
            
            log_message("DEBUG", f"Fragmento {chunk_number}/{transfer.total_chunks} recibido")
            
            # Enviar ACK
            self._send_file_ack(src_mac, transfer_id, chunk_number)
            
            # Verificar si está completo
            if transfer.is_complete():
                self._complete_file_transfer(transfer)
            
            self._notify_transfer_progress(transfer)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando fragmento de archivo: {e}")
    
    def _handle_file_ack(self, src_mac: str, frame: LinkChatFrame) -> None:
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
            
            log_message("DEBUG", f"ACK recibido para fragmento {chunk_number}")
            
            # Verificar si está completo
            if transfer.is_complete():
                self._complete_file_transfer(transfer)
            
            self._notify_transfer_progress(transfer)
            
        except Exception as e:
            log_message("ERROR", f"Error procesando ACK de archivo: {e}")
    
    def _handle_file_end(self, src_mac: str, frame: LinkChatFrame) -> None:
        """
        Maneja finalizaciones de transferencia de archivo
        
        Args:
            src_mac: MAC del remitente
            frame: Trama Link-Chat recibida
        """
        # Implementar si es necesario
        pass
    
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
            
            self._notify_transfer_completed(transfer)
            
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
                        self._notify_transfer_completed(transfer)
                        continue
                    
                    # Enviar fragmentos pendientes para transferencias de envío
                    if transfer.is_sender and transfer.status == "active":
                        self._process_sender_transfer(transfer)
                
                time.sleep(1)  # Revisar cada segundo
                
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
                    if self._send_file_chunk(transfer, chunk_num):
                        time.sleep(0.01)  # Pequeña pausa entre fragmentos
                    break
    
    def _notify_transfer_started(self, transfer: FileTransfer) -> None:
        """Notifica el inicio de una transferencia"""
        for callback in self.callbacks.values():
            try:
                callback("started", transfer.transfer_id, {
                    "transfer": transfer,
                    "filename": transfer.filename,
                    "file_size": transfer.file_size,
                    "is_sender": transfer.is_sender
                })
            except Exception as e:
                log_message("ERROR", f"Error en callback de transferencia: {e}")
    
    def _notify_transfer_progress(self, transfer: FileTransfer) -> None:
        """Notifica el progreso de una transferencia"""
        for callback in self.callbacks.values():
            try:
                callback("progress", transfer.transfer_id, {
                    "transfer": transfer,
                    "progress": transfer.get_progress_percentage(),
                    "speed": transfer.get_transfer_speed(),
                    "bytes_transferred": transfer.bytes_transferred
                })
            except Exception as e:
                log_message("ERROR", f"Error en callback de progreso: {e}")
    
    def _notify_transfer_completed(self, transfer: FileTransfer) -> None:
        """Notifica la finalización de una transferencia"""
        for callback in self.callbacks.values():
            try:
                callback("completed", transfer.transfer_id, {
                    "transfer": transfer,
                    "status": transfer.status,
                    "filename": transfer.filename,
                    "file_size": transfer.file_size
                })
            except Exception as e:
                log_message("ERROR", f"Error en callback de finalización: {e}")

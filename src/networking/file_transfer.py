# Transferencia de archivos
import pathlib
import threading
import queue
import time
from typing import Dict, List
from pathlib import Path
from ..observer.observer import Observer, T
from ..observer.subject import Subject
from ..core.raw_socket_manager import raw_socket_manager
from  ..core.frame import LinkChatFrame
from ..DTOS.file import File
from ..utils.constants import MAX_CHUNK_SIZE,MSG_TYPE_FILE_START,MSG_TYPE_FILE_CHUNK,MSG_TYPE_FILE_END,MSG_TYPE_MESSAGE_ACK,DOWNLOADS_PATH
from  ..utils.binary_serializer import BinarySerializer


class FileTransferService(Subject[File],Observer[LinkChatFrame]):
    def __init__(self, socket_manager: raw_socket_manager):
        self.observers = set()
        self.socket_manager = socket_manager
        
        # Thread management
        self._send_thread = None
        self._running = False
        self._send_queue = queue.Queue()
        
        # Receiving state - support multiple concurrent file transfers
        self._receiving_files: Dict[str, Dict] = {}  # key: file_id (src_mac + file_name)
        


    def start(self):
        """Start the file transfer service thread"""
        if self._running:
            return
        
        self._running = True
        self._send_thread = threading.Thread(target=self._send_worker, daemon=True)
        self._send_thread.start()
    
    def stop(self):
        """Stop the file transfer service thread"""
        if not self._running:
            return
        
        self._running = False
        # Signal thread to stop by adding None to queue
        self._send_queue.put(None)
        
        if self._send_thread:
            self._send_thread.join(timeout=5.0)
            self._send_thread = None
    
    def _send_worker(self):
        """Worker thread for sending files"""
        while self._running:
            try:
                # Get next file transfer task from queue
                task = self._send_queue.get(timeout=1.0)
                
                if task is None:  # Stop signal
                    break
                
                target_mac, file_path = task
                self._send_file_internal(target_mac, file_path)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in send worker: {e}")
    
    def _send_file_internal(self, target_mac: str, file_path: str):
        """Internal method to send a file with acknowledgment handling"""
        confirmed_frame = False
        
        def wait_for_ack(timeout=5.0):
            nonlocal confirmed_frame
            start_time = time.time()
            while not confirmed_frame and (time.time() - start_time) < timeout:
                time.sleep(0.01)
            result = confirmed_frame
            confirmed_frame = False
            return result
        
        # Temporary observer for ACKs
        def ack_handler(frame: LinkChatFrame):
            nonlocal confirmed_frame
            if frame.msg_type == MSG_TYPE_MESSAGE_ACK:
                confirmed_frame = True
        
        # Send file start frame
        file_name = Path(file_path).name
        file_info = File(file_name)
        serialized_info = BinarySerializer.serialize(file_info)
        
        # Send start frame with retries
        for _ in range(3):
            self.socket_manager.send_frame(
                LinkChatFrame(target_mac, self.socket_manager.get_local_mac(),
                            MSG_TYPE_FILE_START, 0, serialized_info)
            )
            if wait_for_ack():
                break
        
        # Split and send chunks
        chunks = self.split_chunks(file_path)
        
        for chunk_id, chunk in enumerate(chunks, start=1):
            for _ in range(3):
                self.socket_manager.send_frame(
                    LinkChatFrame(target_mac, self.socket_manager.get_local_mac(),
                                MSG_TYPE_FILE_CHUNK, chunk_id, chunk)
                )
                if wait_for_ack():
                    break
        
        # Send file end message
        for _ in range(3):
            self.socket_manager.send_frame(
                LinkChatFrame(target_mac, self.socket_manager.get_local_mac(),
                            MSG_TYPE_FILE_END, len(chunks) + 1, b'')
            )
            if wait_for_ack():
                break
    
    def _save_file(self, file_id: str):
        """Save received file to disk"""

        if file_id not in self._receiving_files:
            return
        
        file_data = self._receiving_files[file_id]
        file_name = file_data['file_name']
        chunks = file_data['chunks']
        
        try:
            output_path = Path(DOWNLOADS_PATH) / file_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as output_file:
                for chunk in chunks:
                    output_file.write(chunk)
            
            # Notify observers
            self.notify(File(file_name))
            
        except Exception as e:
            print(f"Error saving file {file_name}: {e}")
        finally:
            # Clean up
            del self._receiving_files[file_id]

    def update(self, data: LinkChatFrame) -> None:
        """Handle incoming frames for file transfers"""
        # Always send ACK
        self.socket_manager.send_frame(
            LinkChatFrame(data.src_mac, data.dest_mac, MSG_TYPE_MESSAGE_ACK, data.msg_id, b'')
        )
        
        if data.msg_type == MSG_TYPE_FILE_START:
            # Start receiving a new file
            file_name = BinarySerializer.deserialize(data.data)
            file_id = f"{data.src_mac}_{file_name}"
            
            with self._lock:
                self._receiving_files[file_id] = {
                    'file_name': file_name,
                    'chunks': [],
                    'src_mac': data.src_mac
                }
        
        elif data.msg_type == MSG_TYPE_FILE_CHUNK:
        # Receive file chunk
        # Find the active file transfer from this source
            for file_id, file_data in self._receiving_files.items():
                if file_data['src_mac'] == data.src_mac:
                    file_data['chunks'].append(data.data)
                    break
        
        elif data.msg_type == MSG_TYPE_FILE_END:
            # File transfer complete
            
            # Find and save the completed file
            for file_id, file_data in list(self._receiving_files.items()):
                if file_data['src_mac'] == data.src_mac:
                    self._save_file(file_id)
                    break

    def split_chunks(self, file_path, chunk_size=MAX_CHUNK_SIZE):

        chunk_files = []
        
        with open(file_path, 'rb') as source_file:
            while True:
                # Read chunk_size bytes
                chunk_data = source_file.read(chunk_size)
                if not chunk_data:  # End of file
                    break

                chunk_files.append(chunk_data)

        return chunk_files

    def send_file(self, target_mac: str, file_path: str) -> None:
        """Queue a file for sending (non-blocking)"""
        if not self._running:
            raise RuntimeError("FileTransferService not started. Call start() first.")
        
        self._send_queue.put((target_mac, file_path))

    def attach(self, observer: Observer[File]) -> None:
        self.observers.add(observer)

    def detach(self, observer: Observer[File]) -> None:
        self.observers.remove(observer)
    def notify(self, notification: File) -> None:
        for observer in self.observers:
            observer.update(notification)


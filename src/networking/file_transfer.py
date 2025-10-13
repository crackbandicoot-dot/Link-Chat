# Transferencia de archivos
import pathlib

from pathlib import Path
from ..observer.observer import Observer, T
from ..observer.subject import Subject
from ..core.raw_socket_manager import raw_socket_manager
from ..core.frame import LinkChatFrame
from ..DTOS.file_info import FileInfo
from ..utils.constants import MAX_CHUNK_SIZE,MSG_TYPE_FILE_START,MSG_TYPE_FILE_CHUNK,MSG_TYPE_FILE_END,DOWNLOADS_PATH,MSG_TYPE_FILE_START_ACK,MSG_TYPE_FILE__END_ACK,MSG_TYPE_FILE_CHUNK_ACK
from ..utils.binary_serializer import BinarySerializer
from ..utils.helpers import create_message_id
from ..DTOS.file_chunk import FileChunk
from asyncio import sleep
class FileTransferManager(Subject[FileInfo],Observer[LinkChatFrame]):
    def __init__(self, socket_manager: raw_socket_manager):
        self.observers = set()
        self.socket_manager = socket_manager
        self.received_chunks  = {}
        self.received_files_names = {}
        self.chunks_confirmations ={}
        self.starts_confirmations ={}
        self.end_confirmations ={}

    def save_file(self,file_id):
        file_name = self.received_files_names[file_id]
        file_path = Path(DOWNLOADS_PATH) / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
        with open(file_path, 'wb') as output_file:
            # Sort chunks by message_id to ensure correct order
            chunks_dict = self.received_chunks[file_id]
            for chunk_id in sorted(chunks_dict.keys()):
                output_file.write(chunks_dict[chunk_id])

    def update(self, data: LinkChatFrame) -> None:
        if data.msg_type==MSG_TYPE_FILE_START_ACK:
            file_info = BinarySerializer.deserialize(data.data)
            self.starts_confirmations[file_info.id] =True

        elif data.msg_type==MSG_TYPE_FILE_START:
            file_info:FileInfo = BinarySerializer.deserialize(data.data)
            self.received_files_names[file_info.id] = file_info.name
            self.socket_manager.send_frame(LinkChatFrame(data.src_mac,data.dest_mac,MSG_TYPE_FILE_START_ACK,data.msg_id,BinarySerializer.serialize(file_info)))
            

        elif data.msg_type==MSG_TYPE_FILE_CHUNK_ACK:
            file_info:FileInfo = BinarySerializer.deserialize(data.data)
            self.received_chunks[file_info.id][data.msg_id] = True

        elif data.msg_type==MSG_TYPE_FILE_CHUNK:
            file_chunk:FileChunk = BinarySerializer.deserialize(data.data)
            self.received_chunks[file_chunk.file_info.id][data.msg_id] = file_chunk.chunk
            self.received_files_names[file_chunk.file_info.id]=file_chunk.file_info.name
            self.socket_manager.send_frame(LinkChatFrame(data.src_mac,data.dest_mac,MSG_TYPE_FILE_CHUNK_ACK,data.msg_id,BinarySerializer.serialize(file_chunk.file_info)))
        
        elif data.msg_type == MSG_TYPE_FILE__END_ACK:
            file_info:FileInfo  = BinarySerializer.deserialize(data.data)
            self.end_confirmations[file_info.id] = True

        elif data.msg_type==MSG_TYPE_FILE_END:
            file_info :FileInfo = BinarySerializer.deserialize(data.data)
            self.save_file(file_info.id)
            self.socket_manager.send_frame(LinkChatFrame(data.src_mac,data.dest_mac,MSG_TYPE_FILE__END_ACK,data.msg_id,data.data))
            self.notify(file_info)
        

    def split_chunks(self, file_path, chunk_size=MAX_CHUNK_SIZE-400):

        chunk_files = []
        
        with open(file_path, 'rb') as source_file:
            while True:
                # Read chunk_size bytes
                chunk_data = source_file.read(chunk_size)
                if not chunk_data:  # End of file
                    break

                chunk_files.append(chunk_data)

        return chunk_files
    def send_file(self,target_mac:str,file_path:str)->None:

         #Send file start frame
         file_name = Path(file_path).name
         file_info =FileInfo(file_name,create_message_id())
         serialized_info =BinarySerializer.serialize(file_info)
         self.starts_confirmations[file_info.id] = False
         while not self.starts_confirmations[file_info.id]:
            self.socket_manager.send_frame(LinkChatFrame(target_mac, self.socket_manager.get_local_mac(), MSG_TYPE_FILE_START, 0, serialized_info))
            

         #Send chunks
         chunk_number = 0
         chunks = self.split_chunks(file_path)
         for chunk in chunks:
             chunk_number+=1
             file_chunk = BinarySerializer.serialize(FileChunk(file_info,chunk))
             self.chunks_confirmations[file_info.id][chunk_number]=False
             while not self.chunks_confirmations[file_info.id][chunk_number]:   
                self.socket_manager.send_frame(LinkChatFrame(target_mac, self.socket_manager.get_local_mac(), MSG_TYPE_FILE_CHUNK, chunk_number, file_chunk))
            

         self.end_confirmations[file_info.id]=False
         while not self.end_confirmations[file_info.id]:
            self.socket_manager.send_frame((LinkChatFrame(target_mac,self.socket_manager.get_local_mac(),MSG_TYPE_FILE_END,chunk_number+1,serialized_info)))
        


    def attach(self, observer: Observer[FileInfo]) -> None:
        self.observers.add(observer)

    def detach(self, observer: Observer[FileInfo]) -> None:
        self.observers.remove(observer)
    def notify(self, notification: FileInfo) -> None:
        for observer in self.observers:
            observer.update(notification)

# Transferencia de archivos
import pathlib

from pathlib import Path
from ..observer.observer import Observer, T
from ..observer.subject import Subject
from ..core.raw_socket import raw_socket_wrapper
from  ..core.frame import LinkChatFrame
from ..DTOS.File import File
from ..utils.constants import MAX_CHUNK_SIZE,MSG_TYPE_FILE_START,MSG_TYPE_FILE_CHUNK,MSG_TYPE_FILE_END,MSG_TYPE_MESSAGE_ACK,DOWNLOADS_PATH
from  ..utils.binary_serializer import BinarySerializer
from file_info import FileInfo





class FileTransferService(Subject[File],Observer[LinkChatFrame]):
    def __init__(self):
        self.observers = set()
        self.confirmed_frame = False
        self.recived_chunks = []
        self.recived_file_name = None

    def attach(self, observer: Observer[File]) -> None:
        self.observers.add(observer)

    def detach(self, observer: Observer[File]) -> None:
        self.observers.remove(observer)
    def notify(self, notification: File) -> None:
        for observer in self.observers:
            observer.update(notification)

    def save_file(self):
        with open(DOWNLOADS_PATH+self.recived_file_name, 'wb') as output_file:
            for chunk in self.recived_chunks:
                    # Copy all data from chunk to output file
                    output_file.write(chunk)

    def update(self, data: LinkChatFrame) -> None:
        if data.msg_type==MSG_TYPE_MESSAGE_ACK:
            self.confirmed_frame=True
            return
        if data.msg_type==MSG_TYPE_FILE_START:
            self.recived_chunks.clear()
            self.recived_file_name = BinarySerializer.deserialize(data.data)

        elif data.msg_type==MSG_TYPE_FILE_CHUNK:
            self.recived_chunks.append(data.data)
        elif data.msg_type==MSG_TYPE_FILE_END:
            self.save_file()
            self.notify(File(self.recived_file_name))

        raw_socket_wrapper.send_frame(LinkChatFrame(data.src_mac,data.dest_mac,MSG_TYPE_MESSAGE_ACK,data.msg_id,b''))

    def split_chunks(self, file_path, chunk_size=MAX_CHUNK_SIZE):

        chunk_files = []
        chunk_num = 1

        with open(file_path, 'rb') as source_file:
            while True:
                # Read chunk_size bytes
                chunk_data = source_file.read(chunk_size)
                if not chunk_data:  # End of file
                    break

                chunk_files.append(chunk_data)

        return chunk_files
    async def send_file(self,target_mac:str,file_path:str)->None:

         #Send file start frame
         file_name = Path(file_path).name
         file_info =FileInfo(file_name)
         serialized_info =BinarySerializer.serialize(file_info)
         while not self.confirmed_frame:
             raw_socket_wrapper.send_frame(LinkChatFrame(target_mac, raw_socket_wrapper.get_self_mac(), MSG_TYPE_FILE_START, 0, serialized_info))
         self.confirmed_frame = False
         chunks = self.split_chunks(file_path)


         #Send chunks
         chunk_id = 0
         for chunk in chunks:
             chunk_id+=1
             while not self.confirmed_frame:
                 raw_socket_wrapper.send_frame(
                     LinkChatFrame(target_mac, raw_socket_wrapper.get_self_mac(), MSG_TYPE_FILE_CHUNK, chunk_id, chunk))
             self.confirmed_frame=False

         #send file end message
         while not self.confirmed_frame:
             raw_socket_wrapper.send_frame((LinkChatFrame(target_mac,raw_socket_wrapper.get_self_mac(),MSG_TYPE_FILE_END,chunk_id+1,b' ')))




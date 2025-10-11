# Sistema de mensajería
import asyncio
from ..observer.observer import Observer

from ..core.frame import LinkChatFrame
from ..core.raw_socket_manager import raw_socket_manager
from ..observer.subject import Subject, T
from ..utils.constants import MSG_TYPE_MESSAGE,MSG_TYPE_MESSAGE_ACK,MAX_RETRIES     # Acknowledgment de mensaje
from ..DTOS.message import Message

class MessageService(Observer[LinkChatFrame],Subject[Message], ):
     def __init__(self, socket_manager: raw_socket_manager):
         self.observers = set()
         self.confirmed_message = False
         self.socket_manager = socket_manager
   
     async def send_message(self,target_mac:str,message:str)->bool:
        #Try send message
        
        message_bytes = message.encode('utf-8')
        frame = LinkChatFrame(target_mac,self.socket_manager.get_local_mac(),MSG_TYPE_MESSAGE,0,message_bytes)

        #Retry sending
        attempts = 0
        while not self.confirmed_message and attempts<MAX_RETRIES:
            self.socket_manager.send_frame(frame)
            await asyncio.sleep(0.1)
            print("Retring messanging")
            attempts+=1
        print("Message actually send it")
        return True
    
        
     #Observer implementation
     def update(self, data: LinkChatFrame) -> None:
         if data.msg_type == MSG_TYPE_MESSAGE:
             message_text = data.data.decode('utf-8')
             message = Message(message_text,data.src_mac)
             self.socket_manager.send_frame(LinkChatFrame(data.src_mac,self.socket_manager.get_local_mac(),MSG_TYPE_MESSAGE_ACK,0,b''))
             self.notify(message)

         if data.msg_type == MSG_TYPE_MESSAGE_ACK:
             self.confirmed_message = True

     
    #Subject implementation    
     def attach(self, observer: Observer[Message]) -> None:
         self.observers.add(observer)

     def detach(self, observer: Observer[Message]) -> None:
         self.observers.remove(observer)

     def notify(self,notification: Message) -> None:
         print("Mensaje recibido!!!!!!!!")
         for observer in self.observers:
             observer.update(notification)




import struct
from typing import Optional
from utils.constants import PROTOCOL_VERSION

class LinkChatProtocol:
    """
    Protocolo de aplicación para Link-Chat 
    """
    
    # Estructura del protocolo Link-Chat:
    # [Version][MsgType][MsgID][DataLength][Checksum][Data]
    
    PROTOCOL_HEADER_SIZE = 10  # 1 + 1 + 4 + 2 + 2 bytes
    
    def __init__(self, msg_type: int, msg_id: int, data: bytes, checksum: int = 0):
        """
        Construye el Payload con el protocolo Link-Chat
        
        Args:
            msg_type: Tipo de mensaje (ver constants.py)
            msg_id: ID único del mensaje
            data: Datos del mensaje
            checksum: Checksum para verificación de integridad
        """
        self.version = PROTOCOL_VERSION
        self.msg_type = msg_type
        self.msg_id = msg_id
        self.data_length = len(data)
        self.data = data
        self.checksum = checksum
    
    def to_bytes(self) -> bytes:
        """
        Convierte el mensaje del protocolo a bytes
        
        Returns:
            bytes: Mensaje completo en bytes
        """
        # Calcular checksum si no se proporcionó
        if self.checksum == 0:
            self.checksum = self._calculate_checksum()
        
        # Construir cabecera del protocolo
        header = struct.pack(
            '!BBIHH',  # B = unsigned char, I = unsigned int, H = unsigned short
            self.version,
            self.msg_type,
            self.msg_id,
            self.data_length & 0xFFFF,  # Limitar a 16 bits
            self.checksum
        )
        
        return header + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['LinkChatProtocol']:
        """
        Construye el Payload desde bytes
        
        Args:
            data: Datos del payload de la trama
            
        Returns:
            Optional[LinkChatProtocol]: Mensaje del protocolo o None si hay error
        """
        if len(data) < cls.PROTOCOL_HEADER_SIZE:
            return None
        
        try:
            # Extraer cabecera del protocolo
            version, msg_type, msg_id, data_length, checksum = struct.unpack(
                '!BBIHH',
                data[:cls.PROTOCOL_HEADER_SIZE]
            )
            
            # Verificar versión del protocolo
            if version != PROTOCOL_VERSION:
                return None
            
            # Verificar que tenemos todos los datos
            if len(data) < cls.PROTOCOL_HEADER_SIZE + data_length:
                return None
            
            # Extraer datos del mensaje
            msg_data = data[cls.PROTOCOL_HEADER_SIZE:cls.PROTOCOL_HEADER_SIZE + data_length]
            
            # Crear instancia del protocolo
            protocol_msg = cls(msg_type, msg_id, msg_data, checksum)
            
            # Verificar checksum
            if not protocol_msg._verify_checksum():
                return None
            
            return protocol_msg
            
        except struct.error:
            return None
    
    def _calculate_checksum(self) -> int:
        """
        Calcula el checksum del mensaje
        
        Returns:
            int: Checksum calculado
        """
        # Simple checksum basado en suma de bytes
        checksum = 0
        checksum += self.version + self.msg_type
        checksum += (self.msg_id >> 16) & 0xFFFF
        checksum += self.msg_id & 0xFFFF
        checksum += (self.data_length >> 16) & 0xFFFF
        checksum += self.data_length & 0xFFFF
        
        for byte in self.data:
            checksum += byte
        
        return checksum & 0xFFFF
    
    def _verify_checksum(self) -> bool:
        """
        Verifica la integridad del mensaje usando checksum
        
        Returns:
            bool: True si el checksum es válido
        """
        saved_checksum = self.checksum
        self.checksum = 0
        calculated_checksum = self._calculate_checksum()
        self.checksum = saved_checksum
        
        return calculated_checksum == saved_checksum
    
    def __str__(self) -> str:
        """
        Representación string del mensaje del protocolo
        """
        return (f"LinkChatProtocol(version={self.version}, type={self.msg_type}, "
                f"id={self.msg_id}, data_length={self.data_length}, "
                f"checksum=0x{self.checksum:04x})")

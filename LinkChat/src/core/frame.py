import struct
from typing import Optional
from utils.constants import ETHERTYPE_LINKCHAT, PROTOCOL_VERSION
from utils.helpers import format_mac_address, parse_mac_address


class LinkChatFrame:
    """
    Clase que maneja tanto la trama Ethernet 
    
    Estructura completa:
    [Dest MAC][Src MAC][EtherType][Version][MsgType][MsgID][DataLength][Checksum][Data]
    """
      
    TOTAL_HEADER_SIZE = 24  # 24 bytes
    
    def __init__(self, dest_mac: str, src_mac: str, msg_type: int, msg_id: int, data: bytes):
        """
        Inicializa una trama Link-Chat completa
        
        Args:
            dest_mac: Dirección MAC destino (formato xx:xx:xx:xx:xx:xx)
            src_mac: Dirección MAC origen (formato xx:xx:xx:xx:xx:xx)
            msg_type: Tipo de mensaje del protocolo (ver constants.py)
            msg_id: ID único del mensaje
            data: Datos del mensaje
        """
        
        self.dest_mac = dest_mac
        self.src_mac = src_mac
        self.ethertype = ETHERTYPE_LINKCHAT
        self.version = PROTOCOL_VERSION
        self.msg_type = msg_type
        self.msg_id = msg_id
        self.data_length = len(data)
        self.data = data
        self.checksum = 0  # Se calculará automáticamente
    
    def to_bytes(self) -> bytes:
        """
        Convierte la trama  a bytes para transmisión
        
        Returns:
            bytes: Trama Ethernet completa
        """
        # Calcular checksum
        self.checksum = self._calculate_checksum()
        
        
        dest_mac_bytes = parse_mac_address(self.dest_mac)
        src_mac_bytes = parse_mac_address(self.src_mac)
        
        header = struct.pack(
            '!6s6sHBBIHH',  # Ethernet: 6s6sH + Protocol: BBIHH
            dest_mac_bytes,           # Dest MAC (6 bytes)
            src_mac_bytes,            # Src MAC (6 bytes)
            self.ethertype,           # EtherType (2 bytes)
            self.version,             # Version (1 byte)
            self.msg_type,            # Message Type (1 byte)
            self.msg_id,              # Message ID (4 bytes)
            self.data_length & 0xFFFF,  # Data Length (2 bytes, limitado a 16 bits)
            self.checksum             # Checksum (2 bytes)
        )
        
        # Combinar header completo con datos
        return header + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['LinkChatFrame']:
        """
        Construye una trama Link-Chat desde bytes recibidos
        
        Args:
            data: Datos recibidos de la red
            
        Returns:
            Optional[LinkChatFrame]: Trama Link-Chat o None si hay error
        """
        if len(data) < cls.TOTAL_HEADER_SIZE:
            return None
        
        try:
            # Extraer header completo (Ethernet + Link-Chat) en una sola operación
            dest_mac_bytes, src_mac_bytes, ethertype, version, msg_type, msg_id, data_length, checksum = struct.unpack(
                '!6s6sHBBIHH',
                data[:cls.TOTAL_HEADER_SIZE]
            )
            
            # Verificar que es nuestro protocolo
            if ethertype != ETHERTYPE_LINKCHAT:
                return None
            
            # Verificar versión del protocolo
            if version != PROTOCOL_VERSION:
                return None
            
            # Convertir MACs a formato string
            dest_mac = format_mac_address(dest_mac_bytes)
            src_mac = format_mac_address(src_mac_bytes)
            
            # Verificar que tenemos todos los datos
            if len(data) < cls.TOTAL_HEADER_SIZE + data_length:
                return None
            
            # Extraer datos del mensaje
            payload_start = cls.TOTAL_HEADER_SIZE
            msg_data = data[payload_start:payload_start + data_length]
            
            # Crear instancia
            frame = cls(dest_mac, src_mac, msg_type, msg_id, msg_data)
            frame.checksum = checksum
            
            # Verificar checksum
            if not frame._verify_checksum():
                return None
            
            return frame
            
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
    
    def get_payload_size(self) -> int:
        """
        Obtiene el tamaño del payload (datos sin headers)
        
        Returns:
            int: Tamaño del payload en bytes
        """
        return len(self.data)
    
    def get_total_size(self) -> int:
        """
        Obtiene el tamaño total de la trama
        
        Returns:
            int: Tamaño total en bytes
        """
        return self.TOTAL_HEADER_SIZE + len(self.data)
    
    
    def __str__(self) -> str:
        """
        Representación string de la trama
        """
        return (f"LinkChatFrame(dest={self.dest_mac}, src={self.src_mac}, "
                f"type={self.msg_type}, id={self.msg_id}, "
                f"size={self.get_total_size()}, broadcast={self.is_broadcast()})")
    
    def __repr__(self) -> str:
        """
        Representación detallada de la trama
        """
        return (f"LinkChatFrame(dest_mac='{self.dest_mac}', src_mac='{self.src_mac}', "
                f"msg_type={self.msg_type}, msg_id={self.msg_id}, "
                f"data_length={self.data_length}, checksum=0x{self.checksum:04x})")
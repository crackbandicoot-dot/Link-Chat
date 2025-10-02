# Manejo de tramas 

import struct
from typing import Optional, Tuple
from utils.constants import ETHERTYPE_LINKCHAT
from utils.helpers import format_mac_address, parse_mac_address

class Frame:
    """
    Clase para manejar tramas  para el protocolo Link-Chat
    """
    
    # Estructura de trama : [Dest MAC][Src MAC][EtherType][Payload]
    ETHERNET_HEADER_SIZE = 14  # 6 + 6 + 2 bytes
    
    def __init__(self, dest_mac: str, src_mac: str, payload: bytes):
        """
        Inicializa una trama Ethernet
        
        Args:
            dest_mac: Dirección MAC destino (formato xx:xx:xx:xx:xx:xx)
            src_mac: Dirección MAC origen (formato xx:xx:xx:xx:xx:xx)
            payload: Datos a transmitir
        """
        self.dest_mac = dest_mac
        self.src_mac = src_mac
        self.ethertype = ETHERTYPE_LINKCHAT
        self.payload = payload
    
    def to_bytes(self) -> bytes:
        """
        Convierte la trama a bytes para transmisión
        
        Returns:
            bytes: Trama Ethernet completa en bytes
        """
        # Convertir direcciones MAC a bytes
        dest_mac_bytes = parse_mac_address(self.dest_mac)
        src_mac_bytes = parse_mac_address(self.src_mac)
        
        # Construir cabecera Ethernet
        header = struct.pack(
            '!6s6sH',  # ! = network byte order, 6s = 6 bytes, H = unsigned short
            dest_mac_bytes,
            src_mac_bytes,
            self.ethertype
        )
        
        return header + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['EthernetFrame']:
        """
        Construye una trama Ethernet desde bytes recibidos
        
        Args:
            data: Datos recibidos de la red
            
        Returns:
            Optional[EthernetFrame]: Trama Ethernet o None si hay error
        """
        if len(data) < cls.ETHERNET_HEADER_SIZE:
            return None
        
        try:
            # Extraer cabecera Ethernet
            dest_mac_bytes, src_mac_bytes, ethertype = struct.unpack(
                '!6s6sH',
                data[:cls.ETHERNET_HEADER_SIZE]
            )
            
            # Verificar que es nuestro protocolo
            if ethertype != ETHERTYPE_LINKCHAT:
                return None
            
            # Convertir MACs a formato string
            dest_mac = format_mac_address(dest_mac_bytes)
            src_mac = format_mac_address(src_mac_bytes)
            
            # Extraer payload
            payload = data[cls.ETHERNET_HEADER_SIZE:]
            
            return cls(dest_mac, src_mac, payload)
            
        except struct.error:
            return None
    
    def __str__(self) -> str:
        """
        Representación string de la trama
        """
        return (f"EthernetFrame(dest={self.dest_mac}, src={self.src_mac}, "
                f"ethertype=0x{self.ethertype:04x}, payload_size={len(self.payload)})")



import os
import platform
import struct
import hashlib
import time
from typing import Optional, List, Dict, Any
import socket
import fcntl
import array
            
def check_admin_privileges() -> bool:
    """
    Verifica si el programa se está ejecutando con permisos de administrador
    
    Returns:
        bool: True si tiene permisos de admin, False en caso contrario
    """
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False

def get_network_interfaces() -> List[str]:
    """
    Obtiene la lista de interfaces de red disponibles
    
    Returns:
        List[str]: Lista de nombres de interfaces de red
    """
    interfaces = []
    
    try: 
        if platform.system() == "Windows":
            # Windows: Usar psutil o WMI
            import psutil
            for interface_name, _ in psutil.net_if_addrs().items():
                interfaces.append(interface_name)
        else:
            # Usar ioctl para obtener interfaces
            max_possible = 128
            bytes_len = max_possible * 32
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            names = array.array('B', b'\0' * bytes_len)
            outbytes = struct.unpack('iL', fcntl.ioctl(
                s.fileno(),
                0x8912,  # SIOCGIFCONF
                struct.pack('iL', bytes_len, names.buffer_info()[0])
            ))[0]
            namestr = names.tobytes()[:outbytes]
            
            for i in range(0, outbytes, 40):
                name = namestr[i:i+16].split(b'\0', 1)[0]
                interfaces.append(name.decode())
                
    except Exception as e:
        print(f"Error obteniendo interfaces: {e}")
        # Interfaces por defecto
        if platform.system() == "Windows":
            interfaces = ["Ethernet", "Wi-Fi"]
        else:
            interfaces = ["eth0", "wlan0", "lo"]
    
    return interfaces

def format_mac_address(mac_bytes: bytes) -> str:
    """
    Formatea una dirección MAC desde bytes a string
    
    Args:
        mac_bytes: Bytes de la dirección MAC
        
    Returns:
        str: Dirección MAC formateada (xx:xx:xx:xx:xx:xx)
    """
    return ':'.join(f'{b:02x}' for b in mac_bytes)

def parse_mac_address(mac_str: str) -> bytes:
    """
    Convierte una dirección MAC string a bytes
    
    Args:
        mac_str: Dirección MAC como string (xx:xx:xx:xx:xx:xx)
        
    Returns:
        bytes: Bytes de la dirección MAC
    """
    return bytes.fromhex(mac_str.replace(':', ''))

def get_timestamp() -> int:
    """
    Obtiene timestamp actual en milisegundos
    
    Returns:
        int: Timestamp en milisegundos
    """
    return int(time.time() * 1000)

def create_message_id() -> int:
    """
    Crea un ID único para mensajes basado en timestamp
    
    Returns:
        int: ID único del mensaje
    """
    return int(time.time() * 1000000) % (2**32)  # 32-bit ID

def log_message(level: str, message: str, show_timestamp: bool = True) -> None:
    """
    Registra un mensaje con nivel y timestamp
    
    Args:
        level: Nivel del mensaje (INFO, WARNING, ERROR, DEBUG)
        message: Mensaje a registrar
        show_timestamp: Si mostrar timestamp
    """
    timestamp = ""
    if show_timestamp:
        timestamp = time.strftime("[%H:%M:%S] ")
    
    level_colors = {
        "INFO": "\033[32m",     # Verde
        "WARNING": "\033[33m",  # Amarillo
        "ERROR": "\033[31m",    # Rojo
        "DEBUG": "\033[36m",    # Cyan
        "RESET": "\033[0m"      # Reset
    }
    
    color = level_colors.get(level, "")
    reset = level_colors["RESET"]
    
    print(f"{timestamp}{color}[{level}]{reset} {message}")
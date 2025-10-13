# Constantes del sistema# Configuración de red
DEFAULT_INTERFACE = "eth0"  # Interfaz de red por defecto (Linux)

# Protocolo personalizado
ETHERTYPE_LINKCHAT = 0x88B5  # EtherType personalizado para Link-Chat
PROTOCOL_VERSION = 1

# Tipos de mensaje del protocolo
MSG_TYPE_DISCOVERY = 0x01      # Descubrimiento de dispositivos
MSG_TYPE_DISCOVERY_REPLY = 0x02  # Respuesta a descubrimiento
MSG_TYPE_MESSAGE = 0x03        # Mensaje de texto
MSG_TYPE_MESSAGE_ACK = 0x04    # Acknowledgment de mensaje
MSG_TYPE_FILE_START = 0x05     # Inicio de transferencia de archivo
MSG_TYPE_FILE_CHUNK = 0x06     # Fragmento de archivo
MSG_TYPE_FILE_END = 0x07       # Fin de transferencia de archivo
MSG_TYPE_FILE_START_ACK = 0x0B #Mesnaje confirmacion de inicio de archivo
MSG_TYPE_FILE_CHUNK_ACK = 0x0C #Mensaje de confirmacion de chunk
MSG_TYPE_FILE__END_ACK = 0x08  # Acknowledgment de archivo
MSG_TYPE_HEARTBEAT = 0x09      # Heartbeat para mantener conexión
MSG_TYPE_BROADCAST = 0x0A      # Mensaje broadcast

# Configuración de transferencia de archivos
MAX_CHUNK_SIZE = 1400  # Tamaño máximo de fragmento (considerando MTU)
FILE_TIMEOUT = 30      # Timeout para transferencia de archivos (segundos)
MAX_RETRIES = 10        # Máximo número de reintentos

# Configuración de red
DISCOVERY_INTERVAL = 35    # Intervalo de descubrimiento (segundos)
HEARTBEAT_INTERVAL = 35    # Intervalo de heartbeat (segundos)
DEVICE_TIMEOUT = 60        # Timeout para considerar dispositivo desconectado

# Configuración de interfaz
CONSOLE_REFRESH_RATE = 1   # Frecuencia de actualización de consola (segundos)

# Códigos de estado
STATUS_SUCCESS = 0
STATUS_ERROR = 1
STATUS_TIMEOUT = 2
STATUS_FILE_NOT_FOUND = 3
STATUS_PERMISSION_DENIED = 4

# Direcciones especiales
BROADCAST_MAC = "ff:ff:ff:ff:ff:ff"
NULL_MAC = "00:00:00:00:00:00"

# Configuración de logging
LOG_LEVEL_DEBUG = 0
LOG_LEVEL_INFO = 1
LOG_LEVEL_WARNING = 2
LOG_LEVEL_ERROR = 3

# Límites del sistema
MAX_MESSAGE_SIZE = 4096    # Tamaño máximo de mensaje de texto
MAX_FILENAME_SIZE = 255    # Tamaño máximo de nombre de archivo
MAX_DEVICES = 100          # Máximo número de dispositivos en la red

DOWNLOADS_PATH = '/home/Downloads'

BUFFER_SIZE = 65536 # Tamaño máximo de un IP Frame

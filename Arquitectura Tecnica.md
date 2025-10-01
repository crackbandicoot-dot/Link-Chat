# Arquitectura Técninca

```
LinkChat/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ethernet_frame.py    # Manejo de tramas 
│   │   ├── raw_socket.py        # Comunicación con raw sockets
│   │   └── protocol.py          # Protocolo de comunicación personalizado
│   ├── networking/
│   │   ├── __init__.py
│   │   ├── discovery.py         # Descubrimiento automático de dispositivos
│   │   ├── messaging.py         # Sistema de mensajería
│   │   └── file_transfer.py     # Transferencia de archivos
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── console.py           # Interfaz de consola
│   │   └── menu.py              # Sistema de menús
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py           # Funciones auxiliares
│       └── constants.py         # Constantes del sistema
```
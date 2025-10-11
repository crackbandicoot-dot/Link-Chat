# 🎨 Link-Chat GUI - Interfaz Gráfica

Interfaz gráfica moderna para Link-Chat construida con **Tkinter**.

## 📋 **Características**

### ✅ **Implementado:**
- 🖥️ **Ventana principal** con menú completo
- 📱 **Panel de dispositivos** con lista dinámica
- 💬 **Ventanas de chat** individuales por dispositivo
- 🔔 **Sistema de notificaciones** en tiempo real
- 🧵 **Thread-safe** mediante Queue pattern
- 🎨 **Interfaz intuitiva** y profesional
- 📊 **Barra de estado** con información del sistema
- 🔄 **Descubrimiento automático** de dispositivos

### 🚧 **En desarrollo:**
- 📁 Diálogo de transferencia de archivos
- 📢 Mensajes broadcast desde GUI
- 📝 Historial persistente de mensajes
- 🎨 Temas personalizables (dark/light)

---

## 🚀 **Instalación**

### **Requisitos:**
```bash
# Python 3.8+
# Tkinter (generalmente incluido con Python)

# En Linux, si Tkinter no está disponible:
sudo apt-get install python3-tk

# Verificar instalación:
python -c "import tkinter; print('Tkinter OK')"
```

### **No requiere instalación de paquetes adicionales** ✅

---

## 💻 **Uso**

### **Iniciar la GUI:**

```bash
# Opción 1: Usar el launcher
python gui_launcher.py

# Opción 2: Ejecutar directamente (con permisos)
sudo python gui_launcher.py  # Linux/macOS

# Windows (como Administrador):
python gui_launcher.py
```

### **Flujo de uso:**

1. **Seleccionar interfaz de red** - Al iniciar, elige tu interfaz Ethernet/WiFi
2. **Esperar descubrimiento** - La aplicación buscará dispositivos automáticamente
3. **Abrir chat** - Doble clic en un dispositivo o botón "Enviar Mensaje"
4. **Enviar mensajes** - Escribe y presiona Enter o click en "Enviar"

---

## 🏗️ **Arquitectura**

### **Estructura de archivos:**

```
src/interface/gui/
├── __init__.py
├── main_window.py          # Ventana principal
├── thread_controller.py    # Adaptador thread-safe
└── widgets/
    ├── __init__.py
    ├── device_panel.py     # Panel de dispositivos
    └── chat_window.py      # Ventana de chat
```

### **Componentes principales:**

#### **1. MainWindow** (`main_window.py`)
Ventana principal que contiene:
- Menú de navegación
- Panel de dispositivos descubiertos
- Panel de información del sistema
- Barra de estado
- Gestión de servicios de red

#### **2. ThreadSafeController** (`thread_controller.py`)
Adaptador que conecta:
- **Servicios de red** (threads secundarios) → **Queue**
- **Queue** → **Tkinter** (thread principal)
- Implementa patrón Observer para recibir eventos
- Usa `Queue` para comunicación thread-safe

#### **3. DevicePanel** (`widgets/device_panel.py`)
Panel con:
- Lista de dispositivos (Treeview)
- Estado en tiempo real (🟢/🔴)
- Botones de acción (mensaje, archivo)
- Doble-click para abrir chat

#### **4. ChatWindow** (`widgets/chat_window.py`)
Ventana de chat que:
- Muestra historial de mensajes
- Diferencia mensajes enviados/recibidos
- Envío asíncrono de mensajes
- Notificaciones visuales

---

## 🔧 **Integración con el proyecto**

### **Patrón Observer:**

La GUI se integra sin modificar el código existente usando el patrón Observer:

```python
# Los servicios notifican al controlador
device_discovery.attach(controller)
message_service.attach(controller)
file_service.attach(controller)

# El controlador usa Queue para thread-safety
controller.register_callback('device', gui_callback)
controller.register_callback('message', gui_callback)
```

### **Threading:**

```
┌─────────────────┐
│  Main Thread    │  ← Tkinter (GUI)
│  (Tkinter)      │
└────────▲────────┘
         │
         │ Queue (thread-safe)
         │
┌────────┴────────┐
│  Worker Threads │  ← Servicios de red
│  - Socket recv  │
│  - Discovery    │
│  - Services     │
└─────────────────┘
```

---

## 🎯 **Características avanzadas**

### **Thread-Safety:**
- Usa `queue.Queue()` para comunicación entre threads
- Actualiza GUI solo desde thread principal
- `root.after()` para callbacks periódicos

### **Gestión de ventanas:**
- Ventanas de chat múltiples (una por dispositivo)
- Tracking de ventanas abiertas
- Cleanup automático al cerrar

### **Sistema de notificaciones:**
- Alertas visuales (cambio de color)
- Sonido (`bell()`) para eventos importantes
- Actualización de barra de estado

---

## 🐛 **Troubleshooting**

### **Error: "Permission denied"**
```bash
# Linux/macOS - Ejecutar con sudo:
sudo python gui_launcher.py

# Windows - Ejecutar como Administrador
```

### **Error: "No module named 'tkinter'"**
```bash
# Linux:
sudo apt-get install python3-tk

# macOS:
brew install python-tk

# Windows: Reinstalar Python con opción "tcl/tk"
```

### **La GUI no responde:**
- Verifica que no haya bucles bloqueantes en el código
- Los eventos de red se procesan en threads separados
- Usa `root.after()` para operaciones asíncronas

### **Dispositivos no aparecen:**
- Verifica permisos de administrador
- Comprueba que la interfaz esté activa
- Revisa que no haya firewall bloqueando

---

## 📚 **Ejemplos de uso**

### **Abrir chat programáticamente:**
```python
# Desde MainWindow
self._open_chat("aa:bb:cc:dd:ee:ff")
```

### **Agregar dispositivo manualmente:**
```python
# Desde DevicePanel
device_panel.add_device(
    "aa:bb:cc:dd:ee:ff",
    {'active': True, 'last_seen': 'Ahora'}
)
```

### **Recibir mensaje en chat:**
```python
# ChatWindow recibe automáticamente vía Observer
# Pero también puedes hacerlo manualmente:
chat_window.receive_message(message_object)
```

---

## 🚀 **Próximas mejoras**

### **Prioridad Alta:**
- [ ] Panel de transferencia de archivos con barra de progreso
- [ ] Diálogo de mensaje broadcast
- [ ] Historial persistente (SQLite)

### **Prioridad Media:**
- [ ] Temas personalizables
- [ ] Notificaciones del sistema (notifypy)
- [ ] Iconos personalizados
- [ ] Sistema tray icon

### **Prioridad Baja:**
- [ ] Configuración avanzada
- [ ] Logs visuales
- [ ] Estadísticas de red

---

## 🤝 **Contribución**

Para agregar funcionalidades:

1. **Widgets nuevos** → `src/interface/gui/widgets/`
2. **Callbacks** → Registrar en `ThreadSafeController`
3. **UI changes** → Modificar en `MainWindow`

**Recuerda:** Siempre usar Queue para comunicación entre threads.

---

## 📞 **Soporte**

Si encuentras bugs o tienes sugerencias:
1. Verifica los logs en consola
2. Revisa el estado de los servicios
3. Comprueba permisos de red

---

*GUI creada el 10 de Octubre, 2025*
*Desarrollada con Python + Tkinter*

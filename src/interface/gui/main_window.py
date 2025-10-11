"""
Ventana principal de la GUI de Link-Chat
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional
import sys
import os

from src.utils.helpers import log_message, get_network_interfaces
from src.core.raw_socket_manager import raw_socket_manager
from src.networking.discovery import DeviceDiscovery
from src.networking.messaging import MessageService
from src.networking.file_transfer import FileTransferService
from src.interface.gui.thread_controller import ThreadSafeController
from src.interface.gui.widgets.device_panel import DevicePanel
from src.interface.gui.widgets.chat_window import ChatWindow


class MainWindow(tk.Tk):
    """Ventana principal de Link-Chat GUI"""
    
    def __init__(self):
        """Inicializa la ventana principal"""
        super().__init__()
        
        self.title("Link-Chat - Mensajería P2P")
        self.geometry("800x600")
        
        # Servicios
        self.socket_manager = None
        self.device_discovery = None
        self.message_service = None
        self.file_service = None
        self.controller = ThreadSafeController()
        
        # Ventanas de chat abiertas
        self.chat_windows = {}  # mac -> ChatWindow
        
        # Crear UI
        self._create_menu()
        self._create_widgets()
        self._create_statusbar()
        
        # Configurar cierre
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Mostrar diálogo de selección de interfaz
        self.after(100, self._show_interface_selection)
    
    def _create_menu(self):
        """Crea la barra de menú"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Cambiar interfaz", command=self._change_interface)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_close)
        
        # Menú Dispositivos
        devices_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dispositivos", menu=devices_menu)
        devices_menu.add_command(label="Enviar mensaje broadcast", command=self._send_broadcast)
        devices_menu.add_command(label="Refrescar lista", command=self._refresh_devices)
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Acerca de", command=self._show_about)
    
    def _create_widgets(self):
        """Crea los widgets principales"""
        # Frame principal con padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título y logo
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            title_frame,
            text="📡 Link-Chat",
            font=('Arial', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            title_frame,
            text="Mensajería P2P sobre Ethernet",
            font=('Arial', 10),
            foreground='gray'
        ).pack(side=tk.LEFT, padx=10)
        
        # Separador
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # PanedWindow para dividir la ventana
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo - Dispositivos
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        self.device_panel = DevicePanel(
            left_frame,
            on_device_select=self._open_chat
        )
        self.device_panel.pack(fill=tk.BOTH, expand=True)
        
        # Panel derecho - Información
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self._create_info_panel(right_frame)
    
    def _create_info_panel(self, parent):
        """
        Crea el panel de información
        
        Args:
            parent: Widget padre
        """
        # Título
        ttk.Label(
            parent,
            text="ℹ️ Información",
            font=('Arial', 12, 'bold')
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # Frame para información
        info_frame = ttk.LabelFrame(parent, text="Estado del Sistema", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Labels de información
        self.interface_label = ttk.Label(
            info_frame,
            text="Interfaz: No inicializada",
            font=('Arial', 10)
        )
        self.interface_label.pack(anchor=tk.W, pady=2)
        
        self.mac_label = ttk.Label(
            info_frame,
            text="MAC local: --:--:--:--:--:--",
            font=('Arial', 10)
        )
        self.mac_label.pack(anchor=tk.W, pady=2)
        
        self.discovery_label = ttk.Label(
            info_frame,
            text="Descubrimiento: Detenido",
            font=('Arial', 10)
        )
        self.discovery_label.pack(anchor=tk.W, pady=2)
        
        ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Instrucciones
        instructions = ttk.Label(
            info_frame,
            text="📋 Instrucciones:\n\n"
                 "1. Selecciona una interfaz de red\n"
                 "2. Espera a que se descubran dispositivos\n"
                 "3. Doble clic en un dispositivo para chatear\n"
                 "4. Usa los botones para enviar archivos",
            justify=tk.LEFT,
            font=('Arial', 9),
            foreground='gray'
        )
        instructions.pack(anchor=tk.W, pady=10)
    
    def _create_statusbar(self):
        """Crea la barra de estado"""
        statusbar = ttk.Frame(self, relief=tk.SUNKEN)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            statusbar,
            text="Inicializando...",
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Indicador de conexión
        self.connection_indicator = ttk.Label(
            statusbar,
            text="⚫ Desconectado",
            foreground='red'
        )
        self.connection_indicator.pack(side=tk.RIGHT, padx=5)
    
    def _show_interface_selection(self):
        """Muestra diálogo para seleccionar interfaz de red"""
        interfaces = get_network_interfaces()
        
        if not interfaces:
            messagebox.showerror(
                "Error",
                "No se encontraron interfaces de red disponibles.\n"
                "Verifica que tengas permisos de administrador."
            )
            self.destroy()
            return
        
        # Diálogo de selección
        dialog = tk.Toplevel(self)
        dialog.title("Seleccionar Interfaz de Red")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(
            dialog,
            text="Selecciona la interfaz de red:",
            font=('Arial', 12, 'bold')
        ).pack(pady=10)
        
        # Listbox para interfaces
        listbox = tk.Listbox(dialog, font=('Arial', 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        for interface in interfaces:
            listbox.insert(tk.END, interface)
        
        if interfaces:
            listbox.selection_set(0)
        
        # Botones
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                interface = listbox.get(selection[0])
                dialog.destroy()
                self._initialize_network(interface)
            else:
                messagebox.showwarning("Advertencia", "Selecciona una interfaz")
        
        def on_cancel():
            dialog.destroy()
            self.destroy()
        
        ttk.Button(button_frame, text="Aceptar", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Centrar diálogo
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _initialize_network(self, interface: str):
        """
        Inicializa los servicios de red
        
        Args:
            interface: Nombre de la interfaz de red
        """
        try:
            self.status_label.config(text=f"Inicializando en {interface}...")
            
            # Inicializar socket manager
            self.socket_manager = raw_socket_manager(interface)
            self.socket_manager.start_reciving()
            
            # Obtener MAC local
            local_mac_bytes = self.socket_manager.get_local_mac()
            local_mac = ':'.join(f'{b:02x}' for b in local_mac_bytes)
            
            # Inicializar descubrimiento
            self.device_discovery = DeviceDiscovery(self.socket_manager)
            self.device_discovery.attach(self.controller)
            self.device_discovery.start_discovery()
            
            # Inicializar servicios
            self.message_service = MessageService(self.socket_manager)
            self.socket_manager.attach(self.message_service)
            self.message_service.attach(self.controller)
            
            self.file_service = FileTransferService(self.socket_manager)
            self.socket_manager.attach(self.file_service)
            self.file_service.attach(self.controller)
            
            # Registrar callbacks
            self.controller.register_callback('device', self._on_device_update)
            self.controller.register_callback('message', self._on_message_received)
            self.controller.register_callback('file', self._on_file_received)
            
            # Iniciar procesamiento de colas
            self.controller.process_queues(self)
            
            # Actualizar UI
            self.interface_label.config(text=f"Interfaz: {interface}")
            self.mac_label.config(text=f"MAC local: {local_mac}")
            self.discovery_label.config(text="Descubrimiento: Activo")
            self.connection_indicator.config(text="🟢 Conectado", foreground='green')
            self.status_label.config(text="Sistema inicializado correctamente")
            
            log_message("INFO", f"GUI inicializada en {interface}")
            
        except Exception as e:
            messagebox.showerror(
                "Error de Inicialización",
                f"No se pudo inicializar la red:\n{str(e)}\n\n"
                "Asegúrate de ejecutar con permisos de administrador."
            )
            self.destroy()
    
    def _on_device_update(self, device_data: Dict):
        """
        Callback para actualizaciones de dispositivos
        
        Args:
            device_data: Datos del dispositivo
        """
        mac = device_data['mac']
        action = device_data['action']
        info = device_data.get('info', {})
        
        if action == 'discovered':
            self.device_panel.add_device(mac, info)
            self.status_label.config(text=f"Nuevo dispositivo: {mac}")
        elif action == 'updated':
            self.device_panel.add_device(mac, info)
        elif action == 'disconnected':
            self.device_panel.update_device_status(mac, False)
            self.status_label.config(text=f"Dispositivo desconectado: {mac}")
    
    def _on_message_received(self, message):
        """
        Callback para mensajes recibidos
        
        Args:
            message: Objeto Message
        """
        sender_mac = message.sender_mac
        
        # Si hay ventana de chat abierta, enviarle el mensaje
        if sender_mac in self.chat_windows:
            self.chat_windows[sender_mac].receive_message(message)
        else:
            # Mostrar notificación
            self.status_label.config(text=f"Mensaje de {sender_mac}")
            self.bell()
    
    def _on_file_received(self, file_data):
        """
        Callback para archivos recibidos
        
        Args:
            file_data: Datos del archivo
        """
        self.status_label.config(text=f"Archivo recibido: {file_data.name}")
        messagebox.showinfo("Archivo Recibido", f"Se recibió: {file_data.name}")
    
    def _open_chat(self, mac: str):
        """
        Abre ventana de chat con un dispositivo
        
        Args:
            mac: MAC del dispositivo
        """
        if mac in self.chat_windows:
            # Traer ventana existente al frente
            self.chat_windows[mac].lift()
            self.chat_windows[mac].focus()
        else:
            # Crear nueva ventana
            local_mac_bytes = self.socket_manager.get_local_mac()
            local_mac = ':'.join(f'{b:02x}' for b in local_mac_bytes)
            
            chat_window = ChatWindow(
                self,
                mac,
                self.message_service,
                local_mac
            )
            self.chat_windows[mac] = chat_window
            
            # Registrar cierre
            def on_close():
                if mac in self.chat_windows:
                    del self.chat_windows[mac]
                chat_window.destroy()
            
            chat_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def _send_broadcast(self):
        """Envía mensaje broadcast"""
        # TODO: Implementar diálogo de mensaje broadcast
        messagebox.showinfo("Broadcast", "Funcionalidad en desarrollo")
    
    def _refresh_devices(self):
        """Refresca la lista de dispositivos"""
        self.status_label.config(text="Refrescando lista de dispositivos...")
        # La lista se actualiza automáticamente vía Observer
    
    def _change_interface(self):
        """Cambia la interfaz de red"""
        if messagebox.askyesno(
            "Cambiar Interfaz",
            "¿Deseas cambiar de interfaz de red?\n"
            "Esto cerrará todas las conexiones actuales."
        ):
            self._shutdown_network()
            self._show_interface_selection()
    
    def _show_about(self):
        """Muestra información sobre la aplicación"""
        messagebox.showinfo(
            "Acerca de Link-Chat",
            "Link-Chat v1.0\n\n"
            "Mensajería y transferencia de archivos P2P\n"
            "sobre protocolo Ethernet personalizado.\n\n"
            "Desarrollado con Python + Tkinter"
        )
    
    def _shutdown_network(self):
        """Cierra todos los servicios de red"""
        if self.device_discovery:
            self.device_discovery.stop_discovery()
        
        if self.socket_manager:
            self.socket_manager.stop_reciving()
        
        self.connection_indicator.config(text="⚫ Desconectado", foreground='red')
        self.status_label.config(text="Servicios detenidos")
    
    def _on_close(self):
        """Maneja el cierre de la aplicación"""
        if messagebox.askyesno("Salir", "¿Deseas cerrar Link-Chat?"):
            self._shutdown_network()
            self.destroy()


def main():
    """Función principal para ejecutar la GUI"""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

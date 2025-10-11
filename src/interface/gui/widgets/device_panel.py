"""
Panel de dispositivos descubiertos para la GUI de Link-Chat
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Callable, Optional


class DevicePanel(ttk.Frame):
    """Panel que muestra la lista de dispositivos descubiertos"""
    
    def __init__(self, parent, on_device_select: Optional[Callable] = None):
        """
        Inicializa el panel de dispositivos
        
        Args:
            parent: Widget padre de Tkinter
            on_device_select: Callback cuando se selecciona un dispositivo
        """
        super().__init__(parent)
        self.on_device_select = on_device_select
        self.devices = {}  # mac -> info
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crea los widgets del panel"""
        # Título
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            title_frame,
            text="📱 Dispositivos Descubiertos",
            font=('Arial', 12, 'bold')
        ).pack(side=tk.LEFT)
        
        self.device_count_label = ttk.Label(
            title_frame,
            text="0 dispositivos",
            font=('Arial', 9)
        )
        self.device_count_label.pack(side=tk.RIGHT)
        
        # Frame para Treeview y scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview para lista de dispositivos
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('mac', 'status', 'last_seen'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        
        # Configurar columnas
        self.tree.heading('mac', text='Dirección MAC')
        self.tree.heading('status', text='Estado')
        self.tree.heading('last_seen', text='Última vez visto')
        
        self.tree.column('mac', width=150)
        self.tree.column('status', width=80)
        self.tree.column('last_seen', width=120)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Bind para doble click
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # Frame para botones
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            button_frame,
            text="💬 Enviar Mensaje",
            command=self._send_message_to_selected
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="📁 Enviar Archivo",
            command=self._send_file_to_selected
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="🔄 Refrescar",
            command=self._refresh_list
        ).pack(side=tk.RIGHT, padx=2)
    
    def add_device(self, mac: str, info: Dict):
        """
        Agrega o actualiza un dispositivo en la lista
        
        Args:
            mac: Dirección MAC del dispositivo
            info: Información del dispositivo
        """
        self.devices[mac] = info
        
        # Buscar si ya existe en el tree
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == mac:
                # Actualizar existente
                status = "🟢 Activo" if info.get('active', False) else "🔴 Inactivo"
                last_seen = info.get('last_seen', 'Desconocido')
                self.tree.item(item, values=(mac, status, last_seen))
                return
        
        # Agregar nuevo
        status = "🟢 Activo" if info.get('active', True) else "🔴 Inactivo"
        last_seen = info.get('last_seen', 'Ahora')
        self.tree.insert('', tk.END, values=(mac, status, last_seen))
        
        self._update_count()
    
    def remove_device(self, mac: str):
        """
        Elimina un dispositivo de la lista
        
        Args:
            mac: Dirección MAC del dispositivo
        """
        if mac in self.devices:
            del self.devices[mac]
        
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == mac:
                self.tree.delete(item)
                break
        
        self._update_count()
    
    def update_device_status(self, mac: str, active: bool):
        """
        Actualiza el estado de un dispositivo
        
        Args:
            mac: Dirección MAC del dispositivo
            active: Si el dispositivo está activo
        """
        if mac in self.devices:
            self.devices[mac]['active'] = active
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == mac:
                status = "🟢 Activo" if active else "🔴 Inactivo"
                self.tree.item(item, values=(values[0], status, values[2]))
                break
    
    def get_selected_device(self) -> Optional[str]:
        """
        Obtiene la MAC del dispositivo seleccionado
        
        Returns:
            MAC del dispositivo o None
        """
        selection = self.tree.selection()
        if selection:
            values = self.tree.item(selection[0])['values']
            return values[0]  # MAC está en primera columna
        return None
    
    def _update_count(self):
        """Actualiza el contador de dispositivos"""
        count = len(self.devices)
        self.device_count_label.config(
            text=f"{count} dispositivo{'s' if count != 1 else ''}"
        )
    
    def _on_double_click(self, event):
        """Maneja doble click en un dispositivo"""
        mac = self.get_selected_device()
        if mac and self.on_device_select:
            self.on_device_select(mac)
    
    def _send_message_to_selected(self):
        """Envía mensaje al dispositivo seleccionado"""
        mac = self.get_selected_device()
        if mac and self.on_device_select:
            self.on_device_select(mac)
        elif not mac:
            messagebox.showwarning(
                "Sin selección",
                "Por favor seleccione un dispositivo primero"
            )
    
    def _send_file_to_selected(self):
        """Envía archivo al dispositivo seleccionado"""
        mac = self.get_selected_device()
        if not mac:
            messagebox.showwarning(
                "Sin selección",
                "Por favor seleccione un dispositivo primero"
            )
        # TODO: Implementar diálogo de selección de archivo
    
    def _refresh_list(self):
        """Refresca la lista de dispositivos"""
        # La lista se actualiza automáticamente vía Observer
        pass
    
    def clear(self):
        """Limpia la lista de dispositivos"""
        self.devices.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._update_count()

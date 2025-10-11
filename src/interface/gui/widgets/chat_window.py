"""
Ventana de chat para enviar y recibir mensajes
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Callable, Optional
import asyncio
from src.DTOS.message import Message


class ChatWindow(tk.Toplevel):
    """Ventana de chat para comunicación con un dispositivo"""
    
    def __init__(self, parent, target_mac: str, message_service, local_mac: str):
        """
        Inicializa la ventana de chat
        
        Args:
            parent: Ventana padre
            target_mac: MAC del dispositivo destino
            message_service: Servicio de mensajería
            local_mac: MAC local
        """
        super().__init__(parent)
        
        self.target_mac = target_mac
        self.message_service = message_service
        self.local_mac = local_mac
        
        self.title(f"Chat con {target_mac}")
        self.geometry("500x600")
        
        self._create_widgets()
        
        # Configurar ventana
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """Crea los widgets de la ventana"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            header_frame,
            text=f"💬 Chat con:",
            font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text=self.target_mac,
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Área de chat
        chat_frame = ttk.Frame(self)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(
            chat_frame,
            text="Historial de mensajes:",
            font=('Arial', 9)
        ).pack(anchor=tk.W)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=50,
            height=20,
            state=tk.DISABLED,
            font=('Arial', 10)
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configurar tags para estilos
        self.chat_display.tag_config('sent', foreground='blue')
        self.chat_display.tag_config('received', foreground='green')
        self.chat_display.tag_config('system', foreground='gray', font=('Arial', 9, 'italic'))
        
        # Área de entrada
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            input_frame,
            text="Escribir mensaje:",
            font=('Arial', 9)
        ).pack(anchor=tk.W)
        
        # Frame para entry y botón
        entry_frame = ttk.Frame(input_frame)
        entry_frame.pack(fill=tk.X, pady=5)
        
        self.message_entry = ttk.Entry(entry_frame, font=('Arial', 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind('<Return>', lambda e: self._send_message())
        
        self.send_button = ttk.Button(
            entry_frame,
            text="📤 Enviar",
            command=self._send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        # Barra de estado
        self.status_label = ttk.Label(
            self,
            text="Listo para enviar mensajes",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Mensaje inicial
        self._add_system_message("Ventana de chat iniciada")
    
    def _send_message(self):
        """Envía un mensaje al dispositivo destino"""
        message_text = self.message_entry.get().strip()
        
        if not message_text:
            return
        
        # Deshabilitar entrada mientras se envía
        self.message_entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.status_label.config(text="Enviando mensaje...")
        
        # Mostrar mensaje enviado
        self._add_message(f"Tú: {message_text}", 'sent')
        self.message_entry.delete(0, tk.END)
        
        # Enviar mensaje (async)
        self._async_send(message_text)
    
    def _async_send(self, message_text: str):
        """
        Envía mensaje de forma asíncrona
        
        Args:
            message_text: Texto del mensaje a enviar
        """
        async def send():
            try:
                success = await self.message_service.send_message(
                    self.target_mac,
                    message_text
                )
                
                # Actualizar UI en thread principal
                self.after(0, lambda: self._send_complete(success))
            except Exception as e:
                self.after(0, lambda: self._send_error(str(e)))
        
        # Ejecutar en el event loop
        try:
            asyncio.create_task(send())
        except RuntimeError:
            # Si no hay event loop, crear uno
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send())
    
    def _send_complete(self, success: bool):
        """
        Callback cuando se completa el envío
        
        Args:
            success: Si el envío fue exitoso
        """
        if success:
            self.status_label.config(text="Mensaje enviado ✓")
        else:
            self.status_label.config(text="Error enviando mensaje ✗")
            self._add_system_message("⚠️ No se pudo enviar el mensaje")
        
        # Rehabilitar entrada
        self.message_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.message_entry.focus()
    
    def _send_error(self, error: str):
        """
        Maneja errores de envío
        
        Args:
            error: Mensaje de error
        """
        self.status_label.config(text=f"Error: {error}")
        self._add_system_message(f"⚠️ Error: {error}")
        
        # Rehabilitar entrada
        self.message_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
    
    def receive_message(self, message: Message):
        """
        Recibe un mensaje (llamado desde el controlador)
        
        Args:
            message: Objeto Message recibido
        """
        if message.sender_mac == self.target_mac:
            self._add_message(f"{self.target_mac}: {message.text}", 'received')
            self.status_label.config(text="Nuevo mensaje recibido")
            
            # Flash de la ventana si no está enfocada
            if not self.focus_get():
                self.bell()
    
    def _add_message(self, text: str, tag: str = None):
        """
        Agrega un mensaje al display
        
        Args:
            text: Texto del mensaje
            tag: Tag de estilo ('sent', 'received', 'system')
        """
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text + '\n', tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def _add_system_message(self, text: str):
        """
        Agrega un mensaje del sistema
        
        Args:
            text: Texto del mensaje
        """
        self._add_message(f"[{text}]", 'system')
    
    def _on_close(self):
        """Maneja el cierre de la ventana"""
        self.destroy()

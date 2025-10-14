
import socket
import threading
from typing import List

from .frame import LinkChatFrame
from ..observer.subject import Subject
from ..observer.observer import Observer
from ..utils.constants import ETHERTYPE_LINKCHAT,BUFFER_SIZE
from ..utils.helpers import format_mac_address
class raw_socket_manager(Subject[LinkChatFrame]):
    """
    A wrapper class for a raw socket to send and receive LinkChatFrame objects.

    This class handles the creation, binding, and usage of a raw socket
    at the link layer (Ethernet). It requires root privileges to run.
    It is designed to be thread-safe.
    """

    def __init__(self, interface_name: str):
        """
        Initializes the raw socket, binds it to the interface, and prepares for concurrent access.

        Args:
            interface_name: The name of the network interface to use (e.g., 'eth0').

        Raises:
            PermissionError: If the script is not run with sufficient privileges.
            OSError: If the interface does not exist or another network error occurs.
        """
        try:
            # Create a raw socket that listens for our custom EtherType
            self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_LINKCHAT))
            self.sock.bind((interface_name, 0))
        except (PermissionError, OSError) as e:
            print(f"Error creating or binding socket: {e}")
            print("This operation typically requires root privileges (e.g., 'sudo python your_script.py')")
            raise

        self._self_mac = format_mac_address(self.sock.getsockname()[4])
        self._observers: List[Observer[LinkChatFrame]] = []
        self._observer_lock = threading.Lock()

        self._is_receiving = False
        self._receive_thread: threading.Thread = None
        self.interface = interface_name

    def send_frame(self, frame_to_send: LinkChatFrame) -> bool:
        """
        Sends a LinkChatFrame over the raw socket.

        Args:
            frame_to_send: The LinkChatFrame object to be sent.

        Returns:
            True if sending was successful, False otherwise.
        """
        try:
            packed_frame = frame_to_send.to_bytes()
            self.sock.send(packed_frame)
            return True
        except socket.error as e:
            print(f"Failed to send frame: {e}")
            return False

    def receive_frames(self) -> None:
        """
        The target method for the receiving thread.
        Listens for incoming packets, unpacks them, and notifies observers.
        This method will block until the socket is closed.
        """
        while self._is_receiving:
            try:
                raw_packet, _ = self.sock.recvfrom(BUFFER_SIZE)
                if raw_packet and self._is_receiving:
                    received_frame = LinkChatFrame.from_bytes(raw_packet)
                    self.notify(received_frame)
            except socket.error:
                # An error (e.g., socket closed) will break the loop
                break

    def close_socket(self):
        """Closes the socket if it is open."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def start_receiving(self) -> None:
        """Starts the frame receiving thread if it's not already running."""
        if not self._is_receiving:
            self._is_receiving = True
            self._receive_thread = threading.Thread(target=self.receive_frames, daemon=True)
            self._receive_thread.start()

    def stop_receiving(self) -> None:
        """Stops the frame receiving thread gracefully."""
        if self._is_receiving:
            self._is_receiving = False
            self.close_socket()  # Unblocks the blocking recvfrom call
            if self._receive_thread and self._receive_thread.is_alive():
                self._receive_thread.join()  # Wait for the thread to finish
            self._receive_thread = None

    def get_local_mac(self) -> str:
        """Returns the MAC address of the interface this socket is bound to."""
        return self._self_mac

    def attach(self, observer: Observer[LinkChatFrame]) -> None:
        """
        Attaches an observer to the subject in a thread-safe manner.

        Args:
            observer: The observer object to attach.
        """
        with self._observer_lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def notify(self, message: LinkChatFrame) -> None:
        """
        Notifies all attached observers with a message in a thread-safe manner.

        Args:
            message: The LinkChatFrame message to send to observers.
        """
        with self._observer_lock:
            # Iterate over a copy of the list to allow observers to detach during notification
            observers_copy = self._observers[:]

        for observer in observers_copy:
            observer.update(message)

    def detach(self, observer: Observer[LinkChatFrame]) -> None:
        """
        Detaches an observer from the subject in a thread-safe manner.

        Args:
            observer: The observer object to detach.
        """
        with self._observer_lock:
            try:
                self._observers.remove(observer)
            except ValueError:
                pass  # Observer not in list, do nothing
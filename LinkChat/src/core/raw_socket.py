import socket
import struct
import threading
from typing import Dict, Optional,Callable,str

# Assuming the provided LinkChatFrame class is in a file named 'frame.py'
from frame import LinkChatFrame 
from utils.constants import ETHERTYPE_LINKCHAT

# Constants
BUFFER_SIZE = 65536  # Max possible size for an IP packet, good for capturing full frames

class raw_socket_wrapper:
    """
    A wrapper class for a raw socket to send and receive LinkChatFrame objects.
    
    This class handles the creation, binding, and usage of a raw socket
    at the link layer (Ethernet). It requires root privileges to run.
    """
    callbacks: Dict[str, Callable] = {}
    
    def __init__(self, interface_name: str):
        """
        Initializes and binds the raw socket to a specific network interface.
        
        Args:
            interface_name (str): The name of the network interface to use (e.g., 'eth0', 'enp3s0').
            
        Raises:
            PermissionError: If the script is not run with sufficient privileges (e.g., as root).
            OSError: If the network interface does not exist or another network-related error occurs.
        """
        self.interface_name = interface_name
        self.sock = None
        try:
            # Create a raw socket that can read all incoming packets (ETH_P_ALL)
            # AF_PACKET allows communication at the device driver level (OSI Layer 2)
            # SOCK_RAW gives us the raw packets including the link-layer header
            # socket.nhtons(ETHERTYPE_LINKCHAT) its for using our protocol
            self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETHERTYPE_LINKCHAT))
            
            # Bind the socket to the specified network interface
            self.sock.bind((self.interface_name, 0))
            print(f"Socket successfully created and bound to interface '{self.interface_name}'")

        except PermissionError:
            print(f"Error: Permission denied to create raw socket. Try running with 'sudo'.")
            raise
        except OSError as e:
            print(f"Error binding to interface '{self.interface_name}': {e}")
            raise

    def send_frame(self, frame_to_send: LinkChatFrame) -> bool:
        """
        Sends a LinkChatFrame over the raw socket.
        
        Args:
            frame_to_send (LinkChatFrame): The frame object to be sent.
            
        Returns:
            bool: True if the frame was sent successfully, False otherwise.
        """
        if not self.sock:
            print("Error: Socket is not initialized.")
            return False
            
        try:
            # Convert the frame object to its byte representation
            frame_bytes = frame_to_send.to_bytes()
            
            # Send the raw bytes through the socket
            self.sock.send(frame_bytes)
            # print(f"Sent frame: {frame_to_send}")
            return True
            
        except OSError as e:
            print(f"Error sending frame: {e}")
            return False

    def receive_frames(self) -> None:
        """
        Receives and parses a LinkChatFrames from the raw socket.
        
        This method listens for incoming packets and attempts to parse them
        as LinkChatFrame objects. It will ignore any packets that do not
        match the LinkChat protocol (e.g., wrong EtherType, bad checksum).
        
        This is a blocking call.
        
        Returns:
            None
        """
        if not self.sock:
            print("Error: Socket is not initialized.")
            return None

        while True:
            try:
                # Receive raw data from the socket.
                # recvfrom returns (bytes, address_info)
                # For AF_PACKET, address_info includes protocol, packet type, etc.
                raw_data, _ = self.sock.recvfrom(BUFFER_SIZE)
                
                # Check if the EtherType matches our protocol before full parsing
                # This is a quick filter to avoid unnecessary processing
                # EtherType is located at bytes 12 and 13
                if len(raw_data) >= 14:
                    ethertype, = struct.unpack('!H', raw_data[12:14])
                    if ethertype != ETHERTYPE_LINKCHAT:
                        continue # Not our protocol, ignore and wait for the next packet
                else:
                    continue # Packet is too short, ignore
                
                # Attempt to parse the raw data into a LinkChatFrame
                # The from_bytes method handles all validation (size, checksum, etc.)
                frame = LinkChatFrame.from_bytes(raw_data)
                
                if frame:
                    # A valid frame for our protocol was found
                    print(f"Received frame: {frame}")
                    # If frame is None, it means the packet was for our EtherType
                # but failed validation (e.g., bad checksum). Loop to get the next one.
                    
            except OSError as e:
                print(f"Error receiving frame: {e}")
                return None
            except Exception as e:
                print(f"An unexpected error occurred during frame reception: {e}")
                return None
                
    def close_socket(self):
        """
        Closes the raw socket.
        """
        if self.sock:
            print("Closing socket.")
            self.sock.close()
            self.sock = None
    
    def start_reciving(self)->None:
        """
        Starts a thread to receive frames in the background.
        
        Returns:
            None
        
        """
        self.is_running = True
        self.receive_thread = threading.Thread(target=self.receive_frames,deamon=True)
        self.receive_thread.start()

    def stop_reciving(self)->None:
        """
        Stops the receiving thread.
        """
        self.receive_thread.join()
    """
    Registers a callback.
    """
    def register_callback(self,name:str,callback:Callable)->None:
        self.callbacks[name] = callback
    """
    Unregisters a callback.
    """
    def unregister_callback(self,name:str)->None:
        self.callbacks.pop(name,None)
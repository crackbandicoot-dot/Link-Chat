class Message:
    """Representa un mensaje en el sistema"""
    
    def __init__(self, msg_id: int, sender_mac: str, target_mac: str, content: str, 
                 timestamp: int, is_broadcast: bool = False):
        self.msg_id = msg_id
        self.sender_mac = sender_mac
        self.target_mac = target_mac
        self.content = content
        self.timestamp = timestamp
        self.is_broadcast = is_broadcast
        self.acknowledged = False
        self.retry_count = 0

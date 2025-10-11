

class Message:
    def __init__(self, text: str, sender_mac: str):
        self._text = text
        self._sender_mac = sender_mac
    
    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def sender_mac(self):
        return self._sender_mac
    
    @sender_mac.setter
    def sender_mac(self, value: str):
        self._sender_mac = value

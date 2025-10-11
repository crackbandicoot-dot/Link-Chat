

class Message:
    def __init__(self,text:str,sender_mac:str):
        self.sender_mac = sender_mac
        self.text = text
        pass
    @property
    def text(self):
        return  self.text

    @text.setter
    def  text(self,value):
        self.text=value

    @property
    def sender_mac(self):
        return self.sender_mac
    @property.setter
    def sender_mac(self,value:str):
        self.sender_mac =value

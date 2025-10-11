
class FileInfo:

    def __init__(self,name:str):
        self.name=name
        pass
    @property
    def name(self):
        return  self.name
    @property.setter
    def name(self,value):
        self.name=value
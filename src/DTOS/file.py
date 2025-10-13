class FileInfo:
    def __init__(self, name: str,id:int):
        self._name = name
        self.id =id

    @property
    def name(self)->str:
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
    @property
    def id(self):
        return self.id
    def id(self,value):
        self.id = value
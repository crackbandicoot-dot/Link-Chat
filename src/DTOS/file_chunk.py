from .file_info import FileInfo
class FileChunk:
    def __init__(self,file_info:FileInfo,chunk :bytes):
        self.file_info = file_info
    
    @property
    def file_info(self)->FileInfo:
        self.file_info
    
    @file_info.setter
    def file_info(self,value):
        self.file_info = value

    @property
    def chunk(self)->bytes:
        return self.chunk
    
    @chunk.setter
    def chunk(self,value):
        self.chunk=value
    
    
    
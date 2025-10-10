from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class Observer(Generic[T], ABC):
    """
    Interface for Observer pattern - defines objects that observe Subjects
    
    Type parameter T specifies the type of data that this observer handles.
    Examples:
    - Observer[Dict] for device discovery notifications
    - Observer[LinkChatFrame] for network frame notifications
    - Observer[Message] for chat message notifications
    """
    
    @abstractmethod
    def update(self, data: T) -> None:
        """
        Called when the observed Subject notifies its observers
        
        Args:
            data: The notification data of type T
        """
        pass



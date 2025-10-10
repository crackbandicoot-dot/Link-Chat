from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from .observer import Observer

T = TypeVar('T')

class Subject(Generic[T], ABC):
    """
    Interface for Observer pattern - defines objects that can be observed
    
    Type parameter T specifies the type of data that this subject notifies with.
    """
    
    @abstractmethod
    def attach(self, observer: Observer[T]) -> None:
        """
        Register an observer to receive notifications
        
        Args:
            observer: Observer that will receive notifications of type T
        """
        pass

    @abstractmethod
    def detach(self, observer: Observer[T]) -> None:
        """
        Remove an observer from notifications
        
        Args:
            observer: Observer to remove
        """
        pass

    @abstractmethod
    def notify(self, notification: T) -> None:
        """
        Notify all registered observers with data
        
        Args:
            notification: Data to send to observers of type T
        """
        pass

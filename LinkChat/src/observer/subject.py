from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from observer import Observer

# Generic type for the data
T = TypeVar('T')
# Subject interface
class Subject(Generic[T], ABC):
    @abstractmethod
    def attach(self, observer: Observer[T]) -> None:
        pass

    @abstractmethod
    def detach(self, observer: Observer[T]) -> None:
        pass

    @abstractmethod
    def notify(self,notification:T) -> None:
        pass

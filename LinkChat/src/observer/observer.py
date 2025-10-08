from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')
# Observer interface
class Observer(Generic[T],ABC):
    @abstractmethod
    def update(self, data: T) -> None:
        pass

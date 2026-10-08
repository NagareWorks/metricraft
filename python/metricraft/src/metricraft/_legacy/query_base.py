"""Abstract build contract for historical regression fixtures."""
from abc import ABC, abstractmethod


class QueryBuilder(ABC):
    @abstractmethod
    def build(self) -> str:
        raise NotImplementedError

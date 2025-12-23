from abc import ABC, abstractmethod
from typing import List
from fie.core.transaction import Transaction


class TransactionStore(ABC):

    @abstractmethod
    def add(self, txns: List[Transaction]) -> None:
        pass

    @abstractmethod
    def update(self, txns: List[Transaction]) -> None:
        pass

    @abstractmethod
    def list_all(self) -> List[Transaction]:
        pass

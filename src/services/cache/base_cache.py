from abc import ABC, abstractmethod


class BaseCache(ABC):
    @abstractmethod
    def store(self):
        pass

    @abstractmethod
    def retrieve(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def set_expiration(self):
        pass

    @abstractmethod
    def update(self):
        pass

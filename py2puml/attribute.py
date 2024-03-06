
from abc import ABC, abstractmethod


class Attribute(ABC):

    def __init__(self, name, type_expr=None):
        self.name = name
        self.type_expr = type_expr

    def __eq__(self, other):
        if isinstance(other, Attribute):
            return self.name == other.name and self.type_expr == other.type_expr
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return f"{type(self).__name__}(name='{self.name}')"

    @property
    @abstractmethod
    def as_puml(self):
        pass


class ClassAttribute(Attribute):

    @property
    def as_puml(self):
        if self.type_expr:
            return f'{self.name}: {self.type_expr} {{static}}'
        else:
            return f'{self.name} {{static}}'


class InstanceAttribute(Attribute):

    @property
    def as_puml(self):
        if self.type_expr:
            return f'{self.name}: {self.type_expr}'
        else:
            return f'{self.name}'

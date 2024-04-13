from dataclasses import dataclass, field
from typing import Dict, List

from py2puml.domain.umlitem import UmlItem
import re

def uml_visibility(uml_attr_name:str):
    if re.search("^__", uml_attr_name):
        return '-'
    
    if re.search("^_", uml_attr_name):
        return '#'
    
    return "+"

@dataclass
class UmlAttribute:
    name: str
    type: str
    static: bool


@dataclass
class UmlMethod:
    name: str
    arguments: Dict = field(default_factory=dict)
    is_static: bool = False
    is_class: bool = False
    return_type: str = None

    def represent_as_puml(self):
        items = []
        items.append( uml_visibility(self.name))
        if self.is_static:
            items.append('{static}')
        if self.return_type:
            items.append(self.return_type)
        items.append(f'{self.name}({self.signature})')
        return ' '.join(items)

    @property
    def signature(self):
        if self.arguments:
            return ', '.join(
                [
                    f'{arg_type} {arg_name}' if arg_type else f'{arg_name}'
                    for arg_name, arg_type in self.arguments.items()
                ]
            )
        return ''


@dataclass
class UmlClass(UmlItem):
    attributes: List[UmlAttribute]
    methods: List[UmlMethod]
    is_abstract: bool = False

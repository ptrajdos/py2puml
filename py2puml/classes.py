from __future__ import annotations


from ast import NodeVisitor, Assign, AnnAssign, ClassDef, FunctionDef, Name, Attribute
from dataclasses import dataclass, field
from typing import List, Dict

from py2puml.methods import Method, TypeVisitor, MethodVisitor, DecoratorVisitor, ConstructorVisitor
from py2puml.attribute import InstanceAttribute, ClassAttribute


@dataclass
class PythonClass:
    """ Class that represents a Python class

    Args:
        name
        fully_qualified_name
        attributes
        methods
        base_classes (dict): dictionary which key is the partially qualified name of a base class and value is the
        corresponding base class object that the class inherits from.
        module (PythonModule): the Python module that the class belongs to
    """
    name: str
    fully_qualified_name: str
    attributes: List = field(default_factory=list)
    methods: List = field(default_factory=list)
    base_classes: Dict[str, PythonClass] = field(default_factory=dict)
    module = None

    @classmethod
    def from_type(cls, class_type):
        """ Alternate class constructor from a class type object

        In case the class is declared in a __init__.py module the class is said to belong to the parent package. Hence the __init__ module is omitted from the fully qualified name of the class.

        Args:
            class_type (type): the class type object """

        name = class_type.__name__

        parent_fully_qualified_name = class_type.__module__
        if parent_fully_qualified_name.endswith('__init__'):
            fully_qualified_name = '.'.join([class_type.__module__[:-9], name])
        else:
            fully_qualified_name = '.'.join([class_type.__module__, name])

        return PythonClass(name=name, fully_qualified_name=fully_qualified_name)

    @property
    def as_puml(self):
        lines = [f'class {self.fully_qualified_name} {{']
        for attribute in self.attributes:
            lines.append(f'  {attribute.as_puml}')
        for method in self.methods:
            lines.append(f'  {method.as_puml}')
        lines.append('}\n')

        return '\n'.join(lines)


class ClassVisitor(NodeVisitor):

    def __init__(self, class_type, root_fqn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_type = class_type
        self.root_fqn = root_fqn
        self.class_name: str = None
        self.attributes = []
        self.methods: List[Method] = []
        self.parent_classes_pqn = []
        self.decorators = []
        self.is_dataclass = False

    def visit_Assign(self, node: Assign):
        """ Retrieve class attribute """
        for target in node.targets:
            if self.is_dataclass:
                attribute = InstanceAttribute(name=target.id)
            else:
                attribute = ClassAttribute(name=target.id)
            self.attributes.append(attribute)

    def visit_AnnAssign(self, node: AnnAssign):
        """ Retrieve annotated class attribute """
        type_visitor = TypeVisitor()
        _type = type_visitor.visit(node.annotation)
        if self.is_dataclass:
            attribute = InstanceAttribute(name=node.target.id, type_expr=_type)
        else:
            attribute = ClassAttribute(name=node.target.id, type_expr=_type)
        self.attributes.append(attribute)

    def visit_ClassDef(self, node: ClassDef):
        """ Retrieve name of the class and base class if any """
        self.class_name = node.name
        if node.bases:
            for base in node.bases:
                base_visitor = BaseClassVisitor()
                base_visitor.visit(base)
                self.parent_classes_pqn.append(base_visitor.qualified_name)

        if node.decorator_list:
            for decorator_node in node.decorator_list:
                visitor = DecoratorVisitor()
                visitor.visit(decorator_node)
                self.decorators.append(visitor.decorator_type)
                if visitor.decorator_type == 'dataclass':
                    self.is_dataclass = True

        self.generic_visit(node)

    def visit_FunctionDef(self, node: FunctionDef):
        method_visitor = MethodVisitor()
        method_visitor.visit(node)
        method = method_visitor.method
        if method.is_getter:
            attribute = InstanceAttribute(name=method.name, type_expr=method.return_type)
            self.attributes.append(attribute)
        else:
            self.methods.append(method)

        if node.name == '__init__' and True:
            constructor_visitor = ConstructorVisitor()
            constructor_visitor.visit(node)
            for attribute in constructor_visitor.instance_attributes.values():
                self.attributes.append(attribute)


class BaseClassVisitor(NodeVisitor):

    """ Node Visitor class for base class definition

     This visitor is used for walking 'base' field of class definition node ClassDef. The name of the base class is
     returned by the class property 'qualified_name'. Handles partially defined base class name, e.g. the class
     definition 'class DerivedClassName(modname.BaseClassName):' will return 'modname.BaseClassName' as
     'qualified_name'.

     """

    def __init__(self):
        """ Class constructor

        Elements of the qualified name are collected in a list """
        self.elements = []

    def visit_Name(self, node: Name):
        self.elements.append(node.id)

    def visit_Attribute(self, node: Attribute):
        """ Recursive call with 'generic_visit' so that Attributes are traversed """
        self.generic_visit(node)
        self.elements.append(node.attr)

    @property
    def qualified_name(self):
        return '.'.join(self.elements)

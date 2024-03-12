import ast
from typing import Dict, List, Tuple
from ast import (
    NodeVisitor, arg,
    FunctionDef, Assign, AnnAssign,
    Attribute, Name, Subscript
)
from collections import namedtuple
from dataclasses import dataclass, field

from py2puml.attribute import InstanceAttribute

Variable = namedtuple('Argument', ['id', 'type_expr'])


@dataclass
class Argument:
    name: str
    type_expr: str
    datatype = None


@dataclass
class Method:
    name: str
    arguments: Dict = field(default_factory=dict)
    is_static: bool = False
    is_class: bool = False
    is_getter: bool = False
    return_type: str = None

    @property
    def as_puml(self):
        items = []
        if self.is_static:
            items.append('{static}')
        if self.return_type:
            items.append(self.return_type)
        items.append(f'{self.name}({self.signature})')
        return ' '.join(items)

    @property
    def signature(self):
        if self.arguments:
            return ', '.join([f'{arg_type} {arg_name}' if arg_type else f'{arg_name}' for arg_name, arg_type in
                              self.arguments.items()])
        return ''


class SignatureVariablesCollector(NodeVisitor):
    """
    Collects the arguments name and type annotations from the signature of a method
    """
    def __init__(self, skip_self=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_self = skip_self
        self.class_self_id: str = None
        self.variables: List[Variable] = []
        self.datatypes = {}

    def visit_arg(self, node: arg):
        variable = Variable(node.arg, node.annotation)
        if node.annotation:
            type_visitor = TypeVisitor()
            datatype = type_visitor.visit(node.annotation)
        else:
            datatype = None
        self.datatypes[node.arg] = datatype
        # first constructor argument is the name for the 'self' reference
        if self.class_self_id is None and not self.skip_self:
            self.class_self_id = variable.id
        # other arguments are constructor parameters
        self.variables.append(variable)


class DecoratorVisitor(NodeVisitor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.elements = []

    def visit_Name(self, node: Name):
        self.elements.append(node.id)

    def visit_Attribute(self, node: Attribute):
        """ Recursive call with 'generic_visit' so that Attributes are traversed """
        self.generic_visit(node)
        self.elements.append(node.attr)

    @property
    def decorator_type(self):
        return '.'.join(self.elements)


class TypeVisitor(NodeVisitor):
    """ Returns a string representation of a data type. Supports nested compound data types """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visit_Attribute(self, node: Attribute):
        return node.attr

    def visit_Name(self, node):
        return node.id

    def visit_Constant(self, node):
        return node.value

    def visit_Subscript(self, node: Subscript):
        """ Visit node of type ast.Subscript and returns a string representation of the compound datatype. Iterate
        over elements contained in slice attribute by calling recursively visit() method of new instances of
        TypeVisitor. This allows to resolve nested compound datatype. """
        datatypes = []

        if hasattr(node.slice.value, 'elts'):
            for child_node in node.slice.value.elts:
                child_visitor = TypeVisitor()
                datatypes.append(child_visitor.visit(child_node))
        else:
            child_visitor = TypeVisitor()
            datatypes.append(child_visitor.visit(node.slice.value))

        joined_datatypes = ', '.join(datatypes)

        return f'{node.value.id}[{joined_datatypes}]'


class MethodVisitor(NodeVisitor):
    """
    Node visitor subclass used to walk the abstract syntax tree of a method class and identify method arguments.

    If the method is the class constructor, instance attributes (and their type) are also identified by looking both
    at the constructor signature and constructor's body. When searching in the constructor's body, the visitor looks
    for relevant assignments (with and without type annotation).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variables_namespace: List[Variable] = []
        self.method: Method
        self.decorators = []

    def visit_FunctionDef(self, node: FunctionDef):

        for decorator_node in node.decorator_list:
            decorator_visitor = DecoratorVisitor()
            decorator_visitor.visit(decorator_node)
            if decorator_visitor.decorator_type:
                self.decorators.append(decorator_visitor.decorator_type)

        is_static = 'staticmethod' in self.decorators
        is_class = 'classmethod' in self.decorators
        is_getter = 'property' in self.decorators
        arguments_collector = SignatureVariablesCollector(skip_self=is_static)
        arguments_collector.visit(node)
        self.variables_namespace = arguments_collector.variables

        self.method = Method(name=node.name, is_static=is_static, is_class=is_class, is_getter=is_getter)

        for argument in arguments_collector.variables:
            if argument.id == arguments_collector.class_self_id:
                self.method.arguments[argument.id] = None
            if argument.type_expr:
                if hasattr(argument.type_expr, 'id'):
                    self.method.arguments[argument.id] = argument.type_expr.id
                else:

                    self.method.arguments[argument.id] = arguments_collector.datatypes[argument.id]
            else:
                self.method.arguments[argument.id] = None

        if node.returns is not None:
            return_visitor = TypeVisitor()
            self.method.return_type = return_visitor.visit(node.returns)


class ConstructorVisitor(NodeVisitor):
    """ Node visitor subclass used to walk the abstract syntax tree of a class constructor.

     The constructor's signature is used to identify the type of the arguments when these are annotated.

     In the constructor's body, assignments where the target is an instance attribute are used to identify the class'
     instance attributes. Their type is simply inferred from the assignment if this one is annotated, otherwise from
     the type of variable in the assignment's value (part on the right-hand side of the equal operator) if it is an
     argument found in the constructor's method signature.

     Attributes:
         name (str): name of the constructor method.
         arguments (list): list of :class:`Argument` objects
         instance_attributes (list): list of :class:`InstanceAttribute` objects
     """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name: str = None
        self.arguments: List[Argument] = []
        self.instance_attributes: Dict[InstanceAttribute] = {}

    def visit_FunctionDef(self, node: FunctionDef):
        self.name = node.name
        self.generic_visit(node)

    def visit_arg(self, node: arg):
        type_expr = None
        if node.annotation:
            type_visitor = TypeVisitor()
            type_expr = type_visitor.visit(node.annotation)
        if not node.arg == 'self':  # FIXME: add support for other instance name than 'self'
            argument = Argument(name=node.arg, type_expr=type_expr)
            self.arguments.append(argument)

    def visit_Assign(self, node: Assign):
        assignment_visitor = AssignmentVisitor()
        assignment_visitor.visit(node)

        if assignment_visitor.attribute_assignments:
            for attribute_assignment in assignment_visitor.attribute_assignments:
                instance_attribute = attribute_assignment.instance_attribute

                type_expr = None
                for argument in self.arguments:
                    if argument.name in attribute_assignment.variable_names:
                        type_expr = argument.type_expr
                        break
                instance_attribute.type_expr = type_expr

                self.instance_attributes[instance_attribute.name] = instance_attribute

    def visit_AnnAssign(self, node: AnnAssign):
        assignment_visitor = AssignmentVisitor()
        assignment_visitor.visit(node)

        if assignment_visitor.attribute_assignments:
            instance_attribute = assignment_visitor.attribute_assignments[0].instance_attribute

            type_visitor = TypeVisitor()
            type_expr = type_visitor.visit(node.annotation)
            instance_attribute.type_expr = type_expr

            self.instance_attributes[instance_attribute.name] = instance_attribute


class AssignmentVisitor(NodeVisitor):
    """ Node visitor subclass used to walk the abstract syntax tree of an assignment, annotated or not. It supports
    multiple assignment on single line.

    Attributes:
        attribute_assignments (list): list of :class:`AttributeAssignment` objects.
        _index (int): index used when parsing multiple assignments (Tuple).
        _visiting_target (bool): True when visiting the left-hand side of the equal sign, False otherwise.
        _visiting_value (bool): True when visiting the right-hand side of the equal sign, False otherwise.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(* args, **kwargs)
        self.attribute_assignments: List[AttributeAssignment] = []
        self._index = 0
        self._visiting_target = False
        self._visiting_value = False
        self._attr_indexes = []

    def visit_AnnAssign(self, node: AnnAssign):
        self._visiting_target = True
        self.visit(node.target)
        self._visiting_target = False

        type_visitor = TypeVisitor()
        type_expr = type_visitor.visit(node.annotation)
        if self.attribute_assignments:
            self.attribute_assignments[-1].instance_attribute.type_expr = type_expr

        self._visiting_value = True
        self.visit(node.value)
        self._visiting_value = False

    def visit_Assign(self, node: Assign):
        self._visiting_target = True
        self.visit(node.targets[0])
        self._visiting_target = False
        self._visiting_value = True
        self.visit(node.value)
        self._visiting_value = False

    def visit_Attribute(self, node: Attribute):
        if type(node.value) == ast.Name:
            if node.value.id == 'self':  # FIXME: add support for other instance name than 'self'
                if len(self._attr_indexes) > 0:
                    self._attr_indexes[self._index] = len(self.attribute_assignments)
                attribute = InstanceAttribute(name=node.attr)
                assignment = AttributeAssignment(instance_attribute=attribute)
                self.attribute_assignments.append(assignment)
                return

    def visit_Name(self, node: Name):
        if self._visiting_value and self.attribute_assignments:
            self.attribute_assignments[self._index].variable_names.append(node.id)

    def visit_Tuple(self, node: Tuple):
        if self._visiting_target:
            for index, element in enumerate(node.elts):
                self._attr_indexes.append(None)
                self._index = index
                self.visit(element)
        elif self._visiting_value:
            for index, element in enumerate(node.elts):
                if len(self._attr_indexes) > 0:
                    self._index = self._attr_indexes[index]
                    if self._index is not None:
                        self.visit(element)
                else:
                    self.visit(element)


@dataclass
class AttributeAssignment:
    """ Class that represent the assignment of variable(s) to an instance variable (attribute).

    Examples:
        The assignment 'self.x = a + b + 3' is represented by the variable 'attr_assign' below::

        >>> type(attr_assignment)
        <class 'AttributeAssignment'>
        >>> type(attr_assignment.instance_attribute)
        <class 'InstanceAttribute'>
        >>> attr_assignment.instance_attribute.name
        'x'
        >>> attr_assignment.variable_names
        ['a', 'b']
    """
    instance_attribute: InstanceAttribute
    variable_names: List[str] = field(default_factory=list)




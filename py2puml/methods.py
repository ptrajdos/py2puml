import ast
from typing import Dict, List, Tuple
from ast import (
    NodeVisitor, arg, ClassDef,
    FunctionDef, Assign, AnnAssign, ImportFrom,
    Attribute, Name, Subscript
)
from collections import namedtuple
from importlib import import_module
from dataclasses import dataclass, field

import py2puml.domain.umlclass as umlclass

Variable = namedtuple('Argument', ['id', 'type_expr'])


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


class ClassVisitor(NodeVisitor):

    def __init__(self, class_type, root_fqn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_type = class_type
        self.root_fqn = root_fqn
        self.class_name: str = None
        self.attributes = []
        self.methods: List[umlclass.Method] = []
        self.parent_classes_pqn = []
        self.decorators = []
        self.is_dataclass = False

    def visit_Assign(self, node: Assign):
        """ Retrieve class attribute """
        for target in node.targets:
            if self.is_dataclass:
                attribute = umlclass.InstanceAttribute(name=target.id)
            else:
                attribute = umlclass.ClassAttribute(name=target.id)
            self.attributes.append(attribute)

    def visit_AnnAssign(self, node: AnnAssign):
        """ Retrieve annotated class attribute """
        type_visitor = TypeVisitor()
        _type = type_visitor.visit(node.annotation)
        if self.is_dataclass:
            attribute = umlclass.InstanceAttribute(name=node.target.id, type_expr=_type)
        else:
            attribute = umlclass.ClassAttribute(name=node.target.id, type_expr=_type)
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
            attribute = umlclass.InstanceAttribute(name=method.name, type_expr=method.return_type)
            self.attributes.append(attribute)
        else:
            self.methods.append(method)

        if node.name == '__init__' and True:
            constructor_visitor = ConstructorVisitor()
            constructor_visitor.visit(node)
            for attribute in constructor_visitor.instance_attributes.values():
                self.attributes.append(attribute)


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
        self.method: umlclass.Method
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

        self.method = umlclass.Method(name=node.name, is_static=is_static, is_class=is_class, is_getter=is_getter)

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
        self.arguments: List[umlclass.Argument] = []
        self.instance_attributes: Dict[umlclass.InstanceAttribute] = {}

    def visit_FunctionDef(self, node: FunctionDef):
        self.name = node.name
        self.generic_visit(node)

    def visit_arg(self, node: arg):
        type_expr = None
        if node.annotation:
            type_visitor = TypeVisitor()
            type_expr = type_visitor.visit(node.annotation)
        if not node.arg == 'self':  # FIXME: add support for other instance name than 'self'
            argument = umlclass.Argument(name=node.arg, type_expr=type_expr)
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

    def visit_AnnAssign(self, node: AnnAssign):
        self._visiting_target = True
        self.visit(node.target)
        self._visiting_target = False

        type_visitor = TypeVisitor()
        type_expr = type_visitor.visit(node.annotation)
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
                attribute = umlclass.InstanceAttribute(name=node.attr)
                assignment = AttributeAssignment(instance_attribute=attribute)
                self.attribute_assignments.append(assignment)

    def visit_Name(self, node: Name):
        if self._visiting_value and self.attribute_assignments:
            self.attribute_assignments[self._index].variable_names.append(node.id)

    def visit_Tuple(self, node: Tuple):
        for index, element in enumerate(node.elts):
            self._index = index
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
    instance_attribute: umlclass.InstanceAttribute
    variable_names: List[str] = field(default_factory=list)


class ModuleVisitor(NodeVisitor):

    def __init__(self, root_fqn):
        self.classes: List[umlclass.PythonClass] = []
        self.enums = []
        self.namedtuples = []
        self.root_fqn = root_fqn
        self.imports: List[umlclass.ImportStatement] = []

    def visit_ClassDef(self, node: ClassDef):
        class_type = getattr(import_module(self.root_fqn), node.name)
        _class = umlclass.PythonClass.from_type(class_type)
        visitor = ClassVisitor(class_type, self.root_fqn)
        visitor.visit(node)
        for attribute in visitor.attributes:
            _class.attributes.append(attribute)
        for method in visitor.methods:
            _class.methods.append(method)
        for parent_class_pqn in visitor.parent_classes_pqn:
            _class.base_classes[parent_class_pqn] = None
        self.classes.append(_class)

    def visit_ImportFrom(self, node: ImportFrom):
        for name in node.names:
            import_statement = umlclass.ImportStatement(
                module_name=node.module,
                name=name.name,
                alias=name.asname,
                level=node.level
            )
            self.imports.append(import_statement)

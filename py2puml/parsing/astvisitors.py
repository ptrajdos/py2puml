from typing import Dict, List, Tuple
from ast import (
    NodeVisitor, arg, expr, ClassDef,
    FunctionDef, Assign, AnnAssign, ImportFrom,
    Attribute, Name, Subscript, get_source_segment, parse
)
from collections import namedtuple
from inspect import getsource, unwrap
from textwrap import dedent
from importlib import import_module

import py2puml.domain.umlclass as umlclass
from py2puml.domain.umlrelation import UmlRelation, RelType
from py2puml.parsing.moduleresolver import ModuleResolver

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


class AssignedVariablesCollector(NodeVisitor):
    '''Parses the target of an assignment statement to detect whether the value is assigned to a variable or an instance attribute'''
    def __init__(self, class_self_id: str, annotation: expr):
        self.class_self_id: str = class_self_id
        self.annotation: expr = annotation
        self.variables: List[Variable] = []
        self.self_attributes: List[Variable] = []

    def visit_Name(self, node: Name):
        '''
        Detects declarations of new variables
        '''
        if node.id != self.class_self_id:
            self.variables.append(Variable(node.id, self.annotation))

    def visit_Attribute(self, node: Attribute):
        '''
        Detects declarations of new attributes on 'self'
        '''
        if isinstance(node.value, Name) and node.value.id == self.class_self_id:
            self.self_attributes.append(Variable(node.attr, self.annotation))

    def visit_Subscript(self, node: Subscript):
        '''
        Assigns a value to a subscript of an existing variable: must be skipped
        '''
        pass


class ClassVisitor(NodeVisitor):

    def __init__(self, class_type, root_fqn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_type = class_type
        self.root_fqn = root_fqn
        self.class_name: str = None
        self.attributes = []
        self.uml_methods: List[umlclass.UmlMethod] = []
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
            attribute = umlclass.InstanceAttribute(name=node.target.id, _type=_type)
        else:
            attribute = umlclass.ClassAttribute(name=node.target.id, _type=_type)
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
        self.uml_methods.append(method_visitor.uml_method)

        if node.name == '__init__' and True:
            constructor_visitor = ConstructorVisitor.from_class_type(self.class_type, self.root_fqn)
            constructor_ast = parse(constructor_visitor.constructor_source)
            constructor_visitor.visit(constructor_ast)
            for attribute in constructor_visitor.instance_attributes:
                self.attributes.append(attribute)


class DecoratorVisitor(NodeVisitor):

    def __init__(self,  *args, **kwargs):
        self.decorator_type: str = None

    def visit_Name(self, node: Name):
        self.decorator_type = node.id


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

    If the method is the class constructor, instance attributes (and their type) are also identified by looking both at the constructor signature and constructor's body. When searching in the constructor's body, the visitor looks for relevant assignments (with and without type annotation).
     """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variables_namespace: List[Variable] = []
        self.uml_method: umlclass.UmlMethod

    def visit_FunctionDef(self, node: FunctionDef):
        # FIXME: refactor with the DecoratorVisitor class
        # TODO: can it handle getter/setter decorator?
        decorators = [decorator.id for decorator in node.decorator_list]
        is_static = 'staticmethod' in decorators
        is_class = 'classmethod' in decorators
        arguments_collector = SignatureVariablesCollector(skip_self=is_static)
        arguments_collector.visit(node)
        self.variables_namespace = arguments_collector.variables

        self.uml_method = umlclass.UmlMethod(name=node.name, is_static=is_static, is_class=is_class)

        for argument in arguments_collector.variables:
            if argument.id == arguments_collector.class_self_id:
                self.uml_method.arguments[argument.id] = None
            if argument.type_expr:
                if hasattr(argument.type_expr, 'id'):
                    self.uml_method.arguments[argument.id] = argument.type_expr.id
                else:

                    self.uml_method.arguments[argument.id] = arguments_collector.datatypes[argument.id]
            else:
                self.uml_method.arguments[argument.id] = None

        if node.returns is not None:
            return_visitor = TypeVisitor()
            self.uml_method.return_type = return_visitor.visit(node.returns)


class ConstructorVisitor(NodeVisitor):
    '''
    Identifies the attributes (and infer their type) assigned to self in the body of a constructor method
    '''
    def __init__(self, constructor_source: str, class_name: str, root_fqn: str, module_resolver: ModuleResolver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constructor_source = constructor_source
        self.class_fqn: str = f'{module_resolver.module.__name__}.{class_name}'
        self.root_fqn = root_fqn
        self.module_resolver = module_resolver
        self.class_self_id: str
        self.variables_namespace: List[Variable] = []
        self.uml_attributes: List[umlclass.UmlAttribute] = []
        self.uml_relations_by_target_fqn: Dict[str, UmlRelation] = {}
        self.instance_attributes: List[umlclass.InstanceAttributes] = []
        # self.namespaced_types = namespaced_types

    @classmethod
    def from_class_type(cls, class_type, root_fqn):
        module_resolver = ModuleResolver(import_module(class_type.__module__))
        constructor = getattr(class_type, '__init__', None)
        constructor = unwrap(constructor)
        constructor_source = dedent(getsource(constructor.__code__))
        return ConstructorVisitor(constructor_source, class_type.__name__, root_fqn, module_resolver)

    def extend_relations(self, target_fqns: List[str]):
        """ """
        self.uml_relations_by_target_fqn.update({
            target_fqn: UmlRelation(self.class_fqn, target_fqn, RelType.COMPOSITION)
            for target_fqn in target_fqns
            if target_fqn.startswith(self.root_fqn) and (
                target_fqn not in self.uml_relations_by_target_fqn
            )
        })

    def get_from_namespace(self, variable_id: str) -> Variable:
        return next((
            variable
            # variables namespace is iterated anti-chronologically
            # to account for variables being overridden
            for variable in self.variables_namespace[::-1]
            if variable.id == variable_id
        ), None)

    def generic_visit(self, node):
        NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node: FunctionDef):
        # retrieves constructor arguments ('self' reference and typed arguments)
        if node.name == '__init__':
            arguments_collector = SignatureVariablesCollector()
            arguments_collector.visit(node)
            self.class_self_id: str = arguments_collector.class_self_id
            self.variables_namespace = arguments_collector.variables

        self.generic_visit(node)

    def visit_AnnAssign(self, node: AnnAssign):
        variables_collector = AssignedVariablesCollector(self.class_self_id, node.annotation)
        variables_collector.visit(node.target)

        short_type, full_namespaced_definitions = self.derive_type_annotation_details(node.annotation)
        # if any, there is at most one self-assignment
        for variable in variables_collector.self_attributes:
            self.uml_attributes.append(umlclass.UmlAttribute(variable.id, short_type, static=False))
            instance_attribute = umlclass.InstanceAttribute(name=variable.id, _type=short_type)
            self.instance_attributes.append(instance_attribute)
            self.extend_relations(full_namespaced_definitions)

        # if any, there is at most one typed variable added to the scope
        self.variables_namespace.extend(variables_collector.variables)

    def visit_Assign(self, node: Assign):
        # recipients of the assignment
        for assigned_target in node.targets:
            variables_collector = AssignedVariablesCollector(self.class_self_id, None)
            variables_collector.visit(assigned_target)

            # attempts to infer attribute type when a single attribute is assigned to a variable
            if (len(variables_collector.self_attributes) == 1) and (isinstance(node.value, Name)):
                assigned_variable = self.get_from_namespace(node.value.id)
                if assigned_variable is not None:
                    short_type, full_namespaced_definitions = self.derive_type_annotation_details(assigned_variable.type_expr)
                    attribute = umlclass.UmlAttribute(variables_collector.self_attributes[0].id, short_type, False)
                    self.uml_attributes.append(attribute)
                    instance_attribute = umlclass.InstanceAttribute(name=variables_collector.self_attributes[0].id, _type=short_type)
                    self.instance_attributes.append(instance_attribute)
                    self.extend_relations(full_namespaced_definitions)
            else:
                for variable in variables_collector.self_attributes:
                    short_type, full_namespaced_definitions = self.derive_type_annotation_details(variable.type_expr)
                    self.uml_attributes.append(umlclass.UmlAttribute(variable.id, short_type, static=False))
                    instance_attribute = umlclass.InstanceAttribute(name=variable.id, _type=short_type)
                    self.instance_attributes.append(instance_attribute)
                    self.extend_relations(full_namespaced_definitions)

            # other assignments were done in new variables that can shadow existing ones
            self.variables_namespace.extend(variables_collector.variables)

    def derive_type_annotation_details(self, annotation: expr) -> Tuple[str, List[str]]:
        '''
        From a type annotation, derives:
        - a short version of the type (withenum.TimeUnit -> TimeUnit, Tuple[withenum.TimeUnit] -> Tuple[TimeUnit])
        - a list of the full-namespaced definitions involved in the type annotation (in order to build the relationships)
        '''
        if annotation is None:
            return None, []

        # primitive type, object definition
        if isinstance(annotation, Name):
            full_namespaced_type, short_type = self.module_resolver.resolve_full_namespace_type(annotation.id)
            return short_type, [full_namespaced_type]
        # definition from module
        elif isinstance(annotation, Attribute):
            source_segment = get_source_segment(self.constructor_source, annotation)
            full_namespaced_type, short_type = self.module_resolver.resolve_full_namespace_type(source_segment)
            return short_type, [full_namespaced_type]
        # compound type (List[...], Tuple[Dict[str, float], module.DomainType], etc.)
        elif isinstance(annotation, Subscript):
            source_segment = get_source_segment(self.constructor_source, annotation)
            short_type, associated_types = self.module_resolver.shorten_compound_type_annotation(source_segment)
            return short_type, associated_types
        return None, []


class ModuleVisitor(NodeVisitor):

    def __init__(self, root_fqn):
        self.classes:List[umlclass.PythonClass] = []
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
        for method in visitor.uml_methods:
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



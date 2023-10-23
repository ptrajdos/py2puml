import unittest
from typing import Dict, Tuple, List

from ast import parse, AST, get_source_segment
from inspect import getsource
from textwrap import dedent

from pytest import mark

from py2puml.parsing.astvisitors import AssignedVariablesCollector, TypeVisitor, SignatureVariablesCollector, ClassVisitor, BaseClassVisitor, ModuleVisitor, DecoratorVisitor
from py2puml.domain.umlclass import ClassAttribute, InstanceAttribute, ImportStatement
from tests.asserts.variable import assert_Variable
from tests.modules.withmethods import withmethods, withinheritedmethods
from tests.modules import withcomposition


class ParseMyConstructorArguments:
    def __init__(
        # the reference to the instance is often 'self' by convention, but can be anything else
        me,
        # some arguments, typed or untyped
        an_int: int, an_untyped, a_compound_type: Tuple[float, Dict[str, List[bool]]],
        # an argument with a default value
        a_default_string: str='text',
        # positional and keyword wildcard arguments
        *args, **kwargs
    ):
        pass

def test_SignatureVariablesCollector_collect_arguments():
    constructor_source: str = dedent(getsource(ParseMyConstructorArguments.__init__.__code__))
    constructor_ast: AST = parse(constructor_source)

    collector = SignatureVariablesCollector()
    collector.visit(constructor_ast)

    assert collector.class_self_id == 'me'
    assert len(collector.variables) == 7, 'all the arguments must be detected'
    assert_Variable(collector.variables[0], 'me', None, constructor_source)
    assert_Variable(collector.variables[1], 'an_int', 'int', constructor_source)
    assert_Variable(collector.variables[2], 'an_untyped', None, constructor_source)
    assert_Variable(collector.variables[3], 'a_compound_type', 'Tuple[float, Dict[str, List[bool]]]', constructor_source)
    assert_Variable(collector.variables[4], 'a_default_string', 'str', constructor_source)
    assert_Variable(collector.variables[5], 'args', None, constructor_source)
    assert_Variable(collector.variables[6], 'kwargs', None, constructor_source)

@mark.parametrize(
    'class_self_id,assignment_code,annotation_as_str,self_attributes,variables', [
        # detects the assignment to a new variable
        ('self', 'my_var = 5', None, [], [('my_var', None)]),
        ('self', 'my_var: int = 5', 'int', [], [('my_var', 'int')]),
        # detects the assignment to a new self attribute
        ('self', 'self.my_attr = 6', None, [('my_attr', None)], []),
        ('self', 'self.my_attr: int = 6', 'int', [('my_attr', 'int')], []),
        # tuple assignment mixing variable and attribute
        ('self', 'my_var, self.my_attr = 5, 6', None, [('my_attr', None)], [('my_var', None)]),
        # assignment to a subscript of an attribute
        ('self', 'self.my_attr[0] = 0', None, [], []),
        ('self', 'self.my_attr[0]:int = 0', 'int', [], []),
        # assignment to an attribute of an attribute
        ('self', 'self.my_attr.id = "42"', None, [], []),
        ('self', 'self.my_attr.id: str = "42"', 'str', [], []),
        # assignment to an attribute of a reference which is not 'self'
        ('me', 'self.my_attr = 6', None, [], []),
        ('me', 'self.my_attr: int = 6', 'int', [], []),
    ]
)
def test_AssignedVariablesCollector_single_assignment_separate_variable_from_instance_attribute(
    class_self_id: str, assignment_code: str, annotation_as_str: str, self_attributes: list, variables: list
):
    # the assignment is the first line of the body
    assignment_ast: AST = parse(assignment_code).body[0]

    # assignment without annotation (multiple targets, but only one in these test cases)
    if annotation_as_str is None:
        annotation = None
        assert len(assignment_ast.targets) == 1, 'unit test consistency'
        assignment_target = assignment_ast.targets[0]
    # assignment with annotation (only one target)
    else:
        annotation = assignment_ast.annotation
        assert get_source_segment(assignment_code, annotation) == annotation_as_str, 'unit test consistency'
        assignment_target = assignment_ast.target

    assignment_collector = AssignedVariablesCollector(class_self_id, annotation)
    assignment_collector.visit(assignment_target)

    # detection of self attributes
    assert len(assignment_collector.self_attributes) == len(self_attributes)
    for self_attribute, (variable_id, variable_type_str) in zip(assignment_collector.self_attributes, self_attributes):
        assert_Variable(self_attribute, variable_id, variable_type_str, assignment_code)

    # detection of new variables occupying the memory scope
    assert len(assignment_collector.variables) == len(variables)
    for variable, (variable_id, variable_type_str) in zip(assignment_collector.variables, variables):
        assert_Variable(variable, variable_id, variable_type_str, assignment_code)

@mark.parametrize(
    ['class_self_id', 'assignment_code', 'self_attributes_and_variables_by_target'], [
        (
            'self', 'x = y = 0', [
                ([], ['x']),
                ([], ['y']),
            ]
        ),
        (
            'self', 'self.x = self.y = 0', [
                (['x'], []),
                (['y'], []),
            ]
        ),
        (
            'self', 'self.my_attr = self.my_list[0] = 5', [
                (['my_attr'], []),
                ([], []),
            ]
        ),
        (
            'self', 'self.x, self.y = self.origin = (0, 0)', [
                (['x', 'y'], []),
                (['origin'], []),
            ]
        ),
    ]
)
def test_AssignedVariablesCollector_multiple_assignments_separate_variable_from_instance_attribute(
    class_self_id: str, assignment_code: str, self_attributes_and_variables_by_target: tuple
):
    # the assignment is the first line of the body
    assignment_ast: AST = parse(assignment_code).body[0]

    assert len(assignment_ast.targets) == len(self_attributes_and_variables_by_target), 'test consitency: all targets must be tested'
    for assignment_target, (self_attribute_ids, variable_ids) in zip(assignment_ast.targets, self_attributes_and_variables_by_target):
        assignment_collector = AssignedVariablesCollector(class_self_id, None)
        assignment_collector.visit(assignment_target)

        assert len(assignment_collector.self_attributes) == len(self_attribute_ids), 'test consistency'
        for self_attribute, self_attribute_id in zip(assignment_collector.self_attributes, self_attribute_ids):
            assert self_attribute.id == self_attribute_id
            assert self_attribute.type_expr == None, 'Python does not allow type annotation in multiple assignment'

        assert len(assignment_collector.variables) == len(variable_ids), 'test consistency'
        for variable, variable_id in zip(assignment_collector.variables, variable_ids):
            assert variable.id == variable_id
            assert variable.type_expr == None, 'Python does not allow type annotation in multiple assignment'


class TestTypeVisitor(unittest.TestCase):

    def test_return_type_int(self):
        source_code = 'def dummy_function() -> int:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'int'
        self.assertEqual(expected_rtype, actual_rtype)

    def test_return_type_compound(self):
        """ Test non-nested compound datatype"""
        source_code = 'def dummy_function() -> Tuple[float, str]:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Tuple[float, str]'
        self.assertEqual(expected_rtype, actual_rtype)

    def test_return_type_compound_nested(self):
        """ Test nested compound datatype"""
        source_code = 'def dummy_function() -> Tuple[float, Dict[str, List[bool]]]:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Tuple[float, Dict[str, List[bool]]]'
        self.assertEqual(expected_rtype, actual_rtype)

    def test_return_type_user_defined(self):
        """ Test user-defined class datatype"""
        source_code = 'def dummy_function() -> Point:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Point'
        self.assertEqual(expected_rtype, actual_rtype)


class TestClassVisitor(unittest.TestCase):

    def test_class_with_methods(self):
        class_source = getsource(withmethods.Point)
        class_ast = parse(class_source)
        visitor = ClassVisitor(withmethods.Point, 'tests.modules.withmethods')
        visitor.visit(class_ast)

        self.assertEqual('Point', visitor.class_name)

        expected_attributes = [
            ClassAttribute(name='PI', _type='float'),
            ClassAttribute(name='origin'),
            InstanceAttribute(name='coordinates', _type='Coordinates'),
            InstanceAttribute(name='day_unit', _type='TimeUnit'),
            InstanceAttribute(name='hour_unit', _type='TimeUnit'),
            InstanceAttribute(name='time_resolution', _type='Tuple[str, TimeUnit]'),
            InstanceAttribute(name='x', _type='int'),
            InstanceAttribute(name='y', _type='Tuple[bool]'),
            InstanceAttribute(name='description', _type='str')]
        actual_attributes = visitor.attributes
        self.assertCountEqual(expected_attributes, actual_attributes)

        expected_methods = ['from_values', 'get_coordinates', '__init__', 'do_something']
        actual_methods = [method.name for method in visitor.methods]
        self.assertCountEqual(expected_methods, actual_methods)

        self.assertEqual(0, len(visitor.parent_classes_pqn))

    def test_class_with_inherited_methods(self):
        class_source = getsource(withinheritedmethods.ThreeDimensionalPoint)
        class_ast = parse(class_source)
        visitor = ClassVisitor(withinheritedmethods.ThreeDimensionalPoint, 'tests.modules.withmethods')
        visitor.visit(class_ast)

        self.assertEqual('ThreeDimensionalPoint', visitor.class_name)

        expected_attributes = [InstanceAttribute(name='z', _type='float')]
        actual_attributes = visitor.attributes
        self.assertCountEqual(expected_attributes, actual_attributes)

        expected_methods = ['__init__', 'move', 'check_positive']
        actual_methods = [method.name for method in visitor.methods]
        self.assertCountEqual(expected_methods, actual_methods)

        self.assertIn('Point', visitor.parent_classes_pqn)
        self.assertEqual(1, len(visitor.parent_classes_pqn))

    def test_class_with_inherited_methods_2(self):
        class_source = getsource(withinheritedmethods.ThreeDimensionalCoordinates)
        class_ast = parse(class_source)
        visitor = ClassVisitor(withinheritedmethods.ThreeDimensionalCoordinates, 'tests.modules.withmethods')
        visitor.visit(class_ast)

        self.assertEqual('ThreeDimensionalCoordinates', visitor.class_name)

        expected_attributes = [InstanceAttribute(name='z', _type='float')]
        actual_attributes = visitor.attributes
        self.assertCountEqual(expected_attributes, actual_attributes)

        expected_methods = ['__init__', 'move', 'check_negative']
        actual_methods = [method.name for method in visitor.methods]
        self.assertCountEqual(expected_methods, actual_methods)

        self.assertIn('withmethods.withmethods.Coordinates', visitor.parent_classes_pqn)
        self.assertEqual(1, len(visitor.parent_classes_pqn))

    def test_dataclass(self):
        """ Test the ClassVisitor with a dataclass """
        module_source = getsource(withcomposition)
        module_ast = parse(module_source)
        visitor = ClassVisitor(withcomposition.Address, 'tests.modules.withcomposition')
        visitor.visit(module_ast.body[2])

        self.assertEqual('Address', visitor.class_name)
        for attribute, expected_name in zip(visitor.attributes, ['street', 'zipcode', 'city']):
            with self.subTest('Message', name=expected_name):
                self.assertIsInstance(attribute, InstanceAttribute)
                self.assertEqual(expected_name, attribute.name)


class TestBaseClassVisitor(unittest.TestCase):

    def test_name(self):
        source_code = 'class DerivedClass(BaseClass):\n    pass'
        ast = parse(source_code)
        node = ast.body[0].bases[0]
        visitor = BaseClassVisitor()
        visitor.visit(node)
        self.assertEqual('BaseClass', visitor.qualified_name)

    def test_name_with_module(self):
        source_code = 'class DerivedClass(package.module.BaseClass):\n    pass'
        ast = parse(source_code)
        node = ast.body[0].bases[0]
        visitor = BaseClassVisitor()
        visitor.visit(node)
        self.assertEqual('package.module.BaseClass', visitor.qualified_name)


class TestModuleVisitor(unittest.TestCase):

    def test_visit(self):
        """ Test that the visit method works correctly on various import statements and that the 'import_statements'
        attribute has the correct value """
        source_code = 'from dataclasses import dataclass\n' \
                      'from typing import List, Optional\n' \
                      'from ..nomoduleroot.modulechild.leaf import OakLeaf\n' \
                      'from ..nomoduleroot.modulechild.leaf import CommownLeaf as CommonLeaf'
        ast = parse(source_code)
        visitor = ModuleVisitor('dummy.root.fqn')
        visitor.visit(ast)

        expected_imports = [ImportStatement(module_name='dataclasses', name='dataclass'),
                            ImportStatement(module_name='typing', name='List'),
                            ImportStatement(module_name='typing', name='Optional'),
                            ImportStatement(module_name='nomoduleroot.modulechild.leaf', name='OakLeaf', level=2),
                            ImportStatement(module_name='nomoduleroot.modulechild.leaf', name='CommownLeaf',
                                            alias='CommonLeaf', level=2)]

        self.assertCountEqual(expected_imports, visitor.imports)


class TestDecoratorVisitor(unittest.TestCase):

    def test_visit(self):
        source_code = '@staticmethod\nclass DummyClass:\n    pass'
        ast = parse(source_code)
        decorator_node = ast.body[0].decorator_list[0]
        visitor = DecoratorVisitor()
        visitor.visit(decorator_node)
        self.assertEqual('staticmethod', visitor.decorator_type)

    def test_visit_2(self):
        source_code = '@unittest.mock.patch\nclass DummyClass:\n    pass'
        ast = parse(source_code)
        decorator_node = ast.body[0].decorator_list[0]
        visitor = DecoratorVisitor()
        visitor.visit(decorator_node)
        self.assertEqual('unittest.mock.patch', visitor.decorator_type)

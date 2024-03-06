import unittest
from ast import parse
from inspect import getsource

from py2puml.classes import ClassVisitor, BaseClassVisitor, ClassAttribute, InstanceAttribute, PythonClass
from py2puml.methods import Method
from tests.modules.withmethods import withmethods, withinheritedmethods
from tests.modules import withcomposition
from tests.modules.withnestednamespace.withonlyonesubpackage.underground import Soil
from tests.modules.withmethods.withmethods import Point


class TestPythonClass(unittest.TestCase):

    def setUp(self) -> None:

        self.point_class = PythonClass(
            name='Point',
            fully_qualified_name='tests.modules.withmethods.withmethods.Point',
            attributes=[
                ClassAttribute(name='PI', type_expr='float'),
                ClassAttribute(name='origin'),
                InstanceAttribute(name='coordinates', type_expr='Coordinates'),
                InstanceAttribute(name='day_unit', type_expr='TimeUnit'),
                InstanceAttribute(name='hour_unit', type_expr='TimeUnit'),
                InstanceAttribute(name='time_resolution', type_expr='Tuple[str, TimeUnit]'),
                InstanceAttribute(name='x', type_expr='int'),
                InstanceAttribute(name='y', type_expr='Tuple[bool]')],
            methods=[
                Method(
                    name='from_values',
                    arguments={'x': 'int', 'y': 'str'},
                    is_static=True,
                    return_type='Point'),
                Method(
                    name='get_coordinates',
                    arguments={'self': None},
                    return_type='Tuple[float, str]'),
                Method(
                    name='__init__',
                    arguments={'self': None, 'x': 'int', 'y': 'Tuple[bool]'}),
                Method(
                    name='do_something',
                    arguments={'self': None, 'posarg_nohint': None, 'posarg_hint': 'str', 'posarg_default': None},
                    return_type='int')])

    def test_from_type(self):
        _class = PythonClass.from_type(Point)
        self.assertEqual('Point', _class.name)
        self.assertEqual('tests.modules.withmethods.withmethods.Point', _class.fully_qualified_name)

    def test_from_type_init_module(self):
        """ Test the from_type alternate constructor with a class initialized in a __init__ module """
        _class = PythonClass.from_type(Soil)
        expected_fqn = 'tests.modules.withnestednamespace.withonlyonesubpackage.underground.Soil'
        self.assertEqual(expected_fqn, _class.fully_qualified_name)

    def test_as_puml(self):
        expected_result = '''class tests.modules.withmethods.withmethods.Point {
  PI: float {static}
  origin {static}
  coordinates: Coordinates
  day_unit: TimeUnit
  hour_unit: TimeUnit
  time_resolution: Tuple[str, TimeUnit]
  x: int
  y: Tuple[bool]
  {static} Point from_values(int x, str y)
  Tuple[float, str] get_coordinates(self)
  __init__(self, int x, Tuple[bool] y)
  int do_something(self, posarg_nohint, str posarg_hint, posarg_default)
}\n'''

        actual_result = self.point_class.as_puml

        self.assertEqual(expected_result, actual_result)


class TestClassVisitor(unittest.TestCase):

    def test_class_with_methods(self):
        class_source = getsource(withmethods.Point)
        class_ast = parse(class_source)
        visitor = ClassVisitor(withmethods.Point, 'tests.modules.withmethods')
        visitor.visit(class_ast)

        self.assertEqual('Point', visitor.class_name)

        expected_attributes = [
            ClassAttribute(name='PI', type_expr='float'),
            ClassAttribute(name='origin'),
            InstanceAttribute(name='coordinates', type_expr='Coordinates'),
            InstanceAttribute(name='day_unit', type_expr='TimeUnit'),
            InstanceAttribute(name='hour_unit', type_expr='TimeUnit'),
            InstanceAttribute(name='time_resolution', type_expr='Tuple[str, TimeUnit]'),
            InstanceAttribute(name='x', type_expr='int'),
            InstanceAttribute(name='y', type_expr='Tuple[bool]'),
            InstanceAttribute(name='description', type_expr='str')]
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

        expected_attributes = [InstanceAttribute(name='z', type_expr='float')]
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

        expected_attributes = [InstanceAttribute(name='z', type_expr='float')]
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

import unittest
from pathlib import Path

import tests.modules
import tests.modules.withabstract
from tests.modules.withmethods.withmethods import Point
from py2puml.domain.umlclass import PythonPackage, PythonModule, PythonClass, UmlMethod, ClassAttribute, InstanceAttribute, Attribute

SRC_DIR = Path(__file__).parent.parent.parent
TESTS_DIR = SRC_DIR / 'tests'
MODULES_DIR = TESTS_DIR / 'modules'


class TestPythonClass(unittest.TestCase):

    def setUp(self) -> None:

        self.point_class = PythonClass(
            name='Point',
            fully_qualified_name='tests.modules.withmethods.withmethods.Point',
            attributes=[
                ClassAttribute(name='PI', _type='float'),
                ClassAttribute(name='origin'),
                InstanceAttribute(name='coordinates', _type='Coordinates'),
                InstanceAttribute(name='day_unit', _type='TimeUnit'),
                InstanceAttribute(name='hour_unit', _type='TimeUnit'),
                InstanceAttribute(name='time_resolution', _type='Tuple[str, TimeUnit]'),
                InstanceAttribute(name='x', _type='int'),
                InstanceAttribute(name='y', _type='Tuple[bool]')],
            methods=[
                UmlMethod(
                    name='from_values',
                    arguments={'x': 'int', 'y': 'str'},
                    is_static=True,
                    return_type='Point'),
                UmlMethod(
                    name='get_coordinates',
                    arguments={'self': None},
                    return_type='Tuple[float, str]'),
                UmlMethod(
                    name='__init__',
                    arguments={'self': None, 'x': 'int', 'y': 'Tuple[bool]'}),
                UmlMethod(
                    name='do_something',
                    arguments={'self': None, 'posarg_nohint': None, 'posarg_hint': 'str', 'posarg_default': None},
                    return_type='int')])

    def test_from_type(self):
        _class = PythonClass.from_type(Point)
        self.assertEqual('Point', _class.name)
        self.assertEqual('tests.modules.withmethods.withmethods.Point', _class.fully_qualified_name)

    def test_represent_as_puml(self):
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
}'''

        actual_result = self.point_class.represent_as_puml()

        self.assertEqual(expected_result, actual_result)


class TestPythonModule(unittest.TestCase):

    def test_from_imported_module(self):
        module = PythonModule.from_imported_module(tests.modules.withabstract)
        self.assertEqual('withabstract', module.name)
        self.assertEqual('tests.modules.withabstract', module.fully_qualified_name)
        self.assertEqual(MODULES_DIR / 'withabstract.py', module.path)

    def test_visit(self):
        module = PythonModule(
            name='withconstructor',
            fully_qualified_name='tests.modules.withconstructor',
            path=MODULES_DIR / 'withconstructor.py'
        )
        module.visit()

        expected_class_names = ['Coordinates', 'Point']
        actual_class_names = [_class.name for _class in module.classes]

        self.assertCountEqual(expected_class_names, actual_class_names)  #FIXME: test more than classes name

    def test_visit_2(self):
        module = PythonModule(
            name='withmethods',
            fully_qualified_name='tests.modules.withmethods.withmethods',
            path=MODULES_DIR / 'withmethods' / 'withmethods.py'
        )
        module.visit()

        expected_class_names = ['Coordinates', 'Point']
        actual_class_names = [_class.name for _class in module.classes]

        self.assertCountEqual(expected_class_names, actual_class_names)  #FIXME: test more than classes name


class TestPythonPackage(unittest.TestCase):

    def test_from_imported_package(self):
        package = PythonPackage.from_imported_package(tests.modules)
        self.assertEqual(TESTS_DIR / 'modules', package.path)
        self.assertEqual('modules', package.name)
        self.assertEqual('tests.modules', package.fully_qualified_name)

    def test_walk(self):
        expected_modules = [
            'tests.modules.withabstract',
            'tests.modules.withbasictypes',
            'tests.modules.withcomposition',
            'tests.modules.withcompoundtypewithdigits',
            'tests.modules.withconstructor',
            'tests.modules.withenum',
            'tests.modules.withinheritancewithinmodule',
            'tests.modules.withnamedtuple',
            'tests.modules.withwrappedconstructor',
            'tests.modules.withsubdomain.withsubdomain',
            'tests.modules.withsubdomain.subdomain.insubdomain'
        ]
        expected_packages = [
            'tests.modules.withsubdomain',
            'tests.modules.withsubdomain.subdomain'
        ]

        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()

        actual_modules = [module.fully_qualified_name for module in package.modules]
        actual_packages = [package.fully_qualified_name for package in package.packages]

        self.assertCountEqual(expected_modules, actual_modules)
        self.assertCountEqual(expected_packages, actual_packages)


class TestClassAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.typed_attribute = ClassAttribute(name='PI', _type='float')
        self.untyped_attribute = ClassAttribute(name='origin')

    def test_constructor_typed(self):
        class_attribute = ClassAttribute(name='PI', _type='float')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('PI', class_attribute.name)
        self.assertEqual('float', class_attribute._type)

    def test_constructor_untyped(self):
        class_attribute = ClassAttribute(name='origin')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('origin', class_attribute.name)
        self.assertIsNone(class_attribute._type)

    def test_represent_as_puml_typed(self):
        expected_result = 'PI: float {static}'
        actual_result = self.typed_attribute.represent_as_puml()
        self.assertEqual(expected_result, actual_result)

    def test_represent_as_puml_untyped(self):
        expected_result = 'origin {static}'
        actual_result = self.untyped_attribute.represent_as_puml()
        self.assertEqual(expected_result, actual_result)
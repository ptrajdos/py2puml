import unittest
from pathlib import Path

import tests.modules
import tests.modules.withabstract
from py2puml.domain.umlclass import PythonPackage, PythonModule

SRC_DIR = Path(__file__).parent.parent.parent
TESTS_DIR = SRC_DIR / 'tests'
MODULES_DIR = TESTS_DIR / 'modules'


class TestPythonModule(unittest.TestCase):

    def test_from_imported_module(self):
        module = PythonModule.from_imported_module(tests.modules.withabstract)
        self.assertEqual('withabstract', module.name)
        self.assertEqual('tests.modules.withabstract', module.fully_qualified_name)
        self.assertEqual(MODULES_DIR / 'withabstract.py', module.path)


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

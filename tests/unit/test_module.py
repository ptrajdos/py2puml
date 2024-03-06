import unittest
from ast import parse
from pathlib import Path

import tests.modules
import tests.modules.withabstract
import tests.modules.withnestednamespace
import tests.modules.withsubdomain
import tests.modules.withmethods.withinheritedmethods
from tests.modules.withmethods.withmethods import Point
from tests.modules.withnestednamespace.withonlyonesubpackage.underground.roots import roots
from tests.modules.withnestednamespace.withoutumlitemroot.withoutumlitemleaf import withoutumlitem
from py2puml.module import ModuleVisitor, ImportStatement, PythonModule
from py2puml.package import PythonPackage


SRC_DIR = Path(__file__).parent.parent.parent
TESTS_DIR = SRC_DIR / 'tests'
MODULES_DIR = TESTS_DIR / 'modules'


class TestPythonModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        import_withmethods = ImportStatement(module_name='tests.modules', name='withmethods', alias=None, level=0,
                        fully_qualified_name='tests.modules')
        import_point = ImportStatement(module_name='withmethods', name='Point', alias=None, level=1,
                                           fully_qualified_name='tests.modules.withmethods.withmethods')
        import_withmeth = ImportStatement(module_name='tests.modules', name='withmethods', alias='withmeth', level=0,
                        fully_qualified_name='tests.modules')
        import_pt = ImportStatement(module_name='withmethods', name='Point', alias='Pt', level=1,
                                           fully_qualified_name='tests.modules.withmethods.withmethods')

        module = PythonModule(name='withinheritedmethods',
                              fully_qualified_name='tests.modules.withmethods.withinheritedmethods', path='.')
        module.import_statements['withmethods'] = import_withmethods
        module.import_statements['Point'] = import_point
        module.import_statements['withmeth'] = import_withmeth
        module.import_statements['Pt'] = import_pt

        cls.module = module

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

    def test_visit_3(self):
        """ Test that the import statements are correctly processed """

        module = PythonModule(
            name='branch',
            fully_qualified_name='tests.modules.withnestednamespace.branches.branch',
            path=MODULES_DIR / 'withnestednamespace' / 'branches' / 'branch.py'
        )
        module.visit()
        self.assertEqual(5, len(module.import_statements))

    def test_has_classes(self):
        """ Test the has_classes property on a module containing two classes """
        module = PythonModule.from_imported_module(tests.modules.withmethods.withmethods)
        module.visit()
        self.assertTrue(module.has_classes)

    def test_has_classes_2(self):
        """ Test the has_classes property on a module containing one dataclass """
        module = PythonModule.from_imported_module(roots)
        module.visit()
        self.assertTrue(module.has_classes)

    def test_has_classes_3(self):
        """ Test the has_classes property on a module not containing any class """
        module = PythonModule.from_imported_module(withoutumlitem)
        module.visit()
        self.assertFalse(module.has_classes)

    def test_resolve_class_name(self):
        """ Test resolve_class_name """
        expected_fqn = 'tests.modules.withmethods.withmethods.Point'
        actual_fqn = self.module.resolve_class_name('Point')
        self.assertEqual(expected_fqn, actual_fqn)

    def test_resolve_class_name_alias(self):
        """ Test resolve_class_name with an aliased class."""
        expected_fqn = 'tests.modules.withmethods.withmethods.Point'
        actual_fqn = self.module.resolve_class_name('Pt')
        self.assertEqual(expected_fqn, actual_fqn)

    def test_resolve_class_pqn(self):
        """ Test resolve_class_pqn on a partially defined class name with relative import """
        expected_fqn = 'tests.modules.withmethods.withmethods.Coordinates'
        actual_fqn = self.module.resolve_class_pqn('withmethods.withmethods.Coordinates')
        self.assertEqual(expected_fqn, actual_fqn)

    def test_resolve_class_pqn_alias(self):
        """ Test resolve_class_pqn on an aliased partially defined class name with relative import """
        expected_fqn = 'tests.modules.withmethods.withmethods.Coordinates'
        actual_fqn = self.module.resolve_class_pqn('withmeth.withmethods.Coordinates')
        self.assertEqual(expected_fqn, actual_fqn)


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


class TestModuleImport(unittest.TestCase):

    def test_resolve_relative_import(self):
        """ Test the resolve_relative_import method with a 2-level relative import. The relative module qualified
        name passed as input 'nomoduleroot.modulechild.leaf' correspond in the Python module to the source code
        '..nomoduleroot.modulechild.leaf' """

        module_import = ImportStatement(
            module_name='nomoduleroot.modulechild.leaf',
            name='OakLeaf',
            alias=None,
            level=2
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        branches_package = package.subpackages['branches']
        branch_module = branches_package.modules[0]

        expected_result = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf'
        module_import.resolve_relative_import(branch_module)

        self.assertEqual(expected_result, module_import.fully_qualified_name)

    def test_resolve_relative_import_2(self):
        """ Test the resolve_relative_import method with a 1-level relative import. The relative module qualified
        name passed as input 'trunks.trunk' correspond in the Python module to the source code
        '.trunks.trunk' """

        module_import = ImportStatement(
            module_name='trunks.trunk',
            name='Trunk',
            alias=None,
            level=1
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        tree_module = package.modules[0]

        expected_result = 'tests.modules.withnestednamespace.trunks.trunk'
        module_import.resolve_relative_import(tree_module)

        self.assertEqual(expected_result, module_import.fully_qualified_name)

    def test_resolve_relative_import_3(self):
        """ Test the resolve_relative_import method when a whole module is imported """
        module_import = ImportStatement(
            module_name='withmethods',
            name='Point',
            alias=None,
            level=1
        )
        package = PythonPackage.from_imported_package(tests.modules.withmethods)
        package.walk()
        module = package.modules[0]

        expected_result = 'tests.modules.withmethods.withmethods'
        module_import.resolve_relative_import(module)

        self.assertEqual(expected_result, module_import.fully_qualified_name)

    def test_resolve_relative_import_fail(self):
        """ Test the resolve_relative_import method raises and error when import cannot be resolved due to parent missing in module hierarchy"""

        module_import = ImportStatement(
            module_name='trunks.trunk',
            name='Trunk',
            alias=None,
            level=3
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        tree_module = package.modules[0]

        with self.assertRaises(Exception):
            module_import.resolve_relative_import(tree_module)

    def test_resolve_relative_import_fail_2(self):
        """ Test that the resolve_relative_import method raises an exception when the imported object module name is
        absolute """
        module_import = ImportStatement(
            module_name='tests.modules',
            name='withmethods',
            alias=None,
            level=0
        )
        module = PythonModule(name='dummy', path='.', fully_qualified_name='dummy.dummy')

        with self.assertRaises(ValueError):
            module_import.resolve_relative_import(module)


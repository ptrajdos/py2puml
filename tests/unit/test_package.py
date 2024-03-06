import unittest
from pathlib import Path
from pytest import mark

import tests.modules
import tests.modules.withnestednamespace
from py2puml.module import PythonModule
from py2puml.package import PythonPackage, PackageType


SRC_DIR = Path(__file__).parent.parent.parent
TESTS_DIR = SRC_DIR / 'tests'
MODULES_DIR = TESTS_DIR / 'modules'


class TestPythonPackage(unittest.TestCase):

    def setUp(self) -> None:
        module1 = PythonModule(name='withmethods', fully_qualified_name='tests.modules.withmethods.withmethods', path=MODULES_DIR / 'withmethods' / 'withmethods.py')
        module2 = PythonModule(name='withinheritedmethods', fully_qualified_name='tests.modules.withmethods.withinheritedmethods', path=MODULES_DIR / 'withmethods' / 'withinheritedmethods.py')
        module1.visit()
        module2.visit()
        self.package = PythonPackage(path=MODULES_DIR / 'withmethods', name='withmethods', fully_qualified_name='tests.modules.withmethods')
        self.package.modules.append(module1)
        self.package.modules.append(module2)

    def test_from_imported_package(self):
        package = PythonPackage.from_imported_package(tests.modules)
        self.assertEqual(TESTS_DIR / 'modules', package.path)
        self.assertEqual('modules', package.name)
        self.assertEqual('tests.modules', package.fully_qualified_name)

    def test_has_sibling_root(self):
        """ Test has_sibling property on root package with modules only """
        self.assertFalse(self.package.has_sibling)

    def test_has_sibling(self):
        """ Test has_sibling property on package containing subpackages """
        root_package = PythonPackage(path=MODULES_DIR, name='root', fully_qualified_name='root')
        package1 = PythonPackage(path=MODULES_DIR, name='pkg1', fully_qualified_name='root.pkg1')
        package2 = PythonPackage(path=MODULES_DIR, name='pkg2', fully_qualified_name='root.pkg2')
        package1.parent_package = root_package
        package2.parent_package = root_package
        package11 = PythonPackage(path=MODULES_DIR / 'root', name='pkg11', fully_qualified_name='root.pkg1.pkg11')
        package11.parent_package = package1

        self.assertTrue(package1.has_sibling)
        self.assertTrue(package2.has_sibling)
        self.assertFalse(package11.has_sibling)

    def test_add_module(self):
        """ Test the _add_module method """
        package = PythonPackage(path=MODULES_DIR / 'withmethods', name='withmethods',
                                fully_qualified_name='tests.modules.withmethods')
        package.all_packages['tests.modules.withmethods'] = package
        package._add_module('tests.modules.withmethods.withmethods')
        module_obj = package.modules[0]

        self.assertEqual(1, len(package.modules))
        self.assertIn(module_obj, package.modules)
        self.assertTrue(module_obj.has_classes)
        self.assertEqual(package, module_obj.parent_package)

    def test_add_module_init(self):
        """ Test the _add_module method on a __init__ module containing class definition """
        package = PythonPackage(path=MODULES_DIR / 'withsubdomain', name='withsubdomain',
                                fully_qualified_name='tests.modules.withsubdomain')
        package.all_packages['tests.modules.withsubdomain'] = package
        package._add_module('tests.modules.withsubdomain.__init__')

        self.assertEqual(1, len(package.classes))
        self.assertEqual(1, len(package.modules))

    def test_add_subpackage(self):
        """ Test the _add_subpackage method """
        package = PythonPackage(path=MODULES_DIR, name='modules',
                                fully_qualified_name='tests.modules')
        package.all_packages['tests.modules'] = package
        subpackage = package._add_subpackage('tests.modules.withmethods')

        self.assertIsInstance(subpackage, PythonPackage)
        self.assertEqual(package, subpackage.parent_package)
        self.assertIn('withmethods', package.subpackages.keys())
        self.assertEqual(subpackage, package.subpackages['withmethods'])
        self.assertEqual(1, subpackage.depth)
        self.assertDictEqual({'tests.modules': package, 'tests.modules.withmethods': subpackage}, package.all_packages)

    def test_walk(self):
        """ Test the walk method on the tests.modules package and make sure the package and module are correctly
        hierarchized """

        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()

        self.assertEqual(9, len(package.modules))
        self.assertEqual(5, len(package.subpackages))
        self.assertEqual(PackageType.NAMESPACE, package.type_expr)
        self.assertEqual(0, package.depth)

        package_withsubdomain = package.subpackages['withsubdomain']
        self.assertEqual(PackageType.REGULAR, package_withsubdomain.type_expr)
        self.assertEqual(2, len(package_withsubdomain.modules))
        self.assertEqual(1, len(package_withsubdomain.subpackages))
        self.assertEqual(1, package_withsubdomain.depth)
        self.assertEqual(1, len(package_withsubdomain.classes))

        package_subdomain = package_withsubdomain.subpackages['subdomain']
        self.assertEqual(PackageType.REGULAR, package_subdomain.type_expr)
        self.assertEqual(1, len(package_subdomain.modules))
        self.assertEqual(0, len(package_subdomain.subpackages))
        self.assertEqual(2, package_subdomain.depth)

        package_withmethods = package.subpackages['withmethods']
        self.assertEqual(PackageType.NAMESPACE, package_withmethods.type_expr)
        self.assertEqual(2, len(package_withmethods.modules))
        self.assertEqual(0, len(package_withmethods.subpackages))
        self.assertEqual(1, package_withmethods.depth)

    def test_walk_nested_namespace(self):
        """ Test the walk method on the tests.modules.withnestednamespace package which contains both regular and namespace packages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        self.assertEqual(PackageType.NAMESPACE, package.type_expr)
        self.assertEqual(5, len(package.subpackages))
        self.assertEqual(1, len(package.modules))

        pkg_branches = package.subpackages['branches']
        self.assertEqual(PackageType.NAMESPACE, pkg_branches.type_expr)
        self.assertEqual(1, len(pkg_branches.modules))
        self.assertEqual(0, len(pkg_branches.subpackages))

        pkg_nomoduleroot = package.subpackages['nomoduleroot']
        self.assertEqual(PackageType.REGULAR, pkg_nomoduleroot.type_expr)
        self.assertEqual(0, len(pkg_nomoduleroot.modules))
        self.assertEqual(1, len(pkg_nomoduleroot.subpackages))

        self.assertEqual(PackageType.NAMESPACE, package.subpackages['trunks'].type_expr)
        self.assertEqual(1, len(package.subpackages['trunks'].modules))
        self.assertEqual(0, len(package.subpackages['trunks'].subpackages))

        package_withonlyonesubpackage = package.subpackages['withonlyonesubpackage']
        self.assertEqual(PackageType.REGULAR, package_withonlyonesubpackage.type_expr)
        self.assertEqual(0, len(package_withonlyonesubpackage.modules))
        self.assertEqual(1, len(package_withonlyonesubpackage.subpackages))

        pkg_underground = package_withonlyonesubpackage.subpackages['underground']
        self.assertEqual(PackageType.REGULAR, pkg_underground.type_expr)
        self.assertEqual(1, len(pkg_underground.modules))
        self.assertEqual(1, len(pkg_underground.subpackages))
        self.assertEqual(1, len(pkg_underground.classes))

        pkg_roots = pkg_underground.subpackages['roots']
        self.assertEqual(PackageType.NAMESPACE, pkg_roots.type_expr)
        self.assertEqual(1, len(pkg_roots.modules))
        self.assertEqual(0, len(pkg_roots.subpackages))

        package_withoutumlitemroot = package.subpackages['withoutumlitemroot']
        self.assertEqual(PackageType.REGULAR, package_withoutumlitemroot.type_expr)
        self.assertEqual(0, len(package_withoutumlitemroot .modules))
        self.assertEqual(1, len(package_withoutumlitemroot .subpackages))

        package_withoutumlitemleaf = package_withoutumlitemroot.subpackages['withoutumlitemleaf']
        self.assertEqual(PackageType.NAMESPACE, package_withoutumlitemleaf.type_expr)
        self.assertEqual(1, len(package_withoutumlitemleaf .modules))
        self.assertEqual(0, len(package_withoutumlitemleaf .subpackages))

    def test_resolve_relative_imports(self):
        """ Test resolve_relative_imports method """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        pkg_branches = package.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        self.assertIsNone(module_branch.import_statements['OakLeaf'].fully_qualified_name)

        package.resolve_relative_imports()

        expected_value = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf'
        actual_value = module_branch.import_statements['OakLeaf'].fully_qualified_name

        self.assertEqual(expected_value, actual_value)

    def test_resolve_class_inheritance_1(self):
        """ Test resolve_class_inheritance method when the class and its base class are in the same module """
        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()
        package.resolve_relative_imports()
        package.resolve_class_inheritance()

        pkg_withnestednamespace = package.subpackages['withnestednamespace']
        pkg_branches = pkg_withnestednamespace.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        class_oak_branch = module_branch.classes[1]

        expected_fully_qualified_name = 'tests.modules.withnestednamespace.branches.branch.Branch'
        actual_fully_qualified_name = class_oak_branch.base_classes['Branch'].fully_qualified_name
        self.assertEqual(expected_fully_qualified_name, actual_fully_qualified_name)

    def test_resolve_class_inheritance_2(self):
        """ Test resolve_class_inheritance method when the class and its base class are in different modules. Also tests
         that aliased import are correctly resolved (in this case 'CommonLeaf' is an alias of the 'CommownLeaf' class in
         the 'leaf' module """
        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()
        package.resolve_relative_imports()
        package.resolve_class_inheritance()

        pkg_withnestednamespace = package.subpackages['withnestednamespace']
        pkg_branches = pkg_withnestednamespace.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        class_birch_leaf = module_branch.classes[2]

        expected_fully_qualified_name = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf.CommownLeaf'
        actual_fully_qualified_name = class_birch_leaf.base_classes['CommonLeaf'].fully_qualified_name
        self.assertEqual(expected_fully_qualified_name, actual_fully_qualified_name)

    def test_find_all_classes_1(self):
        """ Test find_all_classes method on a package containing modules only """
        all_classes = self.package.find_all_classes()
        self.assertEqual(4, len(all_classes))

    def test_find_all_classes_2(self):
        """ Test find_all_classes method on a package containing subpackages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        all_classes = package.find_all_classes()
        self.assertEqual(11, len(all_classes))

    def test_find_all_modules_1(self):
        """ Test find_all_classes method on a package containing modules only """
        all_modules = self.package.find_all_modules()
        self.assertEqual(2, len(all_modules))

    def test_find_all_modules_2(self):
        """ Test find_all_classes method on a package containing subpackages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        all_modules = package.find_all_modules()
        self.assertEqual(7, len(all_modules))

    def test_find_all_modules_3(self):
        """ Test find_all_classes method on a package containing subpackages with the skip_empty flag turned on """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        all_modules = package.find_all_modules(skip_empty=True)
        self.assertEqual(6, len(all_modules))

    def test_as_puml(self):
        package = PythonPackage.from_imported_package(tests.modules.withsubdomain)
        package.walk()

        expected_result = '''namespace tests.modules.withsubdomain {
  namespace withsubdomain {}
  namespace subdomain.insubdomain {}
}\n'''
        actual_result = package.as_puml
        self.assertEqual(expected_result, actual_result)

    @mark.skip(reason='Minor issue with indentation')
    def test_as_puml_2(self):
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        expected_result = '''namespace tests.modules.withnestednamespace {
  namespace tree {}
  namespace branches.branch {}
  namespace nomoduleroot.modulechild.leaf {}
  namespace trunks.trunk {}
  namespace withonlyonesubpackage.underground {
    namespace roots.roots {}
  }
}\n'''
        actual_result = package.as_puml
        self.assertEqual(expected_result, actual_result)


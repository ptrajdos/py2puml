from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from setuptools import find_namespace_packages
from typing import Union, Dict, List

from py2puml.module import PythonModule
from py2puml.classes import PythonClass


class PackageType(Enum):
    REGULAR = 1
    NAMESPACE = 2


@dataclass
class PythonPackage:
    """ Class that represent a regular Python package with its subpackages and modules.

    Basic instantiation of objects is easily done with the 'from_imported_package' constructor method. To search
    recursively for subpackages and modules, use the 'walk' method.

    Python packages can also contain classes if these are declared in the __init__.py module.

    Attributes:
        path (Path): path to the Python package folder
        name (str): name of the Python package
        fully_qualified_name (str): fully qualified name of the Python package
        depth (int): package depth level relative to the root package. Root package has level 0.
        modules (List[PythonModule]): list of modules found in the package
        subpackages (Dict[str, PythonPackage]): dictionary of subpackages found in the package
        classes (List[PythonClass]): classes declared on package level"""
    path: Union[Path, str]
    name: str
    fully_qualified_name: str
    depth: int = 0
    _type: PackageType = PackageType.REGULAR
    modules: List[PythonModule] = field(default_factory=list)
    subpackages: Dict[str, PythonPackage] = field(default_factory=dict)
    _parent_package: PythonPackage = None
    all_packages: Dict[str, PythonPackage] = field(default_factory=dict)
    classes: List[PythonClass] = field(default_factory=list)

    @property
    def parent_package(self) -> PythonPackage:
        return self._parent_package

    @parent_package.setter
    def parent_package(self, value: PythonPackage) -> None:
        self._parent_package = value
        value.subpackages[self.name] = self

    @classmethod
    def from_imported_package(cls, package_obj):
        """ Alternate constructor method that instantiate a PythonPackage object from the corresponding imported
        package.

        Args:
            package_obj (module): imported package from e.g. the 'import' statement or the importlib.import_module()

        Returns:
            A partially instantiated PythonPackage object. To fully instantiate it, proceed by running the 'walk' method
        """
        if isinstance(package_obj.__path__, list):
            path = Path(package_obj.__path__[0])
        else:
            path = Path(package_obj.__path__._path[0])
        name = package_obj.__name__.split('.')[-1]
        fully_qualified_name = package_obj.__name__

        init_filepath = path / '__init__.py'
        if init_filepath.is_file():
            _type = PackageType.REGULAR
        else:
            _type = PackageType.NAMESPACE

        return PythonPackage(path=path, name=name, fully_qualified_name=fully_qualified_name, depth=0, _type=_type)

    def _add_module(self, module_fully_qualified_name: str, skip_empty: bool = False) -> None:
        """ Add a new module to a package from its name.

        This method imports first the module and instantiate a PythonModule object from it. Classes in this
        PythonModule are resolved by visiting the AST corresponding to this module. This method also establish
        parent-child relationship between package and module.

        Args:
            module_fully_qualified_name (str): fully qualified module name
            skip_empty (bool): if set to True skip adding module if it has no classes """

        # FIXME: importing module will execute the code. Find an alternative
        imported_module = import_module(module_fully_qualified_name)
        module = PythonModule.from_imported_module(imported_module)
        module.visit()

        if not skip_empty or module.has_classes:
            parent_package = self.all_packages[module.parent_fully_qualified_name]
            module.parent_package = parent_package

            if module.name == '__init__':
                for _class in module.classes:
                    parent_package.classes.append(_class)

    def _add_subpackage(self, subpackage_fully_qualified_name: str) -> PythonPackage:
        """ Add a new subpackage to a package from its name.

        This method imports first the module and instantiate a PythonModule object from it. Classes in this
        PythonModule are resolved by visiting the AST corresponding to this module. This method also establish
        parent-child relationship between package and subpackage and define the depth of the subpackage (0 corresponds
        to the root package).

        Args:
            subpackage_fully_qualified_name (str): fully qualified package name

        Returns;
            The subpackage itself """

        imported_package = import_module(subpackage_fully_qualified_name)
        subpackage = PythonPackage.from_imported_package(imported_package)

        self.all_packages[subpackage.fully_qualified_name] = subpackage
        parent_package = self.all_packages[subpackage.parent_fully_qualified_name]
        subpackage.depth = parent_package.depth + 1
        subpackage.parent_package = parent_package

        return subpackage

    def walk(self):
        """
        Find subpackages and modules recursively

        Uses the setuptools.find_namespace_packages method to search recursively for regular and namespace
        subpackages of a given root package (the instance 'self' in this case). Create instances of PythonPackage
        object when a subpackage is found and add it as a subpackage while preserving hierarchy (see implementation
        in method _add_subpackage ). In case the root package is a namespace package, a temporary ``__init__.py`` is
        created so that :meth:`find_namespace_packages` can search properly and then deleted.

        Since setuptools.find_namespace_packages flattens the package hierarchy, the instance attribute
        'all_packages' is used to store all packages found (including the top-level package). New packages found are
        appended to the 'subpackages' attribute of the parent package.

        Use the pkgutils.iter_modules() method to find modules in a package. When a module is found the method
        _add_module() will create a PythonModule instance, visit it  and add this object as a module of the
        corresponding PythonPackage object (see attribute 'modules'). For regular packages, the ``__init__`` module
        is visited and if class(es) is/are found, this module will also be added to the PythonPackage.modules
        attribute with the _add_module method.

        Note:
            Found subpackages and modules are imported.
        """
        self.all_packages[self.fully_qualified_name] = self

        if self._type == PackageType.NAMESPACE:
            temp_init_filepath = Path(self.path) / '__init__.py'
            with open(temp_init_filepath, 'w'):
                namespace_packages_names = find_namespace_packages(str(self.path))
            temp_init_filepath.unlink()
        else:
            namespace_packages_names = find_namespace_packages(str(self.path))
        namespace_packages_names.insert(0, None)

        for namespace_package_name in namespace_packages_names:
            if namespace_package_name:
                package = self._add_subpackage(f'{self.fully_qualified_name}.{namespace_package_name}')
            else:
                package = self

            if package._type == PackageType.REGULAR:
                self._add_module(f'{package.fully_qualified_name}.__init__', skip_empty=True)

            for _, name, is_pkg in iter_modules(path=[package.path]):
                if not is_pkg:
                    self._add_module(f'{package.fully_qualified_name}.{name}')

    def find_all_classes(self) -> List[PythonClass]:
        """ Find all classes in a given package declared in their modules, by looking recursively into subpackages.

        Returns:
            List of PythonClass objects """
        classes = []
        for module in self.modules:
            classes.extend(module.classes)
        for subpackage in self.subpackages.values():
            classes.extend(subpackage.find_all_classes())
        return classes

    def find_all_modules(self, skip_empty: bool = False) -> List[PythonModule]:
        """ Find all modules in a given package, looking recursively into subpackages. Modules not containing any
        class can be ignored by passing the optional parameter 'skip_empty' as True.

        Args:
            skip_empty (bool): exclude modules not containing any class

        Returns:
            List of PythonModule objects """
        modules = []
        for module in self.modules:

            if not skip_empty or module.has_classes:
                modules.append(module)
        for subpackage in self.subpackages.values():
            modules.extend(subpackage.find_all_modules(skip_empty=skip_empty))
        return modules

    def resolve_relative_imports(self):
        """ Resolve relative import for all modules contained in a package and its subpackage.

        This method calls recursively the PythonModule.resolve_relative_import and all modules and subpackages
        modules """

        for module in self.modules:
            for import_statement in module.import_statements.values():
                if import_statement.is_relative:
                    import_statement.resolve_relative_import(module)
                else:
                    import_statement.fully_qualified_name = import_statement.module_name

        for subpackage in self.subpackages.values():
            subpackage.resolve_relative_imports()

    def resolve_class_inheritance(self):
        """ Resolve class inheritance by assigning a value to the key(s) of the parent_classes attribute in PythonClass.

        Check first if the parent class is a class in the same module, otherwise check in other check in import statements

        During AST parsing, only the partially_qualified_name of the base class can be inferred. This method assigns the
        PythonClass object for every base class if any. This has to be done once all classes in a given package have
        been identified. """
        all_classes = self.find_all_classes()
        classes_by_fqn = {_class.fully_qualified_name: _class for _class in all_classes}

        for _class in all_classes:
            if _class.base_classes:
                remove_keys = []
                for base_class_pqn in _class.base_classes.keys():
                    if '.' in base_class_pqn:
                        base_class_fqn = _class.module.resolve_class_pqn(base_class_pqn)
                    else:
                        base_class_fqn = _class.module.resolve_class_name(base_class_pqn)

                    if base_class_fqn in classes_by_fqn.keys():
                        base_class = classes_by_fqn[base_class_fqn]
                    else:
                        base_class = None

                    if base_class:
                        _class.base_classes[base_class_pqn] = base_class
                    else:
                        remove_keys.append(base_class_pqn)

                for key in remove_keys:
                    del _class.base_classes[key]

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])

    @property
    def has_sibling(self):
        if self.parent_package:
            return len(self.parent_package.subpackages) > 1
        return False

    @property
    def as_puml(self) -> str:
        """ Returns a plantUML representation of the package that will be used in the
        'namespace' declaration of the .puml file.

        Returns:
            PlantUML representation of package"""
        # FIXME: small issue with indentation
        # FIXME: should be removed according to Issue#53 ?!?!
        modules = [module for module in self.modules if module.has_classes]

        if self.depth == 0:
            puml_str = f'namespace {self.fully_qualified_name}'
        else:
            if self.has_sibling or self.parent_package.modules:
                indentation = self.depth * '  '
                puml_str = f'\n{indentation}namespace {self.name}'
            else:
                puml_str = f'.{self.name}'

        if len(self.subpackages) + len(modules) > 1:
            puml_str = puml_str + ' {'
            indentation = (self.depth + 1) * '  '
            for module in modules:
                puml_str = puml_str + f'\n{indentation}namespace {module.name} {{}}'

            for subpackage in self.subpackages.values():
                puml_str = puml_str + subpackage.as_puml

        elif len(modules) == 1:
            puml_str = puml_str + f'.{modules[0].name} {{}}'

        elif len(self.subpackages):
            subpackage = next(iter(self.subpackages.values()))
            puml_str = puml_str + subpackage.as_puml

        else:
            puml_str = ''

        if len(self.subpackages) + len(modules) > 1:
            indentation = self.depth * '  '
            puml_str = puml_str + f'\n{indentation}}}\n'

        if self.depth == 0:
            lines = puml_str.split('\n')
            clean_lines = [line for line in lines if (line.endswith('{') or line.endswith('}')) and '__init__' not in line]
            puml_str = '\n'.join(clean_lines) + '\n'

        return puml_str
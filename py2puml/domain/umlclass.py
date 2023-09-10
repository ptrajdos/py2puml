from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass, field
from pkgutil import walk_packages, iter_modules
from pathlib import Path
from importlib import import_module
from ast import parse
from abc import ABC, abstractmethod
from enum import Enum
from setuptools import find_namespace_packages

from py2puml.domain.umlitem import UmlItem
import py2puml.parsing.astvisitors as astvisitors


class PackageType(Enum):
    REGULAR = 1
    NAMESPACE = 2


@dataclass
class UmlAttribute:
    name: str
    type: str
    static: bool


@dataclass
class UmlMethod:
    name: str
    arguments: Dict = field(default_factory=dict)
    is_static: bool = False
    is_class: bool = False
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


@dataclass
class UmlClass(UmlItem):
    attributes: List[UmlAttribute]
    methods: List[UmlMethod]
    is_abstract: bool = False


@dataclass
class PythonModule:
    """ Class that represent a Python module with its classes.

        Basic instantiation of objects is easily done with the 'from_imported_module' constructor method.

        Attributes:
            path (Path): path to the Python module file
            name (str): name of the Python module
            fully_qualified_name (str): fully qualified name of the Python module
            classes List[PythonModule]: list of classes in the module """
    name: str
    fully_qualified_name: str
    path: Path
    classes: List = field(default_factory=list)

    @classmethod
    def from_imported_module(cls, module_obj):
        """ Alternate constructor method that instantiate a PythonModule object from the corresponding imported module.

        Args:
            module_obj (module): imported module from e.g. the 'import' statement or importlib.import_module()

        Returns:
            An instantiated PythonModule object.
        """
        name = module_obj.__name__.split('.')[-1]
        fully_qualified_name = module_obj.__name__
        path = Path(module_obj.__file__)
        return PythonModule(name=name, fully_qualified_name=fully_qualified_name, path=path)

    @property
    def has_classes(self):
        return len(self.classes) > 0

    def visit(self):
        """ Visit AST node corresponding to the module in order to find classes """
        with open(self.path, 'r') as fref:
            content = fref.read()

        ast = parse(content, filename=str(self.path))
        visitor = astvisitors.ModuleVisitor(self.fully_qualified_name)
        visitor.visit(ast)

        for _class in visitor.classes:
            self.classes.append(_class)

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])


@dataclass
class PythonPackage:
    """ Class that represent a regular Python package with its subpackages and modules.

    Basic instantiation of objects is easily done with the 'from_imported_package' constructor method. To search
    recursively for subpackages and modules, use the 'walk' method.

    Attributes:
        path (Path): path to the Python package folder
        name (str): name of the Python package
        fully_qualified_name (str): fully qualified name of the Python package
        depth (int): package depth level relative to the root package. Root package has level 0.
        modules (List[PythonModule]): list of modules found in the package
        subpackages (Dict[str, PythonPackage]): dictionary of subpackages found in the package"""
    path: Path
    name: str
    fully_qualified_name: str
    depth: int = 0
    _type: PackageType = PackageType.REGULAR
    modules: List[PythonModule] = field(default_factory=list)
    subpackages: Dict[str, PythonPackage] = field(default_factory=dict)

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

    def walk(self):
        """
        Find subpackages and modules recursively

        Uses the pkgutil.walk_packages to search recursively for modules and subpackages. Create instances of
        PythonModule object when a module is found and append to the list of modules. Create instances of PythonPackage
        object when a subpackage is found and append to the list of packages.

        Since pkgutil.walk_packages flattens the package hierarchy, a local dictionary 'all_packages' is used to store
        all packages found (including the top-level package). New packages found are appended to the 'subpackages'
        attribute of the parent package.

        Note:
            Found subpackages and modules are imported.
            The prefix argument must be provided to 'walk_package' for it to find subpackages recursively.
        """
        # FIXME: refactor this method, not DRY enough!!!
        # FIXME: crash when path passed as string and ending with '/'

        all_packages = {self.fully_qualified_name: self}

        for _, name, is_pkg in iter_modules(path=[self.path]):
            if not is_pkg:
                imported_module = import_module(f'{self.fully_qualified_name}.{name}')
                module = PythonModule.from_imported_module(imported_module)
                module.visit()

                parent_package = all_packages[module.parent_fully_qualified_name]
                parent_package.modules.append(module)

        namespace_packages_names = find_namespace_packages(str(self.path))
        for namespace_package_name in namespace_packages_names:
            imported_package = import_module(f'{self.fully_qualified_name}.{namespace_package_name}')
            package = PythonPackage.from_imported_package(imported_package)

            all_packages[package.fully_qualified_name] = package
            parent_package = all_packages[package.parent_fully_qualified_name]
            package.depth = parent_package.depth + 1
            parent_package.subpackages[package.name] = package

            if package._type == PackageType.REGULAR:
                imported_module = import_module(package.fully_qualified_name + '.__init__')
                module = PythonModule.from_imported_module(imported_module)
                module.visit()
                if module.has_classes:
                    parent_package = all_packages[module.parent_fully_qualified_name]
                    parent_package.modules.append(module)

            for _, name, is_pkg in iter_modules(path=[package.path]):
                if not is_pkg:
                    imported_module = import_module(f'{package.fully_qualified_name}.{name}')
                    module = PythonModule.from_imported_module(imported_module)
                    module.visit()

                    parent_package = all_packages[module.parent_fully_qualified_name]
                    parent_package.modules.append(module)

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

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])

    @property
    def as_puml(self):
        # FIXME: not working yet
        indentation = self.depth * 2 * ' '

        if self.depth==0:
            lines = [f'namespace {self.fully_qualified_name} {{']
        else:
            lines = [indentation + f'namespace {self.name} {{']

        for package in self.subpackages.values():
            lines.append(package.as_puml)
        if self.subpackages:
            lines.append(indentation + '}')
        else:
            lines.append('}')

        if self.subpackages:
            return '\n'.join(lines)
        return ''.join(lines)


@dataclass
class PythonClass:
    name: str
    fully_qualified_name: str
    attributes: List = field(default_factory=list)
    methods: List = field(default_factory=list)

    @classmethod
    def from_type(cls, class_type):
        name = class_type.__name__
        fully_qualified_name = '.'.join([class_type.__module__, name])
        return PythonClass(name=name, fully_qualified_name=fully_qualified_name)

    @property
    def as_puml(self):
        lines = [f'class {self.fully_qualified_name} {{']
        for attribute in self.attributes:
            lines.append(f'  {attribute.as_puml}')
        for method in self.methods:
            lines.append(f'  {method.as_puml}')
        lines.append('}')

        return '\n'.join(lines)


@dataclass
class Relationship:
    source: str
    destination: str


class Attribute(ABC):

    def __init__(self, name, _type=None):
        self.name = name
        self._type = _type

    def __eq__(self, other):
        if isinstance(other, Attribute):
            return (self.name == other.name and self._type == other._type)
        return False

    def __ne__(self, other):
        return not self == other

    @property
    @abstractmethod
    def as_puml(self):
        pass


class ClassAttribute(Attribute):

    @property
    def as_puml(self):
        if self._type:
            return f'{self.name}: {self._type} {{static}}'
        else:
            return f'{self.name} {{static}}'


class InstanceAttribute(Attribute):

    @property
    def as_puml(self):
        if self._type:
            return f'{self.name}: {self._type}'
        else:
            return f'{self.name}'


class ClassDiagram:
    INDENT = 2

    def __init__(self, package: PythonPackage):
        self.package: PythonPackage = package
        self.classes: List[PythonClass] = package.find_all_classes()
        self.relationships = []

    def generate(self):
        yield self.header
        yield self.package.as_puml
        for _class in self.classes:
            yield _class.as_puml
        yield self.footer

    @property
    def header(self):
        return f'@startuml {self.package.fully_qualified_name}\n'

    @property
    def footer(self):
        return 'footer Generated by //py2puml//\n@enduml\n'

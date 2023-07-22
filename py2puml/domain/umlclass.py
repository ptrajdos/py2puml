from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass, field
from pkgutil import walk_packages
from pathlib import Path
from importlib import import_module


from py2puml.domain.umlitem import UmlItem


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

    def represent_as_puml(self):
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
            return ', '.join([f'{arg_type} {arg_name}' if arg_type else f'{arg_name}' for arg_name, arg_type in self.arguments.items()])
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


@dataclass
class PythonPackage:
    """ Class that represent a regular Python package with its subpackages and modules.

    Basic instantiation of objects is easily done with the 'from_imported_package' constructor method. To search
    recursively for subpackages and modules, use the 'walk' method.

    Attributes:
        path (Path): path to the Python package folder
        name (str): name of the Python package
        fully_qualified_name (str): fully qualified name of the Python package
        modules (List[PythonModule]): list of modules found in the package
        packages (List[PythonPackage]): list of subpackages found in the package"""
    path: Path
    name: str
    fully_qualified_name: str
    modules: List[PythonModule] = field(default_factory=list)
    packages: List[PythonPackage] = field(default_factory=list)

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
        return PythonPackage(path=path, name=name, fully_qualified_name=fully_qualified_name)

    def walk(self):
        """
        Find subpackages and modules recursively

        Uses the pkgutil.walk_packages to search recursively for modules and subpackages. Create instances of
        PythonModule object when a module is found and append to the list of modules. Create instances of PythonPackage
        object when a subpackage is found and append to the list of packages.

        Note:
            Found subpackages and modules are imported.
            The prefix argument must be provided to 'walk_package' for it to find subpackages recursively.
        """
        paths = [str(self.path)]
        prefix = f'{self.fully_qualified_name}.'
        for _, name, is_pkg in walk_packages(path=paths, prefix=prefix):
            if is_pkg:
                imported_package = import_module(name)
                package = PythonPackage.from_imported_package(imported_package)
                self.packages.append(package)
            else:
                imported_module = import_module(name)
                module = PythonModule.from_imported_module(imported_module)
                self.modules.append(module)

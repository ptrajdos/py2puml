from __future__ import annotations

from ast import NodeVisitor, ClassDef, ImportFrom, parse
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import List, Dict

from py2puml.classes import PythonClass, ClassVisitor


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
    classes: List[PythonClass] = field(default_factory=list)
    import_statements: Dict[str, ImportStatement] = field(default_factory=dict)
    _parent_package = None

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

    @property
    def parent_package(self):
        return self._parent_package

    @parent_package.setter
    def parent_package(self, value) -> None:
        self._parent_package = value
        value.modules.append(self)

    def visit(self):
        """ Visit AST node corresponding to the module in order to find classes. Import statement are also defined by
        this method and stored in a dictionary for faster look-up later. The fully_qualified_name property of
        ImportStatement objects is not set at this stage. It will be done by the :meth:`resolve_relative_imports´ method
        once the packages hierarchy is fully-defined. """

        with open(self.path, 'r') as fref:
            content = fref.read()

        ast = parse(content, filename=str(self.path))
        visitor = ModuleVisitor(self.fully_qualified_name)
        visitor.visit(ast)

        for _class in visitor.classes:
            _class.module = self
            self.classes.append(_class)

        for import_statement in visitor.imports:
            if import_statement.alias:
                self.import_statements[import_statement.alias] = import_statement
            else:
                self.import_statements[import_statement.name] = import_statement

    def __contains__(self, class_name):
        return class_name in [_class.name for _class in self.classes]

    def find_class_by_name(self, class_name):
        """ Find a class in a module by its name and return the corresponding PythonClass instance.

        Args:
            class_name (str): name of the class to look for

        Returns:
            An instance of PythonClass if found, otherwise returns None """

        for _class in self.classes:
            if class_name == _class.name:
                return _class
        return None

    def resolve_class_name(self, class_name: str):
        """ This method resolves a class name into a fully qualified class name.

        It verifies first if the class belongs to parent module otherwise tries to resolve from the import statements
        of the parent module. """

        if not self:
            raise AttributeError(f"Attribute 'module' in class {self.name} not initialized.")
        if class_name in self:
            return f'{self.fully_qualified_name}.{class_name}'
        elif class_name in self.import_statements.keys():
            import_statement = self.import_statements[class_name]
            imported_module_fqn = import_statement.fully_qualified_name
            return f'{imported_module_fqn}.{import_statement.name}'

        return None

    def resolve_class_pqn(self, class_pqn: str):
        """ This method resolved a partially qualified class name into a fully qualified class name.

        It tries to resolve from the import statements of the parent module. """

        tokens = class_pqn.split('.')

        if tokens[0] in self.import_statements.keys():
            import_statement = self.import_statements[tokens[0]]
            if not import_statement.fully_qualified_name:
                raise ValueError(f"Imported object '{import_statement.name}' fully qualified name missing. Run resolve_relative_import first.")
            imported_module_fqn = import_statement.fully_qualified_name
            if import_statement.alias:
                tokens[0] = import_statement.name
                class_pqn = '.'.join(tokens)
            return f'{imported_module_fqn}.{class_pqn}'

        return None

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])


class ModuleVisitor(NodeVisitor):

    def __init__(self, root_fqn):
        self.classes: List[PythonClass] = []
        self.enums = []
        self.namedtuples = []
        self.root_fqn = root_fqn
        self.imports: List[ImportStatement] = []

    def visit_ClassDef(self, node: ClassDef):
        class_type = getattr(import_module(self.root_fqn), node.name)
        _class = PythonClass.from_type(class_type)
        visitor = ClassVisitor(class_type, self.root_fqn)
        visitor.visit(node)
        for attribute in visitor.attributes:
            _class.attributes.append(attribute)
        for method in visitor.methods:
            _class.methods.append(method)
        for parent_class_pqn in visitor.parent_classes_pqn:
            _class.base_classes[parent_class_pqn] = None
        self.classes.append(_class)

    def visit_ImportFrom(self, node: ImportFrom):
        for name in node.names:
            import_statement = ImportStatement(
                module_name=node.module,
                name=name.name,
                alias=name.asname,
                level=node.level
            )
            self.imports.append(import_statement)


@dataclass
class ImportStatement:
    """ Class that represents ``import`` statement.

     In Python ``import`` statements can take several forms and the goal of this class is to provide a common
     interface for other methods to consume, for example when determining relations between classes (inheritance,
     association).

     The simplest form an import statement is shown below:

     ..code:: python
         import <module_name>

    Individual objects in a module can also be directly imported as shown in the example below. In this context
    objects can be for example: classes, module variables, other modules, packages, ... Several objects can be
    imported in the same statement if objects are separated by a comma.

    ..code:: python
        from <module_name> import <name>
        from <module_name> import <name1>, <name2>

    The last form of import statement allows importing individual object with alternate names (called *alias*).

    .. code:: python
        from <module_name> import <name> as <alias>

    You can also import an entire module under an alternate name:

    .. code:: python
        import <module_name> as <alias>

    On top of that import statements can be defined absolutely or relatively. Absolute import statements are specified
    as dot-separated full path from the project's root folder whereas relative import statements are specified
    relatively to where the import statement is. In relative import statements, module are prepended by one or more
    dot(s): a single dot (level 1) means that the referenced module (or package) is in the same folder of the current
    location. Two dots (level 2) stand for the parent directory of the current location, three dots (level 3) stand for
    the grandparent directory of the current location, and so on ...

    ImportStatement objects are fully initialized in a two-step process. Objects are instantiated first by parsing the
    AST of an import statement, which will define the attributes: ``module_name``, ``name``, ``alias`` and ``level``.
    The module name in its canonical form is stored in the ``fully_qualified_name`` attribute which is set by running
    the  :meth:`resolve_relative_import`. This can be done only once all modules and packages have been instantiated and
    their hierarchy established (with the :meth:`PythonPackage.walk` method)

    Args:
        module_name (str): qualified module name to be resolved. It should not be prepended by any '.' character, these
        are instead reflected by the value of :attr:`level`. Note that this can also represent a package name.
        name (str): name of the object to be imported.
        alias (str): alternate name of the object to be imported.
        level (int): how many level relative to the current module (self) should the module_name be resolved (0
        corresponds to an absolute import.
        fully_qualified_name (str): module/package name in its canonical form. """

    module_name: str
    name: str
    alias: str = None
    level: int = 0
    fully_qualified_name: str = None

    def resolve_relative_import(self, module: PythonModule) -> None:
        """ This method resolves relative qualified module names to a fully qualified module name.

        Args:
            module (PythonModule): module containing the import statement """
        if self.level == 0:
            raise ValueError(f"Imported object '{self.name}' is an absolute import. Only relative import are supported by 'resolve_relative_import'")

        parent = module
        level = self.level
        while level > 0:
            if not parent.parent_package:
                raise(Exception(f'Could not resolve relative import from {self.module_name} since package {module.fully_qualified_name} has no parent.'))
            parent = parent.parent_package
            level -= 1
        self.fully_qualified_name = f'{parent.fully_qualified_name}.{self.module_name}'

    @property
    def is_relative(self):
        return self.level > 0

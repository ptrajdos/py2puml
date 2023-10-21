from typing import Iterable
from pathlib import Path

from py2puml.domain.umlclass import PythonPackage, ClassDiagram, PackageType


def py2puml(domain_path: str, domain_module: str) -> Iterable[str]:

    package_name = domain_module.split('.')[-1]
    init_pathfile = Path(domain_path) / '__init__.py'
    if init_pathfile.is_file():
        package_type = PackageType.REGULAR
    else:
        package_type = PackageType.NAMESPACE
    package = PythonPackage(path=domain_path, name=package_name, fully_qualified_name=domain_module, _type=package_type)

    package.walk()
    package.resolve_relative_imports()
    package.resolve_class_inheritance()

    diagram = ClassDiagram(package=package)
    diagram.define_relations()

    return diagram.generate()

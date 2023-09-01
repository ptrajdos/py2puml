from typing import List, Tuple

from pytest import mark

from py2puml.domain.package import Package
from py2puml.export.namespace import get_or_create_module_package, visit_package


@mark.parametrize(['root_package', 'module_qualified_name'], [
    (Package(None), 'py2puml'),
    (Package(None, [Package('py2puml')]), 'py2puml'),
    (Package(None), 'py2puml.export.namespace'),
])
def test_get_or_create_module_package(root_package: Package, module_qualified_name: str):
    module_parts = module_qualified_name.split('.')
    module_package = get_or_create_module_package(root_package, module_parts)
    assert module_package.name == module_parts[-1], 'the module package has the expected name'

    # checks that the hierarchy of intermediary nested packages has been created if necessary
    inner_package = root_package
    for module_name in module_parts:
        inner_package = next(
            child_package for child_package in inner_package.children
            if child_package.name == module_name
        )

    assert inner_package == module_package, f'the module package is contained in the {module_qualified_name} hierarchy'


NO_CHILDREN_PACKAGES = []

SAMPLE_ROOT_PACKAGE = Package(None, [
    Package('py2puml',[
        Package('domain', [
            Package('package', NO_CHILDREN_PACKAGES, 1),
            Package('umlclass', NO_CHILDREN_PACKAGES, 1)
        ]),
        Package('inspection', [
            Package('inspectclass', NO_CHILDREN_PACKAGES, 1)
        ])
    ])
])
SAMPLE_NAMESPACE_LINES = '''namespace py2puml {
  namespace domain {
    namespace package {}
    namespace umlclass {}
  }
  namespace inspection.inspectclass {}
}'''

@mark.parametrize(
    ['package_to_visit', 'parent_namespace_names', 'indentation_level', 'expected_namespace_lines'],
    [
        (Package(None), tuple(), 0, []), # the root package yields no namespace documentation
        (Package(None, NO_CHILDREN_PACKAGES, 1), tuple(), 0, ['namespace  {}\n']), # the root package yields namespace documentation if it has uml items
        (Package(None, NO_CHILDREN_PACKAGES, 1), tuple(), 1, ['  namespace  {}\n']), # indentation level of 1 -> 2 spaces
        (Package(None, NO_CHILDREN_PACKAGES, 1), tuple(), 3, ['      namespace  {}\n']), # indentation level of 3 -> 6 spaces
        (Package('umlclass', NO_CHILDREN_PACKAGES, 2), ('py2puml', 'domain'), 0, ['namespace py2puml.domain.umlclass {}\n']),
        (SAMPLE_ROOT_PACKAGE, tuple(), 0, (f'{line}\n' for line in SAMPLE_NAMESPACE_LINES.split('\n'))),
    ]
)
def test_visit_package(
    package_to_visit: Package,
    parent_namespace_names: Tuple[str],
    indentation_level: int,
    expected_namespace_lines: List[str]
):
    for expected_namespace_line, namespace_line in zip(
        expected_namespace_lines,
        visit_package(package_to_visit, parent_namespace_names, indentation_level)
    ):
        assert expected_namespace_line == namespace_line

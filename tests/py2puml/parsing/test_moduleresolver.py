from typing import List, Dict
from pytest import mark

from py2puml.parsing.moduleresolver import ModuleResolver, NamespacedType

from tests.py2puml.parsing.mockedinstance import MockedInstance


def assert_NamespacedType(namespaced_type: NamespacedType, full_namespace_type: str, short_type: str):
    assert namespaced_type.full_namespace == full_namespace_type
    assert namespaced_type.type_name == short_type


def test_ModuleResolver_resolve_full_namespace_type():
    source_module = MockedInstance({
        '__name__': 'tests.modules.withconstructor',
        'modules': {
            'withenum': {
                'TimeUnit': {
                    '__module__': 'tests.modules.withenum',
                    '__name__': 'TimeUnit'
                }
            }
        },
        'withenum': {
            'TimeUnit': {
                '__module__': 'tests.modules.withenum',
                '__name__': 'TimeUnit'
            }
        },
        'Coordinates': {
            '__module__': 'tests.modules.withconstructor',
            '__name__': 'Coordinates'
        }
    })
    module_resolver = ModuleResolver(source_module)
    assert_NamespacedType(module_resolver.resolve_full_namespace_type(
        'modules.withenum.TimeUnit'
    ), 'tests.modules.withenum.TimeUnit', 'TimeUnit')
    assert_NamespacedType(module_resolver.resolve_full_namespace_type(
        'withenum.TimeUnit'
    ), 'tests.modules.withenum.TimeUnit', 'TimeUnit')
    assert_NamespacedType(module_resolver.resolve_full_namespace_type(
        'Coordinates'
    ), 'tests.modules.withconstructor.Coordinates', 'Coordinates')


def test_ModuleResolver_get_module_full_name():
    source_module = MockedInstance({
        '__name__': 'tests.modules.withconstructor'
    })
    module_resolver = ModuleResolver(source_module)
    assert module_resolver.get_module_full_name() == 'tests.modules.withconstructor'


@mark.parametrize(['full_annotation', 'short_annotation', 'namespaced_definitions', 'module_dict'], [
    (
        # domain.people was imported, people.Person is used
        'people.Person',
        'Person',
        ['domain.people.Person'],
        {
            '__name__': 'testmodule',
            'people': {
                'Person': {
                    '__module__': 'domain.people',
                    '__name__': 'Person'
                }
            }
        }
    ),
    (
        # combination of compound types
        'Dict[id.Identifier,typing.List[domain.Person]]',
        'Dict[Identifier, List[Person]]',
        ['typing.Dict', 'id.Identifier', 'typing.List', 'domain.Person'],
        {
            '__name__': 'testmodule',
            'Dict': Dict,
            'List': List,
            'id': {
                'Identifier': {
                    '__module__': 'id',
                    '__name__': 'Identifier',
                }
            },
            'domain': {
                'Person': {
                    '__module__': 'domain',
                    '__name__': 'Person',
                }
            }
        }
    )
])
def test_shorten_compound_type_annotation(full_annotation: str, short_annotation, namespaced_definitions: List[str], module_dict: dict):
    module_resolver = ModuleResolver(MockedInstance(module_dict))
    shortened_annotation, full_namespaced_definitions = module_resolver.shorten_compound_type_annotation(full_annotation)
    assert shortened_annotation == short_annotation
    assert full_namespaced_definitions == namespaced_definitions

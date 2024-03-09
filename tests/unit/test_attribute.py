import pytest

from py2puml.attribute import InstanceAttribute, ClassAttribute, Attribute


class TestClassAttributes:

    @pytest.fixture(scope="function", autouse=True)
    def typed_attribute(self):
        return ClassAttribute(name='PI', type_expr='float')

    @pytest.fixture(scope="function", autouse=True)
    def untyped_attribute(self):
        return ClassAttribute(name='origin')

    def test_constructor_typed(self):
        class_attribute = ClassAttribute(name='PI', type_expr='float')
        assert isinstance(class_attribute, Attribute)
        assert isinstance(class_attribute, ClassAttribute)
        assert 'PI' == class_attribute.name
        assert 'float' == class_attribute.type_expr

    def test_constructor_untyped(self):
        class_attribute = ClassAttribute(name='origin')
        assert isinstance(class_attribute, Attribute)
        assert isinstance(class_attribute, ClassAttribute)
        assert 'origin' == class_attribute.name
        assert class_attribute.type_expr is None

    def test_as_puml_typed(self, typed_attribute):
        expected_result = 'PI: float {static}'
        assert expected_result == typed_attribute.as_puml

    def test_as_puml_untyped(self, untyped_attribute):
        expected_result = 'origin {static}'
        assert expected_result == untyped_attribute.as_puml


class TestInstanceAttributes:

    @pytest.fixture(scope="function", autouse=True)
    def typed_attribute(self):
        return InstanceAttribute(name='attribute1', type_expr='int')

    @pytest.fixture(scope="function", autouse=True)
    def untyped_attribute(self):
        return InstanceAttribute(name='attribute2')

    def test_constructor_typed(self):
        class_attribute = InstanceAttribute(name='attribute1', type_expr='int')
        assert isinstance(class_attribute, Attribute)
        assert isinstance(class_attribute, InstanceAttribute)
        assert 'attribute1' == class_attribute.name
        assert 'int', class_attribute.type_expr

    def test_constructor_untyped(self):
        class_attribute = InstanceAttribute(name='attribute2')
        assert isinstance(class_attribute, Attribute)
        assert isinstance(class_attribute, InstanceAttribute)
        assert 'attribute2' == class_attribute.name
        assert class_attribute.type_expr is None

    def test_as_puml_typed(self, typed_attribute):
        expected_result = 'attribute1: int'
        assert expected_result == typed_attribute.as_puml

    def test_as_puml_untyped(self, untyped_attribute):
        expected_result = 'attribute2'
        assert expected_result == untyped_attribute.as_puml


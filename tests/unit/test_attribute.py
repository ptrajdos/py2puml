import unittest

from py2puml.attribute import InstanceAttribute, ClassAttribute, Attribute


class TestClassAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.typed_attribute = ClassAttribute(name='PI', type_expr='float')
        self.untyped_attribute = ClassAttribute(name='origin')

    def test_constructor_typed(self):
        class_attribute = ClassAttribute(name='PI', type_expr='float')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('PI', class_attribute.name)
        self.assertEqual('float', class_attribute.type_expr)

    def test_constructor_untyped(self):
        class_attribute = ClassAttribute(name='origin')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('origin', class_attribute.name)
        self.assertIsNone(class_attribute.type_expr)

    def test_as_puml_typed(self):
        expected_result = 'PI: float {static}'
        actual_result = self.typed_attribute.as_puml
        self.assertEqual(expected_result, actual_result)

    def test_as_puml_untyped(self):
        expected_result = 'origin {static}'
        actual_result = self.untyped_attribute.as_puml
        self.assertEqual(expected_result, actual_result)


class TestInstanceAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.typed_attribute = InstanceAttribute(name='attribute1', type_expr='int')
        self.untyped_attribute = InstanceAttribute(name='attribute2')

    def test_constructor_typed(self):
        class_attribute = InstanceAttribute(name='attribute1', type_expr='int')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, InstanceAttribute)
        self.assertEqual('attribute1', class_attribute.name)
        self.assertEqual('int', class_attribute.type_expr)

    def test_constructor_untyped(self):
        class_attribute = InstanceAttribute(name='attribute2')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, InstanceAttribute)
        self.assertEqual('attribute2', class_attribute.name)
        self.assertIsNone(class_attribute.type_expr)

    def test_as_puml_typed(self):
        expected_result = 'attribute1: int'
        actual_result = self.typed_attribute.as_puml
        self.assertEqual(expected_result, actual_result)

    def test_as_puml_untyped(self):
        expected_result = 'attribute2'
        actual_result = self.untyped_attribute.as_puml
        self.assertEqual(expected_result, actual_result)


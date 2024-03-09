from ast import parse

from py2puml.methods import DecoratorVisitor, TypeVisitor, AssignmentVisitor, AttributeAssignment, ConstructorVisitor
from py2puml.classes import InstanceAttribute


class TestDecoratorVisitor:

    def test_visit(self):
        source_code = '@staticmethod\nclass DummyClass:\n    pass'
        ast = parse(source_code)
        decorator_node = ast.body[0].decorator_list[0]
        visitor = DecoratorVisitor()
        visitor.visit(decorator_node)
        assert 'staticmethod' == visitor.decorator_type

    def test_visit_2(self):
        source_code = '@unittest.mock.patch\nclass DummyClass:\n    pass'
        ast = parse(source_code)
        decorator_node = ast.body[0].decorator_list[0]
        visitor = DecoratorVisitor()
        visitor.visit(decorator_node)
        assert 'unittest.mock.patch' == visitor.decorator_type


class TestConstructorVisitor2:

    def test_attribute(self):
        source_code = 'def __init__(self, xx):\n    self.x = xx + 1\n    a = xx + self.x -2'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = ConstructorVisitor()
        visitor.visit(node)
        expected_attributes = [InstanceAttribute(name='x')]
        actual_attributes = list(visitor.instance_attributes.values())
        assert expected_attributes == actual_attributes

    def test_attribute_with_type(self):
        source_code = 'def __init__(self, xx: int):\n    a = 2\n    self.x = xx + a'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = ConstructorVisitor()
        visitor.visit(node)
        expected_attributes = [InstanceAttribute(name='x', type_expr='int')]
        actual_attributes = list(visitor.instance_attributes.values())
        assert expected_attributes == actual_attributes

    def test_attribute_with_annotation(self):
        source_code = 'def __init__(self, xx):\n    self.x: int = xx\n    a = 2\n    self.y = 3'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = ConstructorVisitor()
        visitor.visit(node)
        expected_attributes = [InstanceAttribute(name='x', type_expr='int'),
                               InstanceAttribute(name='y', type_expr=None)]
        actual_attributes = list(visitor.instance_attributes.values())
        assert expected_attributes == actual_attributes

    def test_multiple_attributes(self):
        source_code = 'def __init__(self, xx: int, yy: str):\n    self.x, self.y = xx, yy + 1'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = ConstructorVisitor()
        visitor.visit(node)
        expected_attributes = [InstanceAttribute(name='x', type_expr='int'),
                               InstanceAttribute(name='y', type_expr='str')]
        actual_attributes = list(visitor.instance_attributes.values())
        assert expected_attributes == actual_attributes


class TestAssignmentVisitor:

    def test_attribute_not_annotated(self):
        source_code = 'self.x = xx + a'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        expected_assignments = [AttributeAssignment(InstanceAttribute('x'), ['xx', 'a'])]
        assert expected_assignments == visitor.attribute_assignments

    def test_variable(self):
        source_code = 'a = 2'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        assert not visitor.attribute_assignments

    def test_variable_annotated(self):
        source_code = 'a: int = 2'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        assert not visitor.attribute_assignments

    def test_attribute_annotated(self):
        source_code = 'self.x: int = xx'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        expected_assignments = [AttributeAssignment(InstanceAttribute('x', 'int'), ['xx'])]
        assert expected_assignments == visitor.attribute_assignments

    def test_multiple_attribute(self):
        source_code = 'self.x, self.y = xx, yy + 1'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        expected_assignments = [
            AttributeAssignment(InstanceAttribute('x'), ['xx']),
            AttributeAssignment(InstanceAttribute('y'), ['yy'])]
        assert expected_assignments == visitor.attribute_assignments

    def test_attribute_name(self):
        """ Test multiple assignment with a mix of Attribute and Name AST nodes."""
        source_code = 'self.x, a, self.y = xx, 3, yy + 1'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        expected_assignments = [
            AttributeAssignment(InstanceAttribute('x'), ['xx']),
            AttributeAssignment(InstanceAttribute('y'), ['yy'])]
        assert expected_assignments == visitor.attribute_assignments

    def test_attributes(self):
        """ Test multiple assignment with Attribute nodes, both instance variables and variables. """
        source_code = 'self.x, other.z, self.y = xx, 3, yy + 1'
        ast = parse(source_code)
        node = ast.body[0]
        visitor = AssignmentVisitor()
        visitor.visit(node)
        expected_assignments = [
            AttributeAssignment(InstanceAttribute('x'), ['xx']),
            AttributeAssignment(InstanceAttribute('y'), ['yy'])]
        assert expected_assignments == visitor.attribute_assignments


class TestTypeVisitor:

    def test_return_type_int(self):
        source_code = 'def dummy_function() -> int:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'int'
        assert expected_rtype == actual_rtype

    def test_return_type_compound(self):
        """ Test non-nested compound datatype"""
        source_code = 'def dummy_function() -> Tuple[float, str]:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Tuple[float, str]'
        assert expected_rtype == actual_rtype

    def test_return_type_compound_2(self):
        """ Test non-nested compound datatype"""
        source_code = 'def dummy_function() -> Tuple[float, withenum.TimeUnit]:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Tuple[float, TimeUnit]'
        assert expected_rtype == actual_rtype

    def test_return_type_compound_nested(self):
        """ Test nested compound datatype"""
        source_code = 'def dummy_function() -> Tuple[float, Dict[str, List[bool]]]:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Tuple[float, Dict[str, List[bool]]]'
        assert expected_rtype == actual_rtype

    def test_return_type_user_defined(self):
        """ Test user-defined class datatype"""
        source_code = 'def dummy_function() -> Point:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'Point'
        assert expected_rtype == actual_rtype

    def test_return_type_user_defined_2(self):
        """ Test user-defined class datatype"""
        source_code = 'def dummy_function() -> modules.withenum.TimeUnit:\n     pass'
        ast = parse(source_code)
        node = ast.body[0].returns
        visitor = TypeVisitor()
        actual_rtype = visitor.visit(node)
        expected_rtype = 'TimeUnit'
        assert expected_rtype == actual_rtype

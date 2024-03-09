from pathlib import Path
from pytest import mark

from py2puml.asserts import assert_py2puml_is_file_content


CURRENT_DIR = Path(__file__).parent
TESTS_DIR = CURRENT_DIR.parent
DATA_DIR = TESTS_DIR / "data"

test_data = [
    ('tests/modules/withnestednamespace', 'tests.modules.withnestednamespace'),
    ('tests/modules/withsubdomain', 'tests.modules.withsubdomain'),
    ('tests/modules/withmethods', 'tests.modules.withmethods')
]


@mark.skip(reason="If the purpose of this test is to generate doc, do it somewhere else.")
def test_py2puml_model_on_py2uml_domain():
    """
    Ensures that the documentation of the py2puml domain model is up-to-date
    """
    domain_diagram_file_path = CURRENT_DIR.parent.parent / 'py2puml' / 'py2puml.domain.puml'

    assert_py2puml_is_file_content('py2puml/domain', 'py2puml.domain', domain_diagram_file_path)


@mark.xfail(reason='Composition relation not implemented')
@mark.parametrize("path, module", test_data)
def test_py2puml(path, module):
    expected_filepath = DATA_DIR / f"{module}.puml"
    assert_py2puml_is_file_content(path, module, DATA_DIR / expected_filepath)

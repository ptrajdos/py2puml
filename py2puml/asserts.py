from io import StringIO
from pathlib import Path
from typing import Iterable, List, Union

from py2puml.py2puml import py2puml


def assert_py2puml_is_file_content(domain_path: str, domain_module: str, diagram_filepath: Union[str, Path]):
    # reads the existing class diagram
    with open(diagram_filepath, 'r', encoding='utf8') as expected_puml_file:
        assert_py2puml_is_stringio(domain_path, domain_module, expected_puml_file)


def assert_py2puml_is_stringio(domain_path: str, domain_module: str, expected_content_stream: StringIO):
    # generates the PlantUML documentation
    puml_content = list(py2puml(domain_path, domain_module))
    actual_content = []
    for item in puml_content:
        tokens = item.split("\n")
        actual_content.extend(tokens)
    actual_content = [f"{item}\n" for item in actual_content if item]
    assert_multilines(actual_content, expected_content_stream)


def assert_multilines(actual_multilines: List[str], expected_multilines: Iterable[str]):
    line_index = 0
    for line_index, (actual_line, expected_line) in enumerate(zip(actual_multilines, expected_multilines)):
        # print(actual_line[:-1])
        assert actual_line == expected_line, f"Content mismatch at line {line_index + 1}:\n    Actual   |{actual_line}    Expected |{expected_line}"

    assert line_index + 1 == len(actual_multilines), f'actual and expected diagrams have {line_index + 1} lines'
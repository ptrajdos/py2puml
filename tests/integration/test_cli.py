from io import StringIO
from subprocess import run, PIPE
from typing import List
from pathlib import Path

from pytest import mark

from py2puml.asserts import assert_multilines
from py2puml.py2puml import py2puml

from tests import __version__, __description__


CURRENT_DIR = Path(__file__).parent
TESTS_DIR = CURRENT_DIR.parent
DATA_DIR = TESTS_DIR / "data"


@mark.parametrize(
    'entrypoint', [
        ['py2puml'],
        ['python', '-m', 'py2puml']
    ]
)
def test_cli_consistency_with_the_default_configuration(entrypoint: List[str]):
    command = entrypoint + ['tests/modules/withmethods', 'tests.modules.withmethods']
    cli_stdout = run(command,
        stdout=PIPE, stderr=PIPE,
        text=True, check=True
    ).stdout

    puml_content = py2puml('tests/modules/withmethods', 'tests.modules.withmethods')

    assert ''.join(puml_content).strip() == cli_stdout.strip()


@mark.xfail(reason='Composition relation not implemented')
def test_cli_on_specific_working_directory():
    command = ['py2puml', 'withrootnotincwd', 'withrootnotincwd']
    cli_process = run(command,
        stdout=PIPE, stderr=PIPE,
        text=True, check=True,
        cwd='tests/modules'
    )

    with open(DATA_DIR / 'withrootnotincwd.puml', 'r', encoding='utf8') as expected_puml_file:
        assert_multilines(
            # removes the last return carriage added by the stdout
            [line for line in StringIO(cli_process.stdout)][:-1],
            expected_puml_file
        )


@mark.parametrize(
    'version_command', [
        ['-v'],
        ['--version']
    ]
)
def test_cli_version(version_command: List[str]):
    '''
    Ensures the consistency between the CLI version and the project version set in pyproject.toml
    which is not included when the CLI is installed system-wise
    '''
    command = ['py2puml'] + version_command
    cli_version = run(command,
        stdout=PIPE, stderr=PIPE,
        text=True, check=True
    ).stdout

    assert cli_version == f'py2puml {__version__}\n'

@mark.parametrize(
    'help_command', [
        ['-h'],
        ['--help']
    ]
)
def test_cli_help(help_command: List[str]):
    '''
    Ensures the consistency between the CLI help and the project description set in pyproject.toml
    which is not included when the CLI is installed system-wise
    '''
    command = ['py2puml'] + help_command
    help_text = run(command,
        stdout=PIPE, stderr=PIPE,
        text=True, check=True
    ).stdout.replace('\n', ' ')

    assert __description__ in help_text

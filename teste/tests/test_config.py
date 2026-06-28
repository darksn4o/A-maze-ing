"""Unit tests for the configuration parser and the output serializer."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, load_config
from app.output import render_output
from mazegen import MazeGenerator

_VALID = """
# a comment
WIDTH=10
HEIGHT=8
ENTRY=0,0
EXIT=9,7
OUTPUT_FILE=out.txt
PERFECT=True
SEED=1
"""


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "config.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_load_valid(tmp_path: Path) -> None:
    """A well-formed file parses into the expected values."""
    config = load_config(_write(tmp_path, _VALID))
    assert config.width == 10
    assert config.entry == (0, 0)
    assert config.exit == (9, 7)
    assert config.perfect is True
    assert config.seed == 1


def test_missing_file() -> None:
    """A missing file raises ConfigError, not OSError."""
    with pytest.raises(ConfigError):
        load_config("/does/not/exist.txt")


def test_missing_key(tmp_path: Path) -> None:
    """Omitting a mandatory key is reported."""
    text = "WIDTH=5\nHEIGHT=5\nENTRY=0,0\nEXIT=4,4\nPERFECT=True\n"
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, text))


def test_endpoint_out_of_bounds(tmp_path: Path) -> None:
    """An out-of-bounds exit is rejected at config time."""
    text = _VALID.replace("EXIT=9,7", "EXIT=99,99")
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, text))


def test_bad_syntax(tmp_path: Path) -> None:
    """A line without '=' is reported."""
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, _VALID + "\nGARBAGE\n"))


def test_output_format_shape() -> None:
    """The serialized output has the mandatory five-block structure."""
    maze = MazeGenerator(10, 8, entry=(0, 0), exit=(9, 7), seed=1).generate()
    text = render_output(maze)
    assert text.endswith("\n")
    lines = text.split("\n")[:-1]  # drop trailing empty from final newline
    # 8 grid rows + empty line + entry + exit + path = 12 lines
    assert len(lines) == maze.height + 4
    assert lines[maze.height] == ""        # separator
    assert lines[maze.height + 1] == "0,0"  # entry
    assert lines[maze.height + 2] == "9,7"  # exit
    # every grid cell is a single hex digit
    for row in lines[:maze.height]:
        assert len(row) == maze.width
        assert all(ch in "0123456789ABCDEF" for ch in row)

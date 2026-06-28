"""Parsing and validation of the ``KEY=VALUE`` configuration file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

Cell = tuple[int, int]

_MANDATORY_KEYS = (
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
)
_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


class ConfigError(Exception):
    """Raised on any problem with the configuration file."""


@dataclass
class Config:
    """Validated maze configuration.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        entry: Entry coordinates ``(x, y)``.
        exit: Exit coordinates ``(x, y)``.
        output_file: Path of the hexadecimal output file.
        perfect: Whether the maze must have a single entry-to-exit path.
        seed: Optional random seed (``SEED`` key).
        draw_42: Whether to embed the "42" pattern (``PATTERN`` key).
        animate: Whether to animate the generation (``ANIMATE`` key).
        animation_speed: Animation speed multiplier (``ANIMATION_SPEED`` key);
            ``1.0`` is the default, below ``1`` is slower, above ``1`` faster.
    """

    width: int
    height: int
    entry: Cell
    exit: Cell
    output_file: str
    perfect: bool
    seed: Optional[int] = None
    draw_42: bool = True
    animate: bool = True
    animation_speed: float = 1.0


def _parse_pairs(text: str) -> dict[str, str]:
    """Turn the raw file content into a ``KEY -> VALUE`` mapping.

    Args:
        text: Whole content of the configuration file.

    Returns:
        Mapping of upper-cased keys to their string value.

    Raises:
        ConfigError: On a malformed line or a duplicated key.
    """
    pairs: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()  # drop full-line/inline comments
        if not line:
            continue
        if "=" not in line:
            raise ConfigError(f"line {number}: missing '=' in {raw!r}")
        key, value = line.split("=", 1)
        key = key.strip().upper()
        if not key:
            raise ConfigError(f"line {number}: empty key in {raw!r}")
        if key in pairs:
            raise ConfigError(f"line {number}: duplicated key {key!r}")
        pairs[key] = value.strip()
    return pairs


def _to_int(key: str, value: str) -> int:
    """Convert a value to ``int`` or raise a :class:`ConfigError`."""
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {value!r}") from exc


def _to_float(key: str, value: str) -> float:
    """Convert a value to ``float`` or raise a :class:`ConfigError`."""
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number, got {value!r}") from exc


def _to_cell(key: str, value: str) -> Cell:
    """Convert an ``x,y`` value to a coordinate tuple."""
    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must look like 'x,y', got {value!r}")
    return _to_int(key, parts[0].strip()), _to_int(key, parts[1].strip())


def _to_bool(key: str, value: str) -> bool:
    """Convert a value to ``bool`` accepting common spellings."""
    low = value.strip().lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    raise ConfigError(f"{key} must be true/false, got {value!r}")


def load_config(path: str) -> Config:
    """Read, parse and validate a configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        A fully validated :class:`Config`.

    Raises:
        ConfigError: If the file is missing, unreadable, incomplete or holds
            invalid values (out-of-bounds endpoints, equal endpoints, ...).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    pairs = _parse_pairs(text)
    missing = [key for key in _MANDATORY_KEYS if key not in pairs]
    if missing:
        raise ConfigError(f"missing mandatory key(s): {', '.join(missing)}")

    width = _to_int("WIDTH", pairs["WIDTH"])
    height = _to_int("HEIGHT", pairs["HEIGHT"])
    if width < 1 or height < 1:
        raise ConfigError("WIDTH and HEIGHT must be positive")

    entry = _to_cell("ENTRY", pairs["ENTRY"])
    exit_ = _to_cell("EXIT", pairs["EXIT"])
    for name, (x, y) in (("ENTRY", entry), ("EXIT", exit_)):
        if not (0 <= x < width and 0 <= y < height):
            raise ConfigError(f"{name} {(x, y)} is outside the maze bounds")
    if entry == exit_:
        raise ConfigError("ENTRY and EXIT must be different cells")

    seed = _to_int("SEED", pairs["SEED"]) if "SEED" in pairs else None
    draw_42 = _to_bool("PATTERN", pairs["PATTERN"]) if "PATTERN" in pairs \
        else True
    animate = _to_bool("ANIMATE", pairs["ANIMATE"]) if "ANIMATE" in pairs \
        else True
    speed = _to_float("ANIMATION_SPEED", pairs["ANIMATION_SPEED"]) \
        if "ANIMATION_SPEED" in pairs else 1.0
    if speed <= 0:
        raise ConfigError("ANIMATION_SPEED must be a positive number")

    return Config(
        width=width,
        height=height,
        entry=entry,
        exit=exit_,
        output_file=pairs["OUTPUT_FILE"],
        perfect=_to_bool("PERFECT", pairs["PERFECT"]),
        seed=seed,
        draw_42=draw_42,
        animate=animate,
        animation_speed=speed,
    )

# this_file: tests/test_placement.py
"""Placement geometry and real CLI regression tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree

from vexylicon import VexyliconGenerator, VexyliconParams

ARTWORK = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 200 100">'
    '<rect x="10" y="20" width="200" height="100" fill="red"/></svg>'
)


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"scale": 0.8}, (120, 120, 960, 960)),
        ({"scale": 1.5, "x_off": -40, "y_off": 60}, (-340, -240, 1800, 1800)),
        ({"size": 600}, (300, 300, 600, 600)),
        ({"size": 600, "scale": 0.5, "x_off": 30, "y_off": -20}, (480, 430, 300, 300)),
    ],
)
def test_payload_is_scaled_about_canvas_centre_then_offset(options: dict[str, float], expected: tuple) -> None:
    generator = VexyliconGenerator(params=VexyliconParams(steps=2, **options))
    root = etree.fromstring(generator.generate(ARTWORK).encode())
    artwork = root.find('.//*[@id="payload"]/{*}svg')
    geometry = tuple(float(artwork.get(key)) for key in ("x", "y", "width", "height"))
    assert geometry == expected, "Placement must use canvas units and centre-based scaling"
    assert artwork.get("viewBox") == "10 20 200 100", "Source coordinates must survive"
    assert root.find('.//*[@id="payload"]').get("clip-path") == "url(#borderClip)"
    assert root.get("viewBox") == "0 0 1200 1200", "Placement must not resize the glass frame"


@pytest.mark.parametrize(
    "options",
    [
        {"scale": 0},
        {"scale": -1},
        {"scale": float("nan")},
        {"size": 0},
        {"size": float("inf")},
        {"x_off": float("inf")},
        {"y_off": float("nan")},
    ],
)
def test_invalid_placement_is_rejected(options: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="finite|positive"):
        VexyliconParams(**options)


def run_cli(*args: str | Path) -> subprocess.CompletedProcess[str]:
    """Run the actual Fire entry point, including parsing and exit status."""
    return subprocess.run(  # noqa: S603 -- fixed Python entry point and local test arguments
        [sys.executable, "-m", "vexylicon.cli", *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1"},
    )


def test_create_cli_accepts_relative_scale_and_negative_offsets(tmp_path: Path) -> None:
    source = tmp_path / "art.svg"
    source.write_text(ARTWORK)
    output = tmp_path / "out.svg"
    result = run_cli(
        "create", "--payload", source, "--output", output, "--scale=0.8", "--x_off=-40", "--y_off=20", "--steps=2"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    artwork = etree.parse(str(output)).find('.//*[@id="payload"]/{*}svg')
    assert (artwork.get("x"), artwork.get("y"), artwork.get("width")) == ("80", "140", "960")


def test_batch_cli_absolute_size_and_in_place_suffix_are_repeatable(tmp_path: Path) -> None:
    source = tmp_path / "art.svg"
    source.write_text(ARTWORK)
    original = source.read_bytes()
    for _ in range(2):
        result = run_cli(
            "batch", tmp_path, tmp_path, "--size=600", "--x_off=25", "--y_off=-10", "--suffix=-icon", "--steps=2"
        )
        assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(p.name for p in tmp_path.glob("*.svg")) == ["art-icon.svg", "art.svg"]
    assert source.read_bytes() == original, "In-place batch must preserve original SVGs"
    artwork = etree.parse(str(tmp_path / "art-icon.svg")).find('.//*[@id="payload"]/{*}svg')
    assert (artwork.get("x"), artwork.get("y"), artwork.get("width")) == ("325", "290", "600")


def test_invalid_create_cli_options_fail_without_output(tmp_path: Path) -> None:
    output = tmp_path / "out.svg"
    result = run_cli("create", "--output", output, "--scale=-1")
    assert result.returncode != 0, "Invalid scale must set a failure exit status"
    assert not output.exists(), "Invalid placement must not create an output"


def test_batch_failure_returns_nonzero(tmp_path: Path) -> None:
    source = tmp_path / "bad.svg"
    source.write_text("<broken")
    result = run_cli("batch", tmp_path, tmp_path / "out", "--steps=2")
    assert result.returncode != 0, "A failed batch must be visible to wrapper scripts"

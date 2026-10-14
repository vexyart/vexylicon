#!/usr/bin/env -S uv run -s
# this_file: tests/test_core.py
"""Tests for core Vexylicon functionality."""

import pytest
from lxml import etree

from vexylicon import VexyliconGenerator, VexyliconParams
from vexylicon.core import InvalidSVGError, OpacityProgression


def test_vexylicon_generator_creation():
    """Test basic generator creation."""
    generator = VexyliconGenerator()
    assert generator is not None
    assert generator.theme.name == "default"
    assert generator.params.steps == 24


def test_vexylicon_params():
    """Test parameter configuration."""
    params = VexyliconParams(
        steps=16,
        opacity_start=0.8,
        opacity_end=0.1,
        opacity_progression=OpacityProgression.LINEAR,
    )
    assert params.steps == 16
    assert params.opacity_start == 0.8
    assert params.opacity_end == 0.1
    assert params.opacity_progression == OpacityProgression.LINEAR


def test_quality_presets():
    """Test quality preset application."""
    params_low = VexyliconParams(quality="low")
    assert params_low.steps == 8

    params_high = VexyliconParams(quality="high")
    assert params_high.steps == 24

    params_ultra = VexyliconParams(quality="ultra")
    assert params_ultra.steps == 32


def test_basic_generation():
    """Test basic SVG generation without payload."""
    generator = VexyliconGenerator()
    result = generator.generate()

    # Check it's valid SVG
    assert result.startswith("<?xml")
    assert "<svg" in result
    assert "</svg>" in result

    # Check for expected elements
    assert 'id="bevelSteps"' in result
    assert 'mix-blend-mode="screen"' in result


def test_invalid_svg_handling():
    """Test handling of invalid SVG input."""
    generator = VexyliconGenerator()

    # Test with invalid payload
    with pytest.raises(InvalidSVGError):
        generator.generate(payload_svg="<not valid xml>")


def test_opacity_calculation():
    """Test opacity calculation for different modes."""
    params = VexyliconParams(steps=4, opacity_progression=OpacityProgression.LINEAR)
    generator = VexyliconGenerator(params=params)

    opacities = generator._calculate_opacities()
    assert len(opacities) == 4
    assert all(0 < op <= 1 for op in opacities)

    # Test that opacities increase (for linear mode)
    assert opacities == sorted(opacities)


def test_payload_preserves_definitions_viewbox_and_root_attributes():
    """Complex artwork must retain its masks, images and coordinate system."""
    payload = """<svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        width="2048" height="2048" viewBox="10 20 2048 2048" fill="red">
      <defs>
        <clipPath id="artClip"><rect width="2048" height="2048"/></clipPath>
        <linearGradient id="artGradient"><stop stop-color="blue"/></linearGradient>
        <mask id="artMask"><rect width="2048" height="2048" fill="white"/></mask>
        <path id="artPath" d="M10 20h100v100z"/>
      </defs>
      <g clip-path="url(#artClip)" mask="url(#artMask)">
        <use xlink:href="#artPath" fill="url(#artGradient)"/>
        <image xlink:href="data:image/png;base64,AAAA" width="10" height="10"/>
      </g>
    </svg>"""
    result = VexyliconGenerator(params=VexyliconParams(steps=2)).generate(payload)
    root = etree.fromstring(result.encode())
    ns = {"s": "http://www.w3.org/2000/svg"}
    artwork = root.find('.//s:g[@id="payload"]/s:svg', ns)
    assert artwork is not None, "Payload must keep its own SVG viewport"
    assert artwork.get("viewBox") == "10 20 2048 2048"
    assert artwork.get("fill") == "red", "Root presentation attributes must survive"
    assert artwork.get("width") == artwork.get("height") == "100%"
    assert len(artwork.findall("s:defs/*", ns)) == 4
    assert artwork.find(".//s:image", ns).get("{http://www.w3.org/1999/xlink}href") == "data:image/png;base64,AAAA"
    assert root.get("viewBox") == "0 0 1200 1200"


def test_payload_without_viewbox_uses_intrinsic_dimensions(tmp_path):
    """File payloads with pixel dimensions also scale to the icon canvas."""
    payload = tmp_path / "art.svg"
    payload.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200px" height="100px"><rect width="200" height="100"/></svg>'
    )
    result = VexyliconGenerator(params=VexyliconParams(steps=2)).generate(payload)
    root = etree.fromstring(result.encode())
    artwork = root.find('.//{*}g[@id="payload"]/{*}svg')
    assert artwork.get("viewBox") == "0 0 200 100"


def test_large_inline_payload_does_not_get_treated_as_a_filename():
    """Real artwork can be much longer than the filesystem's path limit."""
    payload = '<svg xmlns="http://www.w3.org/2000/svg">' + " " * 10000 + "</svg>"
    result = VexyliconGenerator(params=VexyliconParams(steps=2)).generate(payload)
    assert 'id="payload"' in result


def test_theme_gradients_have_unique_ids_and_valid_stop_colors():
    """Theme updates must replace template gradients using SVG attribute names."""
    generator = VexyliconGenerator(params=VexyliconParams(steps=2))
    generator.theme.gradients["edgeGlow"]["stops"][0]["color"] = "#123456"
    root = etree.fromstring(generator.generate().encode())
    ids = root.xpath("//@id")
    assert len(ids) == len(set(ids)), "Duplicate IDs make gradient resolution ambiguous"
    stops = root.find('.//*[@id="edgeGlow"]').findall("{*}stop")
    assert stops[0].get("stop-color") == "#123456"
    assert not root.xpath("//@stop_color | //@pointer_events")

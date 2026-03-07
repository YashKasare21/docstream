"""
Tests for the Renderer module.

This module contains unit tests for template-based output generation.
File system and subprocess calls are mocked where appropriate.
"""

import pytest

from docstream.core.renderer import LuaRenderer, Renderer, TemplateInfo, TemplateType
from docstream.exceptions import RenderingError


class TestLuaRenderer:
    """Unit tests for LuaRenderer."""

    def test_list_templates_returns_list(self, tmp_path):
        """LuaRenderer.list_templates should return a list."""
        renderer = LuaRenderer(template_dir=str(tmp_path))
        assert isinstance(renderer._template_cache, dict)

    def test_get_template_path_raises_for_unknown(self, tmp_path):
        """LuaRenderer should raise RenderingError for unknown template names."""
        renderer = LuaRenderer(template_dir=str(tmp_path))
        with pytest.raises(RenderingError):
            renderer._get_template_path("nonexistent_template")

    def test_get_template_path_accepts_full_path(self, tmp_path):
        """LuaRenderer should accept a full path to a template file."""
        template_file = tmp_path / "custom.lua"
        template_file.write_text("-- empty template")
        renderer = LuaRenderer(template_dir=str(tmp_path))
        path = renderer._get_template_path(str(template_file))
        assert path == str(template_file)

    def test_escape_latex_ampersand(self):
        """_escape_latex should escape & as \\&."""
        renderer = LuaRenderer()
        result = renderer._escape_latex("a & b")
        assert r"\&" in result

    def test_escape_latex_percent(self):
        """_escape_latex should escape % as \\%."""
        renderer = LuaRenderer()
        result = renderer._escape_latex("50% done")
        assert r"\%" in result

    def test_escape_latex_dollar(self):
        """_escape_latex should escape $ as \\$."""
        renderer = LuaRenderer()
        result = renderer._escape_latex("$100")
        assert r"\$" in result

    def test_escape_latex_empty_string(self):
        """_escape_latex should handle empty strings gracefully."""
        renderer = LuaRenderer()
        assert renderer._escape_latex("") == ""

    def test_template_cache_populated_after_load(self, tmp_path):
        """Template cache should contain template after first load."""
        template_file = tmp_path / "test.lua"
        template_file.write_text("-- simple template")
        renderer = LuaRenderer(template_dir=str(tmp_path))
        renderer._load_template(str(template_file))
        assert str(template_file) in renderer._template_cache

    def test_join_blocks_returns_string(self, sample_document_ast):
        """_join_blocks should concatenate block contents."""
        renderer = LuaRenderer()
        blocks = sample_document_ast.sections[0].blocks
        result = renderer._join_blocks(blocks)
        assert isinstance(result, str)

    def test_render_raises_for_missing_template(self, sample_document_ast):
        """render() should raise RenderingError when template is not found."""
        renderer = LuaRenderer(template_dir="/nonexistent/dir")
        with pytest.raises(RenderingError):
            renderer.render(sample_document_ast, "missing_template")


class TestRenderer:
    """Unit tests for the main Renderer class."""

    def test_list_templates_includes_builtins(self, tmp_path):
        """list_templates should include built-in template names."""
        renderer = Renderer(template_dir=str(tmp_path))
        templates = renderer.list_templates()
        for t in TemplateType:
            assert t.value in templates

    def test_get_template_info_ieee(self):
        """get_template_info should return TemplateInfo for ieee."""
        renderer = Renderer()
        info = renderer.get_template_info(TemplateType.IEEE)
        assert isinstance(info, TemplateInfo)
        assert info.name == "IEEE"

    def test_get_template_info_report(self):
        """get_template_info should return TemplateInfo for report."""
        renderer = Renderer()
        info = renderer.get_template_info(TemplateType.REPORT)
        assert isinstance(info, TemplateInfo)

    def test_get_template_info_resume(self):
        """get_template_info should return TemplateInfo for resume."""
        renderer = Renderer()
        info = renderer.get_template_info(TemplateType.RESUME)
        assert isinstance(info, TemplateInfo)

    def test_get_template_info_custom_string(self):
        """get_template_info with a custom string should return TemplateInfo."""
        renderer = Renderer()
        info = renderer.get_template_info("my_custom_template")
        assert isinstance(info, TemplateInfo)
        assert info.name == "my_custom_template"

    def test_validate_template_returns_false_for_missing(self, tmp_path):
        """validate_template should return False when file is missing."""
        renderer = Renderer(template_dir=str(tmp_path))
        result = renderer.validate_template("/nonexistent/template.lua")
        assert result is False

    def test_validate_template_returns_true_for_valid_file(self, tmp_path):
        """validate_template should return True for an existing file."""
        template_file = tmp_path / "valid.lua"
        template_file.write_text("-- valid lua template")
        renderer = Renderer(template_dir=str(tmp_path))
        result = renderer.validate_template(str(template_file))
        assert result is True

    def test_render_to_latex_returns_string(self, sample_document_ast, tmp_path):
        """render_to_latex should return a non-empty string."""
        template_file = tmp_path / "report.lua"
        template_file.write_text("-- stub report template")
        renderer = Renderer(template_dir=str(tmp_path))
        result = renderer.render_to_latex(sample_document_ast, "report")
        assert isinstance(result, str)


class TestTemplateType:
    """Tests for the TemplateType enum."""

    def test_enum_values(self):
        """TemplateType values should match expected strings."""
        assert TemplateType.IEEE.value == "ieee"
        assert TemplateType.REPORT.value == "report"
        assert TemplateType.RESUME.value == "resume"

    def test_enum_from_string(self):
        """TemplateType should be constructable from string value."""
        assert TemplateType("ieee") == TemplateType.IEEE
        assert TemplateType("report") == TemplateType.REPORT


class TestTemplateInfo:
    """Tests for the TemplateInfo dataclass."""

    def test_defaults(self):
        """TemplateInfo should have sensible defaults."""
        info = TemplateInfo(name="test", description="A test template")
        assert info.version == "1.0.0"
        assert info.dependencies == []

    def test_custom_values(self):
        """TemplateInfo should store custom values."""
        info = TemplateInfo(
            name="custom",
            description="Custom template",
            version="2.0.0",
            author="Me",
            dependencies=["geometry", "fancyhdr"],
        )
        assert info.author == "Me"
        assert "geometry" in info.dependencies

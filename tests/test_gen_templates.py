from json_explorer.codegen.core import TemplateManager


class TestTemplates:
    """Test template system."""

    def test_template_manager_creation(self, tmp_path):
        # Create test template
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.j2").write_text("Hello {{ name }}!")

        manager = TemplateManager(template_dir)
        assert manager.template_dir == template_dir

    def test_template_rendering(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.j2").write_text("Hello {{ name }}!")

        manager = TemplateManager(template_dir)
        result = manager.render("test.j2", {"name": "World"})
        assert result == "Hello World!"

    def test_template_exists(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "exists.j2").write_text("test")

        manager = TemplateManager(template_dir)
        assert manager.exists("exists.j2")
        assert not manager.exists("missing.j2")

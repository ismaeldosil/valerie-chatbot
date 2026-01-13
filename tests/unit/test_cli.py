"""Tests for CLI module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from valerie.cli import (
    app,
    print_debug_info,
    print_error,
    print_response,
    print_welcome,
)

runner = CliRunner()


class TestPrintFunctions:
    """Tests for CLI print functions."""

    def test_print_welcome(self, capsys):
        """Test welcome message prints."""
        with patch("valerie.cli.console") as mock_console:
            print_welcome()
            mock_console.print.assert_called_once()

    def test_print_response_simple(self):
        """Test simple response printing."""
        with patch("valerie.cli.console") as mock_console:
            print_response("Hello, world!")
            assert mock_console.print.call_count >= 1

    def test_print_response_with_debug(self):
        """Test response printing with debug info."""
        with patch("valerie.cli.console") as mock_console:
            debug_info = {"key1": "value1", "key2": "value2"}
            print_response("Hello!", debug_info)
            assert mock_console.print.call_count >= 2

    def test_print_debug_info(self):
        """Test debug info printing."""
        with patch("valerie.cli.console") as mock_console:
            info = {"Intent": "search", "Confidence": "0.95"}
            print_debug_info(info)
            mock_console.print.assert_called_once()

    def test_print_error(self):
        """Test error message printing."""
        with patch("valerie.cli.console") as mock_console:
            print_error("Something went wrong")
            mock_console.print.assert_called_once()


class TestVersionCommand:
    """Tests for version command."""

    def test_version_command(self):
        """Test version command runs."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Valerie" in result.output


class TestConfigCommand:
    """Tests for config command."""

    def test_config_command(self):
        """Test config command shows settings."""
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0


class TestTestGraphCommand:
    """Tests for test-graph command."""

    def test_graph_command_success(self):
        """Test graph compilation command."""
        with patch("valerie.graph.builder.build_graph") as mock_build:
            mock_graph = MagicMock()
            mock_graph.nodes = ["node1", "node2", "node3"]
            mock_build.return_value = mock_graph

            result = runner.invoke(app, ["test-graph"])
            assert result.exit_code == 0

    def test_graph_command_failure(self):
        """Test graph compilation failure."""
        with patch(
            "valerie.graph.builder.build_graph",
            side_effect=Exception("Build failed"),
        ):
            result = runner.invoke(app, ["test-graph"])
            assert result.exit_code == 1


class TestChatCommand:
    """Tests for chat command."""

    def test_chat_no_api_key(self):
        """Test chat without API key."""
        with patch("valerie.cli.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key=None)
            result = runner.invoke(app, ["chat"])
            assert result.exit_code == 1

    def test_chat_graph_compile_failure(self):
        """Test chat with graph compilation failure."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch(
                "valerie.cli.get_compiled_graph",
                side_effect=Exception("Failed"),
            ),
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            result = runner.invoke(app, ["chat"])
            assert result.exit_code == 1


class TestMainFunction:
    """Tests for main entry point."""

    def test_main_calls_app(self):
        """Test main function calls app."""
        with patch("valerie.cli.app") as mock_app:
            from valerie.cli import main

            main()
            mock_app.assert_called_once()

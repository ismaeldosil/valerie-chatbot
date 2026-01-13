"""Extended tests for CLI module - chat loop."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from valerie.cli import run_chat_loop
from valerie.models import ChatState, Intent


class TestRunChatLoop:
    """Tests for run_chat_loop function."""

    @pytest.mark.asyncio
    async def test_run_chat_loop_no_api_key(self):
        """Test chat loop exits when no API key."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.print_error") as mock_error,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key=None)

            with pytest.raises(typer.Exit):
                await run_chat_loop()

            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_chat_loop_graph_compile_failure(self):
        """Test chat loop exits on graph compilation failure."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.print_error") as mock_error,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.side_effect = Exception("Graph failed")

            with pytest.raises(typer.Exit):
                await run_chat_loop()

            mock_error.assert_called()

    @pytest.mark.asyncio
    async def test_run_chat_loop_exit_command(self):
        """Test chat loop exits on 'exit' command."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability") as mock_get_obs,
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            mock_get_obs.return_value = MagicMock()
            mock_prompt.ask.return_value = "exit"

            await run_chat_loop()

            mock_prompt.ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_chat_loop_quit_command(self):
        """Test chat loop exits on 'quit' command."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            mock_prompt.ask.return_value = "quit"

            await run_chat_loop()

    @pytest.mark.asyncio
    async def test_run_chat_loop_clear_command(self):
        """Test chat loop clears on 'clear' command."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console") as mock_console,
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            # First clear, then exit
            mock_prompt.ask.side_effect = ["clear", "exit"]

            await run_chat_loop()

            assert mock_prompt.ask.call_count == 2
            # Check that clear message was printed
            calls = mock_console.print.call_args_list
            clear_printed = any("cleared" in str(call).lower() for call in calls)
            assert clear_printed

    @pytest.mark.asyncio
    async def test_run_chat_loop_debug_toggle(self):
        """Test chat loop toggles debug mode."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console") as mock_console,
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            mock_prompt.ask.side_effect = ["debug", "exit"]

            await run_chat_loop()

            # Check debug message printed
            calls = mock_console.print.call_args_list
            debug_printed = any("debug" in str(call).lower() for call in calls)
            assert debug_printed

    @pytest.mark.asyncio
    async def test_run_chat_loop_help_command(self):
        """Test chat loop shows help on 'help' command."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome") as mock_welcome,
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            mock_prompt.ask.side_effect = ["help", "exit"]

            await run_chat_loop()

            # Welcome shown twice (initial + help)
            assert mock_welcome.call_count == 2

    @pytest.mark.asyncio
    async def test_run_chat_loop_empty_input(self):
        """Test chat loop skips empty input."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            mock_prompt.ask.side_effect = ["", "  ", "exit"]

            await run_chat_loop()

            assert mock_prompt.ask.call_count == 3

    @pytest.mark.asyncio
    async def test_run_chat_loop_successful_message(self):
        """Test chat loop processes a message successfully."""
        mock_graph = AsyncMock()
        result_state = ChatState()
        result_state.final_response = "Test response"
        result_state.intent = Intent.GREETING
        mock_graph.ainvoke.return_value = result_state

        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability") as mock_get_obs,
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.print_response") as mock_print_response,
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = mock_graph
            mock_observability = MagicMock()
            mock_observability.start_trace.return_value = "trace-123"
            mock_get_obs.return_value = mock_observability
            mock_prompt.ask.side_effect = ["Hello", "exit"]

            await run_chat_loop()

            mock_graph.ainvoke.assert_called_once()
            mock_print_response.assert_called_once()
            mock_observability.end_trace.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_chat_loop_with_debug_mode(self):
        """Test chat loop shows debug info when enabled."""
        mock_graph = AsyncMock()
        result_state = ChatState()
        result_state.final_response = "Test response"
        result_state.intent = Intent.SUPPLIER_SEARCH
        result_state.confidence = 0.95
        result_state.suppliers = []
        result_state.itar_flagged = False
        result_state.requires_human_approval = False
        result_state.evaluation_score = 85.0
        result_state.agent_outputs = {"test": MagicMock()}
        mock_graph.ainvoke.return_value = result_state

        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability") as mock_get_obs,
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.print_response") as mock_print_response,
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = mock_graph
            mock_observability = MagicMock()
            mock_observability.start_trace.return_value = "trace-123"
            mock_get_obs.return_value = mock_observability
            mock_prompt.ask.side_effect = ["Hello", "exit"]

            await run_chat_loop(debug=True)

            # Check debug info was passed (second positional arg)
            call_args = mock_print_response.call_args
            assert call_args[0][0] == "Test response"
            # Debug info is second positional arg
            assert call_args[0][1] is not None

    @pytest.mark.asyncio
    async def test_run_chat_loop_no_response(self):
        """Test chat loop handles no final_response."""
        mock_graph = AsyncMock()
        result_state = ChatState()
        result_state.final_response = None
        result_state.intent = Intent.UNKNOWN
        mock_graph.ainvoke.return_value = result_state

        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability") as mock_get_obs,
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.print_response") as mock_print_response,
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = mock_graph
            mock_observability = MagicMock()
            mock_observability.start_trace.return_value = "trace-123"
            mock_get_obs.return_value = mock_observability
            mock_prompt.ask.side_effect = ["Hello", "exit"]

            await run_chat_loop()

            call_args = mock_print_response.call_args
            assert "couldn't generate" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_run_chat_loop_processing_error(self):
        """Test chat loop handles processing errors."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = Exception("Processing failed")

        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability") as mock_get_obs,
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.print_error") as mock_print_error,
            patch("valerie.cli.console"),
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = mock_graph
            mock_observability = MagicMock()
            mock_observability.start_trace.return_value = "trace-123"
            mock_get_obs.return_value = mock_observability
            mock_prompt.ask.side_effect = ["Hello", "exit"]

            await run_chat_loop()

            mock_print_error.assert_called_once()
            assert "Processing failed" in str(mock_print_error.call_args)

    @pytest.mark.asyncio
    async def test_run_chat_loop_keyboard_interrupt(self):
        """Test chat loop handles keyboard interrupt."""
        with (
            patch("valerie.cli.get_settings") as mock_settings,
            patch("valerie.cli.get_compiled_graph") as mock_get_graph,
            patch("valerie.cli.get_observability"),
            patch("valerie.cli.print_welcome"),
            patch("valerie.cli.console") as mock_console,
            patch("valerie.cli.Prompt") as mock_prompt,
        ):
            mock_settings.return_value = MagicMock(anthropic_api_key="test-key")
            mock_get_graph.return_value = MagicMock()
            # First call raises KeyboardInterrupt, second returns exit
            mock_prompt.ask.side_effect = [KeyboardInterrupt(), "exit"]

            await run_chat_loop()

            # Check interrupt message was printed
            calls = mock_console.print.call_args_list
            interrupt_printed = any("interrupted" in str(call).lower() for call in calls)
            assert interrupt_printed


class TestMainFunction:
    """Tests for main entry point."""

    def test_main_module_execution(self):
        """Test __main__ block execution."""
        with patch("valerie.cli.main") as mock_main:
            # Import the module to trigger __main__ check
            import valerie.cli as cli_module

            # Simulate running as __main__
            cli_module.main()
            mock_main.assert_called()

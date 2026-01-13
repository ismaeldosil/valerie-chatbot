"""Command-line interface for the Valerie Supplier Chatbot."""

import asyncio
import uuid

import typer
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .graph import get_compiled_graph
from .infrastructure.observability import get_observability
from .models import ChatState, get_settings

app = typer.Typer(
    name="valerie-chat",
    help="Valerie Supplier Recommendation Chatbot CLI",
    add_completion=False,
)
console = Console()


def print_welcome():
    """Print welcome message."""
    console.print(
        Panel.fit(
            "[bold blue]Valerie Supplier Chatbot[/bold blue]\n"
            "[dim]Aerospace Supplier Recommendation System v2.0[/dim]\n\n"
            "Commands:\n"
            "  [green]exit[/green] or [green]quit[/green] - Exit the chatbot\n"
            "  [green]clear[/green] - Clear conversation history\n"
            "  [green]debug[/green] - Toggle debug mode\n"
            "  [green]help[/green] - Show available commands",
            title="Welcome",
            border_style="blue",
        )
    )


def print_response(response: str, debug_info: dict | None = None):
    """Print the chatbot response."""
    console.print()
    console.print(
        Panel(
            Markdown(response),
            title="[bold green]Assistant[/bold green]",
            border_style="green",
        )
    )

    if debug_info:
        print_debug_info(debug_info)


def print_debug_info(info: dict):
    """Print debug information."""
    table = Table(title="Debug Info", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in info.items():
        table.add_row(str(key), str(value))

    console.print(table)


def print_error(message: str):
    """Print an error message."""
    console.print(
        Panel(
            f"[red]{message}[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red",
        )
    )


async def run_chat_loop(debug: bool = False):
    """Run the main chat loop."""
    settings = get_settings()
    observability = get_observability()

    # Check for API key
    if not settings.anthropic_api_key:
        print_error(
            "No Anthropic API key found.\n"
            "Set VALERIE_ANTHROPIC_API_KEY environment variable or create a .env file."
        )
        raise typer.Exit(1)

    # Compile the graph
    try:
        graph = get_compiled_graph()
    except Exception as e:
        print_error(f"Failed to compile graph: {e}")
        raise typer.Exit(1)

    # Initialize state
    session_id = str(uuid.uuid4())
    state = ChatState(session_id=session_id)

    print_welcome()
    console.print(f"\n[dim]Session ID: {session_id}[/dim]\n")

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("[bold blue]You[/bold blue]")

            # Handle commands
            if user_input.lower() in ("exit", "quit"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "clear":
                state = ChatState(session_id=session_id)
                console.print("[dim]Conversation cleared.[/dim]")
                continue

            if user_input.lower() == "debug":
                debug = not debug
                console.print(f"[dim]Debug mode: {'enabled' if debug else 'disabled'}[/dim]")
                continue

            if user_input.lower() == "help":
                print_welcome()
                continue

            if not user_input.strip():
                continue

            # Add message to state
            state.messages.append(HumanMessage(content=user_input))

            # Start trace
            trace_id = observability.start_trace(session_id)
            state.trace_id = trace_id

            # Run the graph
            config = {"configurable": {"thread_id": session_id}}

            try:
                result = await graph.ainvoke(state, config=config)
                state = result

                # Print response
                response = state.final_response or "I couldn't generate a response."
                debug_info = None

                if debug:
                    debug_info = {
                        "Intent": state.intent.value,
                        "Confidence": f"{state.confidence:.2f}",
                        "Suppliers Found": len(state.suppliers),
                        "ITAR Flagged": state.itar_flagged,
                        "HITL Required": state.requires_human_approval,
                        "Evaluation Score": state.evaluation_score or "N/A",
                        "Agents Run": len(state.agent_outputs),
                    }

                print_response(response, debug_info)

                # End trace
                observability.end_trace(trace_id, state)

            except Exception as e:
                print_error(f"Error processing request: {e}")
                if debug:
                    console.print_exception()

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
            continue


@app.command()
def chat(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
):
    """Start an interactive chat session."""
    asyncio.run(run_chat_loop(debug=debug))


@app.command()
def version():
    """Show version information."""
    from . import __version__

    console.print(f"Valerie Supplier Chatbot v{__version__}")


@app.command()
def config():
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    # Only show non-sensitive settings
    table.add_row("Model", settings.model_name)
    table.add_row("Temperature", str(settings.temperature))
    table.add_row("Oracle Base URL", settings.oracle_base_url)
    table.add_row("PII Detection", str(settings.pii_detection_enabled))
    table.add_row("ITAR Detection", str(settings.itar_detection_enabled))
    table.add_row("HITL Enabled", str(settings.hitl_enabled))
    table.add_row("Tracing Enabled", str(settings.tracing_enabled))
    table.add_row("API Key Set", "Yes" if settings.anthropic_api_key else "No")

    console.print(table)


@app.command()
def test_graph():
    """Test the graph compilation without API key."""
    console.print("[dim]Testing graph compilation...[/dim]")

    try:
        from .graph.builder import build_graph

        graph = build_graph()
        console.print("[green]Graph built successfully![/green]")

        # Show graph structure
        console.print("\n[bold]Graph Nodes:[/bold]")
        for node in graph.nodes:
            console.print(f"  - {node}")

    except Exception as e:
        print_error(f"Graph compilation failed: {e}")
        raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()

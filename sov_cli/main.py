"""Sovereignty CLI — the Round Console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sov_engine.hashing import make_round_proof, save_proof, verify_proof
from sov_engine.models import GameState, WinCondition
from sov_engine.rules.campfire import (
    check_deal_deadlines,
    check_voucher_deadlines,
    new_game,
    resolve_space,
    roll_and_move,
)
from sov_engine.serialize import canonical_json, game_state_snapshot

app = typer.Typer(
    name="sov",
    help="Sovereignty — a strategy game about governance, trust, and trade.",
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Persistent state (file-backed per game session)
# ---------------------------------------------------------------------------

SAVE_DIR = Path(".sov")
STATE_FILE = SAVE_DIR / "game_state.json"
RNG_SEED_FILE = SAVE_DIR / "rng_seed.txt"
PROOFS_DIR = SAVE_DIR / "proofs"


def _save_state(state: GameState) -> None:
    """Persist game state to disk."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = game_state_snapshot(state)
    STATE_FILE.write_text(canonical_json(snapshot), encoding="utf-8", newline="\n")


def _load_game() -> tuple[GameState, GameRng] | None:  # type: ignore[name-defined]  # noqa: F821
    """Load game state from disk. Returns None if no active game."""
    if not STATE_FILE.exists():
        return None
    if not RNG_SEED_FILE.exists():
        return None

    seed = int(RNG_SEED_FILE.read_text().strip())
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    # Reconstruct game from saved state
    from sov_engine.rng import GameRng

    rng = GameRng(seed)

    wcs: dict[str, WinCondition] = {}
    names = []
    for p_data in data["players"]:
        names.append(p_data["name"])
        wcs[p_data["name"]] = WinCondition(p_data["win_condition"])

    state, _ = new_game(seed, names, wcs)

    # Restore mutable state
    for i, p_data in enumerate(data["players"]):
        p = state.players[i]
        p.coins = p_data["coins"]
        p.reputation = p_data["reputation"]
        p.upgrades = p_data["upgrades"]
        p.position = p_data["position"]

    state.current_round = data["current_round"]
    state.current_player_index = data["current_player_index"]
    state.turn_in_round = data["turn_in_round"]
    state.game_over = data["game_over"]
    state.winner = data["winner"]
    state.market.food = data["market"]["food"]
    state.market.wood = data["market"]["wood"]
    state.market.tools = data["market"]["tools"]

    # Advance RNG to match game progression (approximate)
    # For true determinism we'd need to replay all actions from seed
    # This is sufficient for Phase 1 CLI play
    return state, rng


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def new(
    seed: Annotated[int, typer.Option("--seed", "-s", help="RNG seed for reproducibility")] = 42,
    players: Annotated[
        list[str],
        typer.Option("--player", "-p", help="Player names (2-4 required)"),
    ] = None,
) -> None:
    """Start a new Campfire game."""
    if players is None:
        players = []
    if len(players) < 2:
        console.print("[red]Need at least 2 players. Use -p Name1 -p Name2[/red]")
        raise typer.Exit(1)
    if len(players) > 4:
        console.print("[red]Maximum 4 players.[/red]")
        raise typer.Exit(1)

    if STATE_FILE.exists() and not typer.confirm("Active game found. Overwrite?"):
        raise typer.Exit(0)

    state, rng = new_game(seed, players)

    # Save seed for reloading
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    RNG_SEED_FILE.write_text(str(seed), encoding="utf-8")
    _save_state(state)

    console.print(Panel(
        f"[bold green]Sovereignty: Campfire[/bold green]\n"
        f"Seed: {seed}\n"
        f"Players: {', '.join(players)}\n"
        f"Round limit: {state.config.max_rounds}",
        title="New Game",
    ))
    _print_status(state)


@app.command()
def status() -> None:
    """Show current game state."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game. Run 'sov new' first.[/red]")
        raise typer.Exit(1)
    state, _ = result
    _print_status(state)


@app.command()
def turn() -> None:
    """Execute the current player's turn: roll, move, resolve."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game. Run 'sov new' first.[/red]")
        raise typer.Exit(1)
    state, rng = result

    if state.game_over:
        console.print(f"[yellow]Game is over! Winner: {state.winner}[/yellow]")
        raise typer.Exit(0)

    player = state.current_player
    console.print(f"\n[bold]{player.name}'s turn[/bold] (Round {state.current_round})")

    # Roll and move
    roll = roll_and_move(state, rng)
    space = state.board[player.position]
    console.print(f"  Rolled [bold cyan]{roll}[/bold cyan] -> landed on [bold]{space.name}[/bold]")

    # Resolve space
    result_msg = resolve_space(state, rng)
    console.print(f"  {result_msg}")

    # Check win
    winner = state.check_winner()
    if winner:
        console.print(f"\n[bold green]{winner} wins![/bold green]")
        _save_state(state)
        raise typer.Exit(0)

    # Advance to next player
    old_round = state.current_round
    state.advance_turn()

    # End of round checks
    if state.current_round > old_round:
        console.print(f"\n[dim]--- End of Round {old_round} ---[/dim]")
        voucher_msgs = check_voucher_deadlines(state)
        deal_msgs = check_deal_deadlines(state)
        for m in voucher_msgs + deal_msgs:
            console.print(f"  {m}")

        # Reset market prices if they were modified by events
        state.market.food = 1
        state.market.wood = 2
        state.market.tools = 3

    _save_state(state)
    _print_brief_status(state)


@app.command(name="end-round")
def end_round(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for proof files"),
    ] = None,
) -> None:
    """Generate a round proof for the current state."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game.[/red]")
        raise typer.Exit(1)
    state, _ = result

    proof = make_round_proof(state)
    out_dir = output or PROOFS_DIR
    path = save_proof(proof, out_dir)

    console.print(Panel(
        f"Round: {proof['round']}\n"
        f"Hash: [bold]{proof['state_hash']}[/bold]\n"
        f"File: {path}",
        title="Round Proof",
    ))


@app.command()
def verify(
    proof_file: Annotated[Path, typer.Argument(help="Path to proof JSON file")],
) -> None:
    """Verify a round proof file."""
    valid, message = verify_proof(proof_file)
    if valid:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]{message}[/red]")
        raise typer.Exit(1)


@app.command()
def board() -> None:
    """Show the game board with player positions."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game.[/red]")
        raise typer.Exit(1)
    state, _ = result

    table = Table(title="Board")
    table.add_column("#", style="dim", width=3)
    table.add_column("Space", width=14)
    table.add_column("Players Here", width=30)
    table.add_column("Effect", width=40)

    for space in state.board:
        players_here = [p.name for p in state.players if p.position == space.index]
        names = (f"[bold cyan]{n}[/bold cyan]" for n in players_here)
        marker = ", ".join(names) if players_here else ""
        table.add_row(str(space.index), space.name, marker, space.description)

    console.print(table)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _print_status(state: GameState) -> None:
    table = Table(title=f"Round {state.current_round}")
    table.add_column("Player", style="bold")
    table.add_column("Coins", justify="right")
    table.add_column("Rep", justify="right")
    table.add_column("Upgrades", justify="right")
    table.add_column("Position")
    table.add_column("Goal")

    for i, p in enumerate(state.players):
        marker = " *" if i == state.current_player_index else ""
        pos_name = state.board[p.position].name if state.board else str(p.position)
        table.add_row(
            p.name + marker,
            str(p.coins),
            str(p.reputation),
            str(p.upgrades),
            pos_name,
            p.win_condition.value,
        )

    console.print(table)
    if state.game_over:
        console.print(f"[bold green]Winner: {state.winner}[/bold green]")
    else:
        console.print(f"[dim]Next: {state.current_player.name}[/dim]")


def _print_brief_status(state: GameState) -> None:
    parts = []
    for i, p in enumerate(state.players):
        marker = ">" if i == state.current_player_index else " "
        parts.append(f"{marker}{p.name}: {p.coins}c {p.reputation}r {p.upgrades}u")
    console.print(f"[dim]R{state.current_round} | {' | '.join(parts)}[/dim]")


if __name__ == "__main__":
    app()

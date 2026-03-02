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
    apologize,
    break_promise,
    check_deal_deadlines,
    check_voucher_deadlines,
    keep_promise,
    make_promise,
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
        p.promises = p_data.get("promises", [])
        p.helped_last_round = p_data.get("helped_last_round", False)
        p.skip_next_move = p_data.get("skip_next_move", False)
        p.apology_used = p_data.get("apology_used", False)

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
        f"[bold green]Sovereignty: Campfire[/bold green]\n\n"
        f"  Everyone starts with 5 coins, 3 reputation, and a goal.\n"
        f"  Players: {', '.join(players)}\n"
        f"  {state.config.max_rounds} rounds. Make them count.",
        title="Gather 'round",
    ))
    _print_status(state)


@app.command()
def tutorial() -> None:
    """Learn to play in 60 seconds. Sets up a quick demo game."""
    from time import sleep

    console.print(Panel(
        "[bold green]Sovereignty: Campfire[/bold green]\n\n"
        "  A quick walkthrough. Two players, one round.\n"
        "  Takes about a minute.",
        title="Learn by doing",
    ))
    sleep(1)

    # Set up a 2-player demo game
    state, rng = new_game(seed=1, player_names=["You", "Friend"])
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    RNG_SEED_FILE.write_text("1", encoding="utf-8")

    console.print("\n  You and Friend sit down with 5 coins and 3 reputation each.")
    console.print("  [dim]Goal: be the first to reach 20 coins (Prosperity).[/dim]\n")
    sleep(1)

    # Step 1: Roll and move
    console.print("  [bold]Step 1: Roll and move[/bold]")
    roll = roll_and_move(state, rng)
    space = state.board[state.current_player.position]
    console.print(f"  You rolled a {roll} and landed on {space.name}.")
    console.print(f"  [dim]{space.description}[/dim]")
    result_msg = resolve_space(state, rng)
    console.print(f"  {result_msg}\n")
    sleep(1)

    # Step 2: Make a promise
    console.print("  [bold]Step 2: The Promise[/bold]")
    console.print('  You say out loud: "I promise to help Friend next round."')
    make_promise(state, state.current_player, "help Friend next round")
    console.print("  [dim]Keep it = +1 Rep. Break it = -2 Rep. Just your word.[/dim]\n")
    sleep(1)

    # Advance to Friend's turn
    state.advance_turn()

    console.print("  [bold]Step 3: Friend's turn[/bold]")
    player = state.current_player
    roll = roll_and_move(state, rng)
    space = state.board[player.position]
    console.print(f"  Friend rolled a {roll} and landed on {space.name}.")
    result_msg = resolve_space(state, rng)
    console.print(f"  {result_msg}\n")
    sleep(1)

    # Step 4: End of round -> proof
    console.print("  [bold]Step 4: End of round[/bold]")
    console.print("  Everyone took a turn. The round wraps up.")
    from sov_engine.hashing import make_round_proof

    proof = make_round_proof(state)
    h = proof["state_hash"][:16]
    console.print(f"  Receipt: [dim]{h}...[/dim]")
    console.print("  [dim]This hash is your game's fingerprint.")
    console.print("  If anyone changes the score later, the hash won't match.[/dim]\n")
    sleep(1)

    # Save the demo state
    _save_state(state)

    console.print(Panel(
        "  That's Campfire. Roll, land, trade, promise, repeat.\n"
        "  The console keeps score. You keep your word.\n\n"
        "  [dim]Start a real game: sov new -p Alice -p Bob[/dim]\n"
        "  [dim]Continue this demo: sov turn[/dim]",
        title="You're ready",
    ))


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
    """Take your turn. Roll the dice and see what happens."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game. Run 'sov new' first.[/red]")
        raise typer.Exit(1)
    state, rng = result

    if state.game_over:
        console.print(f"\n  The game is over. [bold]{state.winner}[/bold] won.")
        raise typer.Exit(0)

    player = state.current_player
    rnd = state.current_round
    console.print(f"\n  [bold]{player.name}[/bold], it's your turn. [dim](Round {rnd})[/dim]")

    # Show active promises as a gentle reminder
    if player.promises:
        for p_text in player.promises:
            console.print(f'  [dim italic]You promised: "{p_text}"[/dim italic]')

    # Roll and move
    roll = roll_and_move(state, rng)

    if roll == 0:
        # Skipped turn (Broken Bridge)
        console.print("  You're stuck. Road's out. Sit tight.")
    else:
        space = state.board[player.position]
        console.print(f"  You rolled a [bold cyan]{roll}[/bold cyan].")
        console.print(f"  You land on [bold]{space.name}[/bold]. [dim]{space.description}[/dim]")

        # Resolve space
        result_msg = resolve_space(state, rng)
        console.print(f"\n  {result_msg}")

    # Check win
    winner = state.check_winner()
    if winner:
        console.print(f"\n  [bold green]{winner} wins![/bold green]")
        _save_state(state)
        raise typer.Exit(0)

    # Advance to next player
    old_round = state.current_round
    state.advance_turn()

    # End of round checks
    if state.current_round > old_round:
        console.print(f"\n  [dim]--- Round {old_round} wraps up ---[/dim]")
        voucher_msgs = check_voucher_deadlines(state)
        deal_msgs = check_deal_deadlines(state)
        for m in voucher_msgs + deal_msgs:
            console.print(f"  {m}")

        # Reset helped_last_round for all players at end of round
        for p in state.players:
            p.helped_last_round = False

        # Reset market prices if they were modified by events
        state.market.food = 1
        state.market.wood = 2
        state.market.tools = 3

    _save_state(state)
    console.print()
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
    tx: Annotated[str, typer.Option("--tx", help="XRPL tx hash to verify against")] = "",
) -> None:
    """Verify a round proof file, optionally against an anchored tx."""
    valid, message = verify_proof(proof_file)
    if valid:
        console.print(f"  [green]Local proof valid.[/green] {message}")
    else:
        console.print(f"  [red]Local proof invalid.[/red] {message}")
        raise typer.Exit(1)

    if tx:
        proof_data = json.loads(proof_file.read_text(encoding="utf-8"))
        expected_hash = proof_data["state_hash"]
        try:
            from sov_transport.xrpl_testnet import XRPLTestnetTransport

            transport = XRPLTestnetTransport()
            if transport.verify(tx, expected_hash):
                memo = transport.get_memo_text(tx)
                console.print("  [green]Anchor verified.[/green] TX memo matches proof hash.")
                if memo:
                    console.print(f"  [dim]{memo}[/dim]")
                explorer = f"https://testnet.xrpl.org/transactions/{tx}"
                console.print(f"  [dim]{explorer}[/dim]")
            else:
                console.print("  [red]Anchor mismatch.[/red] TX memo doesn't match.")
                raise typer.Exit(1)
        except RuntimeError as e:
            console.print(f"  [red]{e}[/red]")
            raise typer.Exit(1) from None


@app.command()
def anchor(
    proof_file: Annotated[
        Path | None,
        typer.Argument(help="Proof file to anchor (default: latest)"),
    ] = None,
    seed_env: Annotated[
        str, typer.Option("--seed-env", help="Env var containing wallet seed"),
    ] = "XRPL_SEED",
    signer_file: Annotated[
        Path | None,
        typer.Option("--signer-file", help="File containing wallet seed"),
    ] = None,
) -> None:
    """Anchor a round proof hash on XRPL Testnet. The ledger remembers."""
    import os

    # Find the proof file
    if proof_file is None:
        # Find the latest proof file
        PROOFS_DIR.mkdir(parents=True, exist_ok=True)
        proofs = sorted(PROOFS_DIR.glob("round_*.proof.json"))
        if not proofs:
            console.print("  [red]No proof files found. Run 'sov end-round' first.[/red]")
            raise typer.Exit(1)
        proof_file = proofs[-1]

    if not proof_file.exists():
        console.print(f"  [red]Proof file not found: {proof_file}[/red]")
        raise typer.Exit(1)

    # Load proof
    proof_data = json.loads(proof_file.read_text(encoding="utf-8"))
    state_hash = proof_data["state_hash"]
    rnd = proof_data["round"]
    seed_val = proof_data.get("rng_seed", "?")

    # Get wallet seed
    seed: str | None = None
    if signer_file and signer_file.exists():
        seed = signer_file.read_text(encoding="utf-8").strip()
    else:
        seed = os.environ.get(seed_env)

    if not seed:
        console.print(
            f"  [red]No wallet seed found.[/red]\n"
            f"  Set {seed_env} env var, or use --signer-file.\n"
            f"  Create a testnet wallet: sov wallet"
        )
        raise typer.Exit(1)

    # Build the memo
    game_id = f"s{seed_val}"
    memo = f"SOV|campfire_v1|{game_id}|r{rnd}|sha256:{state_hash}"

    console.print(f"\n  Anchoring Round {rnd}...")
    console.print(f"  [dim]{memo}[/dim]\n")

    try:
        from sov_transport.xrpl_testnet import XRPLTestnetTransport

        transport = XRPLTestnetTransport()
        txid = transport.anchor(state_hash, memo, seed)

        explorer = f"https://testnet.xrpl.org/transactions/{txid}"
        console.print(Panel(
            f"  Round {rnd} anchored on XRPL Testnet.\n\n"
            f"  TX: [bold]{txid}[/bold]\n"
            f"  Hash: [dim]{state_hash}[/dim]\n"
            f"  Explorer: [dim]{explorer}[/dim]\n\n"
            f"  [dim]Verify later: sov verify {proof_file} --tx {txid}[/dim]",
            title="Anchored",
        ))
    except RuntimeError as e:
        console.print(f"  [red]{e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"  [red]Anchor failed: {e}[/red]")
        console.print("  [dim]The game still works fine offline.[/dim]")
        raise typer.Exit(1) from None


@app.command()
def wallet() -> None:
    """Create a funded XRPL Testnet wallet for anchoring."""
    console.print("\n  Creating a Testnet wallet...")
    console.print("  [dim]This is play money. Testnet XRP has no value.[/dim]\n")

    try:
        from sov_transport.xrpl_testnet import fund_testnet_wallet

        address, seed = fund_testnet_wallet()

        # Save seed to .sov/wallet_seed.txt
        wallet_file = SAVE_DIR / "wallet_seed.txt"
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        wallet_file.write_text(seed, encoding="utf-8")

        console.print(Panel(
            f"  Address: [bold]{address}[/bold]\n"
            f"  Seed saved to: {wallet_file}\n\n"
            f"  [dim]Use it: sov anchor --signer-file {wallet_file}[/dim]\n"
            f"  [dim]Or set: export XRPL_SEED={seed}[/dim]",
            title="Testnet Wallet",
        ))
    except RuntimeError as e:
        console.print(f"  [red]{e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"  [red]Wallet creation failed: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def promise(
    action: Annotated[str, typer.Argument(help="make, keep, or break")],
    text: Annotated[str, typer.Argument(help="What you're promising")],
    player: Annotated[str, typer.Option("--player", "-p", help="Who's promising")] = "",
) -> None:
    """Make, keep, or break a promise. Say it out loud."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game.[/red]")
        raise typer.Exit(1)
    state, _ = result

    # Find the player (default: current player)
    target = None
    if player:
        target = next((p for p in state.players if p.name == player), None)
    else:
        target = state.current_player

    if target is None:
        console.print(f"[red]Player '{player}' not found.[/red]")
        raise typer.Exit(1)

    match action:
        case "make":
            msg = make_promise(state, target, text)
            console.print(f"\n  {msg}")
        case "keep":
            msg = keep_promise(state, target, text)
            console.print(f"\n  {msg}")
        case "break":
            msg = break_promise(state, target, text)
            console.print(f"\n  {msg}")
        case _:
            console.print("[red]Use: promise make/keep/break 'your promise text'[/red]")
            raise typer.Exit(1)

    _save_state(state)


@app.command(name="apologize")
def apologize_cmd(
    to: Annotated[str, typer.Argument(help="Who you're apologizing to")],
    player: Annotated[str, typer.Option("--player", "-p", help="Who's sorry")] = "",
) -> None:
    """Apologize for a broken promise. Once per game. Costs 1 coin."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game.[/red]")
        raise typer.Exit(1)
    state, _ = result

    source = None
    if player:
        source = next((p for p in state.players if p.name == player), None)
    else:
        source = state.current_player
    target_p = next((p for p in state.players if p.name == to), None)

    if source is None:
        console.print(f"[red]Player '{player}' not found.[/red]")
        raise typer.Exit(1)
    if target_p is None:
        console.print(f"[red]Player '{to}' not found.[/red]")
        raise typer.Exit(1)

    msg = apologize(state, source, target_p)
    console.print(f"\n  {msg}")
    _save_state(state)


@app.command()
def recap() -> None:
    """Show a human-readable summary of what happened recently."""
    result = _load_game()
    if result is None:
        console.print("[red]No active game.[/red]")
        raise typer.Exit(1)
    state, _ = result

    if not state.log:
        console.print("  Nothing has happened yet.")
        return

    # Show log entries from the current round (and previous if we just started)
    rnd = state.current_round
    prev_rnd = rnd - 1 if rnd > 1 else rnd

    console.print(f"\n  [bold]What happened lately[/bold] [dim](Round {rnd})[/dim]\n")
    for entry in state.log:
        # Show entries from current and previous round
        if entry.startswith(f"R{rnd}") or entry.startswith(f"R{prev_rnd}"):
            # Strip the round/turn prefix for readability
            _, _, text = entry.partition(": ")
            if text:
                console.print(f"  - {text}")

    # Highlight interesting moments
    broken = [e for e in state.log if "broke their promise" in e]
    helped = [e for e in state.log if "helps" in e and "Help" not in e[:5]]
    apologized = [e for e in state.log if "apologizes" in e]

    if broken or helped or apologized:
        console.print()
    for b in broken:
        _, _, text = b.partition(": ")
        console.print(f"  [red]Ouch:[/red] {text}")
    for h in helped:
        _, _, text = h.partition(": ")
        console.print(f"  [green]Kind:[/green] {text}")
    for a in apologized:
        _, _, text = a.partition(": ")
        console.print(f"  [yellow]Brave:[/yellow] {text}")
    console.print()


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
        console.print(f"  [bold green]{state.winner} wins the game.[/bold green]")
    else:
        console.print(f"  [dim]{state.current_player.name}'s turn next.[/dim]")


def _print_brief_status(state: GameState) -> None:
    parts = []
    for i, p in enumerate(state.players):
        marker = ">" if i == state.current_player_index else " "
        parts.append(f"{marker}{p.name}: {p.coins}c {p.reputation}r {p.upgrades}u")
    console.print(f"[dim]R{state.current_round} | {' | '.join(parts)}[/dim]")


if __name__ == "__main__":
    app()

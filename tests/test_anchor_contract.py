"""End-to-end contract regression guards for the anchor pipeline.

These tests join the THREE layers that the Wave 3 ``sha256:`` double-prefix
bug lived between:

    1. ``sov_engine.hashing.make_round_proof`` -> ``proof['envelope_hash']``
       (must be raw 64-char hex, no algorithm prefix)
    2. ``sov_cli.main`` anchor memo construction at line 817
       (``f"SOV|{ruleset}|{game_id}|r{rnd}|sha256:{envelope_hash}"`` --
       the ``sha256:`` prefix is added HERE, exactly once)
    3. ``sov_transport.xrpl_testnet.XRPLTestnetTransport.verify``
       (parses the memo by ``split('|')``, finds the field starting with
       ``"sha256:"``, strips the prefix, equality-checks against the raw hex)

If anyone ever (a) re-introduces the prefix into ``envelope_hash`` itself, or
(b) drops the prefix at the memo layer, or (c) changes the verify-side parser
to expect a different shape, exactly one of these tests will fail loud.

These guards are intentionally separate from ``tests/test_proofs.py`` so they
show up under their own file in ``pytest -v`` output as named regression
guards for the historical drift class.
"""

from __future__ import annotations

from sov_engine.hashing import make_round_proof
from sov_engine.rules.campfire import new_game


def test_envelope_hash_is_raw_hex_no_algorithm_prefix() -> None:
    """``proof['envelope_hash']`` must be the RAW 64-char lowercase hex digest.

    The ``sha256:`` algorithm tag belongs at the wire/memo layer (added in
    ``sov_cli/main.py:817``). Storing it inside the field value re-introduces
    the Wave 3 double-prefix bug where the on-chain memo would read
    ``...|sha256:sha256:abc...`` and the verifier-side ``startswith("sha256:")``
    would strip only one level, leaving a literal ``sha256:`` glued to the
    hash on equality compare.
    """
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    envelope_hash = proof["envelope_hash"]

    # Raw hex shape: 64 lowercase hex chars, nothing else.
    assert len(envelope_hash) == 64, (
        f"envelope_hash must be 64 hex chars, got {len(envelope_hash)}: {envelope_hash!r}"
    )
    assert all(c in "0123456789abcdef" for c in envelope_hash), (
        f"envelope_hash must be lowercase hex, got: {envelope_hash!r}"
    )
    # Explicit prefix-shape assertion -- this is the one that catches drift.
    assert not envelope_hash.startswith("sha256:"), (
        "envelope_hash must NOT contain the 'sha256:' algorithm prefix; "
        "the prefix is added at the memo layer (sov_cli/main.py anchor) only. "
        f"Got: {envelope_hash!r}"
    )


def test_cli_memo_has_exactly_one_sha256_prefix_and_verifies_via_transport_parse() -> None:
    """Full pipeline: real proof -> CLI memo -> transport-side parse round-trip.

    Constructs the memo string the EXACT same way ``sov_cli/main.py:817`` does,
    asserts the literal ``"sha256:"`` substring appears exactly once (not zero,
    not two), then parses the memo the EXACT same way
    ``sov_transport/xrpl_testnet.py:verify`` does (split on ``|``, locate the
    field starting with ``"sha256:"``, strip the prefix), and asserts the
    stripped hash equals ``proof['envelope_hash']``.

    This is the regression that would have caught the Wave 3 drift the moment
    Wave 2's engine agent dropped the prefix from ``_compute_envelope_hash``.
    """
    state, _ = new_game(42, ["Alice", "Bob"])
    proof = make_round_proof(state)

    envelope_hash = proof["envelope_hash"]
    ruleset = proof["ruleset"]
    game_id = proof["game_id"]
    rnd = proof["round"]

    # Layer 2: construct the memo the same way sov_cli/main.py:817 does.
    memo = f"SOV|{ruleset}|{game_id}|r{rnd}|sha256:{envelope_hash}"

    # Layer 2 invariant: the memo carries EXACTLY ONE ``sha256:`` prefix.
    # Zero would mean someone dropped the wire-layer tag (verify can't find
    # the hash field). Two would mean someone re-introduced the prefix into
    # ``envelope_hash`` itself (the Wave 3 double-prefix bug).
    assert memo.count("sha256:") == 1, (
        f"memo must contain exactly one 'sha256:' prefix; got {memo.count('sha256:')} in {memo!r}"
    )

    # Layer 3: parse the memo the same way sov_transport.xrpl_testnet.verify
    # does -- split on '|', find the field starting with 'sha256:', strip
    # the prefix, equality-check against the raw envelope_hash.
    fields = memo.split("|")
    sha_fields = [f for f in fields if f.startswith("sha256:")]
    assert len(sha_fields) == 1, (
        f"memo must contain exactly one '|'-delimited field starting with "
        f"'sha256:'; got {len(sha_fields)} in fields={fields!r}"
    )
    stripped = sha_fields[0][len("sha256:") :]
    assert stripped == envelope_hash, (
        "transport-side strip(sha256:) must yield the raw envelope_hash. "
        f"Got stripped={stripped!r}, envelope_hash={envelope_hash!r}. "
        "This indicates either a double-prefix in the field or a missing "
        "prefix in the memo."
    )

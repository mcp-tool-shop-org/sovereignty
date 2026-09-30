# @mcptoolshop/sovereignty

Run [Sovereignty](https://github.com/mcp-tool-shop-org/sovereignty) — a board game about trust, trade, and keeping your word — without installing Python.

```bash
npx @mcptoolshop/sovereignty tutorial
npx @mcptoolshop/sovereignty play campfire_v1
```

The first run downloads the `sov` binary for your platform from the matching [GitHub Release](https://github.com/mcp-tool-shop-org/sovereignty/releases) and checks it against the release's SHA256 checksums before running it. Every argument goes to `sov`.

Platforms: Linux x64, macOS arm64 (Intel Macs run it under Rosetta), Windows x64.

Other ways to play:

```bash
pip install sovereignty-game
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
```

Handbook: https://mcp-tool-shop-org.github.io/sovereignty/handbook/

MIT licensed. Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/).

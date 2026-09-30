"""Container HEALTHCHECK: authenticated GET /health against the local daemon.

Port and token come from the handshake the daemon writes after binding
(``.sov/daemon.json`` under the working directory, /data in the image).
No handshake means the daemon has not bound yet, so the probe fails.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    try:
        info = json.loads(Path(".sov/daemon.json").read_text(encoding="utf-8"))
        port = int(info["port"])
        token = str(info["token"])
    except (OSError, ValueError, KeyError) as exc:
        print(f"no daemon handshake: {exc}", file=sys.stderr)
        return 1

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return 0 if response.status == 200 else 1
    except OSError as exc:
        print(f"health probe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

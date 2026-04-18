"""CLI entrypoint. Dispatches subcommands."""
from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print("usage: python -m agent_smith "
              "{control-plane,run-agent,seed-admin}", file=sys.stderr)
        sys.exit(2)

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "control-plane":
        from agent_smith.main import run_control_plane
        run_control_plane(rest)
    elif cmd == "run-agent":
        from agent_smith.agent_runner.runner import main as agent_main
        agent_main()
    elif cmd == "seed-admin":
        from dotenv import load_dotenv
        load_dotenv()
        from agent_smith.core.config import load_config
        from agent_smith.auth.seed import seed_admin
        cfg = load_config(rest[0] if rest else "config.yaml")
        seed_admin(cfg.auth.users_file)
    else:
        print(f"unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

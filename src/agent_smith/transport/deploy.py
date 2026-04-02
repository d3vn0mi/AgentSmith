"""Optional: deploy a lightweight agent script to the assessment box."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from agent_smith.transport.ssh import SSHConnection

logger = logging.getLogger(__name__)

AGENT_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"Lightweight agent deployed on the assessment box for persistent command execution.\"\"\"
import json
import subprocess
import sys

def run(cmd, timeout=60):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timeout", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        result = run(cmd)
        print(json.dumps(result))
"""


async def deploy_agent(ssh: SSHConnection, remote_path: str = "/tmp/.agent_smith_runner.py") -> bool:
    """Deploy the lightweight agent script to the remote host."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(AGENT_SCRIPT)
            local_path = f.name

        await ssh.upload_file(local_path, remote_path)
        await ssh.run_command(f"chmod +x {remote_path}")

        # Verify deployment
        result = await ssh.run_command(f"python3 {remote_path} echo test")
        if result.success and "test" in result.stdout:
            logger.info("Agent deployed successfully at %s", remote_path)
            return True

        logger.warning("Agent deployment verification failed")
        return False

    except Exception as e:
        logger.error("Failed to deploy agent: %s", e)
        return False

    finally:
        Path(local_path).unlink(missing_ok=True)

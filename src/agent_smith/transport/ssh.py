"""AsyncSSH connection management for executing commands on the attack box."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import asyncssh

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        """Combined stdout + stderr for display."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n".join(parts)


class SSHConnection:
    """Manages an async SSH connection to the attack box."""

    def __init__(
        self,
        host: str,
        user: str = "root",
        key_path: str | None = None,
        password: str | None = None,
        port: int = 22,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = key_path
        self.password = password
        self.port = port
        self._conn: asyncssh.SSHClientConnection | None = None

    async def connect(self) -> None:
        """Establish SSH connection."""
        connect_kwargs: dict = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "known_hosts": None,  # Accept any host key for pentesting
        }

        if self.key_path:
            key_path = Path(self.key_path).expanduser()
            if key_path.exists():
                connect_kwargs["client_keys"] = [str(key_path)]

        if self.password:
            connect_kwargs["password"] = self.password

        self._conn = await asyncssh.connect(**connect_kwargs)
        logger.info("SSH connected to %s@%s:%d", self.user, self.host, self.port)

    async def disconnect(self) -> None:
        """Close SSH connection."""
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
            logger.info("SSH disconnected from %s", self.host)

    async def run_command(self, cmd: str, timeout: int = 60) -> CommandResult:
        """Execute a command on the remote host."""
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.debug("Executing: %s", cmd)
        try:
            result = await asyncio.wait_for(
                self._conn.run(cmd, check=False),
                timeout=timeout,
            )
            return CommandResult(
                command=cmd,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                exit_code=result.exit_status,
            )
        except asyncio.TimeoutError:
            logger.warning("Command timed out after %ds: %s", timeout, cmd)
            return CommandResult(
                command=cmd,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=None,
                timed_out=True,
            )
        except (asyncssh.Error, OSError) as e:
            logger.error("SSH error running command: %s", e)
            return CommandResult(
                command=cmd,
                stdout="",
                stderr=str(e),
                exit_code=-1,
            )

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the remote host via SFTP."""
        if not self._conn:
            raise RuntimeError("Not connected.")
        async with self._conn.start_sftp_client() as sftp:
            await sftp.put(local_path, remote_path)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the remote host via SFTP."""
        if not self._conn:
            raise RuntimeError("Not connected.")
        async with self._conn.start_sftp_client() as sftp:
            await sftp.get(remote_path, local_path)

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    async def __aenter__(self) -> SSHConnection:
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.disconnect()

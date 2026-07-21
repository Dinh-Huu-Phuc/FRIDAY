from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from friday.googleServiceCloud.credentials import ensure_google_application_credentials


MCP_SERVER_PORT = 8000

logger = logging.getLogger("friday-agent")
logger.setLevel(logging.INFO)


def bootstrap_environment() -> None:
    load_dotenv()
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    ensure_google_application_credentials()


def _get_windows_host_ip() -> str:
    """Get the Windows host IP by looking at the default network route."""
    try:
        cmd = "ip route show default | awk '{print $3}'"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        ip = result.stdout.strip()
        if ip:
            logger.info("Resolved Windows host IP via gateway: %s", ip)
            return ip
    except Exception as exc:
        logger.warning("Gateway resolution failed: %s. Trying fallback...", exc)

    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    ip = line.split()[1]
                    logger.info("Resolved Windows host IP via nameserver: %s", ip)
                    return ip
    except Exception as exc:
        logger.warning("Nameserver fallback resolution failed: %s", exc)

    return "127.0.0.1"


def mcp_server_url() -> str:
    configured_url = os.getenv("MCP_SERVER_URL", "").strip()
    if configured_url:
        logger.info("MCP Server URL: %s", configured_url)
        return configured_url

    # host_ip = _get_windows_host_ip()
    # url = f"http://{host_ip}:{MCP_SERVER_PORT}/sse"
    # url = f"https://ongoing-colleague-samba-pioneer.trycloudflare.com/sse"
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server URL: %s", url)
    return url


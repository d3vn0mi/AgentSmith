"""Verifies the htb_easy_recon playbook loads cleanly via the v2 loader."""
from __future__ import annotations

from pathlib import Path

from agent_smith.scenarios.loader import load_playbook


PB = Path("src/agent_smith/playbooks/htb_easy_recon.yaml")


def test_playbook_loads():
    pb = load_playbook(PB)
    assert pb.name == "htb-easy-recon"
    tt = pb.task_types
    assert set(tt) == {"port_scan", "ffuf_dir", "whatweb",
                         "searchsploit_lookup"}
    assert tt["ffuf_dir"].command_template
    assert "FUZZ" in tt["ffuf_dir"].command_template
    assert tt["port_scan"].parser == "nmap"
    assert tt["ffuf_dir"].parser == "ffuf"
    assert tt["whatweb"].parser == "whatweb"
    assert tt["searchsploit_lookup"].parser == "searchsploit"


def test_expansions_wire_recon_chain():
    pb = load_playbook(PB)
    ids = {r.id for r in pb.expansions}
    assert ids == {"http-enum", "tech-to-cve"}

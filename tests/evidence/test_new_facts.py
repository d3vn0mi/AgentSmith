"""Tests for DirPath/WebTech/Vulnerability fact factories."""
from __future__ import annotations

from agent_smith.evidence.facts import DirPath, WebTech, Vulnerability


def test_dirpath_canonical_key_by_url():
    a = DirPath.new(host="10.0.0.1", port=80,
                     url="http://10.0.0.1/admin", status=301, size=178)
    b = DirPath.new(host="10.0.0.1", port=80,
                     url="http://10.0.0.1/admin", status=301, size=178)
    assert a.canonical_key == b.canonical_key == "dir:http://10.0.0.1/admin"
    assert a.payload["url"] == "http://10.0.0.1/admin"
    assert a.payload["status"] == 301
    assert a.payload["size"] == 178


def test_webtech_canonical_key_slugged():
    a = WebTech.new(host="10.0.0.1", port=80,
                     software="WordPress", version="5.8.1")
    b = WebTech.new(host="10.0.0.1", port=80,
                     software="wordpress", version="5.8.2")
    assert a.canonical_key == b.canonical_key == "tech:10.0.0.1:80:wordpress"
    assert a.payload["software"] == "WordPress"


def test_webtech_spaces_slugged():
    f = WebTech.new(host="h", port=80, software="Apache HTTPD", version=None)
    assert f.canonical_key == "tech:h:80:apache-httpd"


def test_vulnerability_key_prefers_cve():
    a = Vulnerability.new(subject_id="tech:h:80:wordpress",
                           name="WordPress plugin X RCE",
                           cve="CVE-2023-12345",
                           exploit_path="php/webapps/47691.sh")
    assert a.canonical_key == "vuln:tech:h:80:wordpress:CVE-2023-12345"
    assert a.payload["cve"] == "CVE-2023-12345"
    assert a.payload["exploit_path"] == "php/webapps/47691.sh"


def test_vulnerability_key_falls_back_to_name():
    a = Vulnerability.new(subject_id="tech:h:80:nginx",
                           name="Nginx default config disclosure")
    assert a.canonical_key == (
        "vuln:tech:h:80:nginx:Nginx default config disclosure"
    )
    assert a.payload["cve"] is None

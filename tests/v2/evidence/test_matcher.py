"""Tests for fact-shape predicate matching used by expansion rules."""
from __future__ import annotations

import pytest

from agent_smith.evidence.facts import Host, OpenPort, WebEndpoint
from agent_smith.evidence.matcher import parse_predicate


def test_parse_bare_type_matches_any_fact_of_that_type():
    pred = parse_predicate("Host")
    assert pred.type_name == "Host"
    assert pred.matches(Host.new(ip="1.2.3.4"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22))


def test_parse_predicate_with_equality_constraint():
    pred = parse_predicate("OpenPort{service: ssh}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))


def test_alternation_matches_either():
    pred = parse_predicate("OpenPort{service: http|https}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=80, service="http"))
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh"))


def test_present_and_absent():
    present = parse_predicate("OpenPort{service: present}")
    absent = parse_predicate("OpenPort{service: absent}")
    with_service = OpenPort.new(host_ip="1.2.3.4", number=22, service="ssh")
    without_service = OpenPort.new(host_ip="1.2.3.4", number=22, service=None)
    assert present.matches(with_service)
    assert not present.matches(without_service)
    assert absent.matches(without_service)
    assert not absent.matches(with_service)


def test_numeric_range():
    pred = parse_predicate("OpenPort{number: 1-1024}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=22))
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=1024))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=3000))


def test_regex_predicate():
    pred = parse_predicate("WebEndpoint{title: ~/admin/i}")
    assert pred.matches(WebEndpoint.new(url="https://x/1", status=200, title="Admin Panel"))
    assert pred.matches(WebEndpoint.new(url="https://x/2", status=200, title="admin"))
    assert not pred.matches(WebEndpoint.new(url="https://x/3", status=200, title="Home"))


def test_multiple_constraints_all_must_match():
    pred = parse_predicate("OpenPort{service: http|https, number: 1-65535}")
    assert pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="https"))
    assert not pred.matches(OpenPort.new(host_ip="1.2.3.4", number=443, service="ssh"))


def test_invalid_syntax_raises():
    with pytest.raises(ValueError):
        parse_predicate("OpenPort{service ssh}")
    with pytest.raises(ValueError):
        parse_predicate("")

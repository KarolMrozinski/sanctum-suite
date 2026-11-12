import ipaddress
import json

from hypothesis import given, settings, strategies as st

from sanctum_suite.core.target_authorization import normalize_target_host
from sanctum_suite.core.telemetry_adapters import (
    CEFEventFileParser,
    JsonEventFileParser,
    JsonLinesEventFileParser,
)


@settings(max_examples=200, deadline=None)
@given(st.ip_addresses())
def test_target_normalization_is_idempotent_for_ip_addresses(address):
    normalized = normalize_target_host(str(address))

    assert normalized == ipaddress.ip_address(normalized).compressed
    assert normalize_target_host(normalized) == normalized


@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=24),
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.text(max_size=80),
            ),
            max_size=12,
        ),
        min_size=1,
        max_size=20,
    )
)
def test_json_parser_round_trips_bounded_event_objects(events):
    parsed = JsonEventFileParser().parse(json.dumps(events), max_events=20)

    assert parsed == events


@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=24),
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.text(max_size=80),
            ),
            max_size=12,
        ),
        min_size=1,
        max_size=20,
    )
)
def test_jsonl_parser_round_trips_bounded_event_objects(events):
    content = "\n".join(json.dumps(event) for event in events)

    assert JsonLinesEventFileParser().parse(content, max_events=20) == events


@settings(max_examples=500, deadline=None)
@given(st.text(max_size=2_000))
def test_cef_parser_arbitrary_input_returns_events_or_a_validation_error(content):
    try:
        events = CEFEventFileParser().parse(content, max_events=20)
    except ValueError:
        return

    assert 1 <= len(events) <= 20
    assert all(isinstance(event, dict) for event in events)

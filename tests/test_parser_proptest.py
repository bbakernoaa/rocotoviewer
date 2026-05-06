import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from rocototop.parser import RocotoParser

@pytest.fixture
def parser(mock_rocoto_files):
    wf, db = mock_rocoto_files
    return RocotoParser(workflow_file=wf, database_file=db)

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    text=st.text(),
    cycle_dt=st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31))
)
def test_resolve_cyclestr_property(parser, text, cycle_dt):
    # This ensures that resolve_cyclestr doesn't crash on arbitrary text
    # and handles valid datetime objects
    try:
        resolved = parser.resolve_cyclestr(text, cycle_dt)
        assert isinstance(resolved, str)
    except Exception as e:
        pytest.fail(f"resolve_cyclestr crashed with {e}")

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    fmt=st.sampled_from(["@Y", "@m", "@d", "@H", "@M"]),
    cycle_dt=st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31))
)
def test_resolve_cyclestr_simple_tags(parser, fmt, cycle_dt):
    tag = f"<cyclestr>{fmt}</cyclestr>"
    resolved = parser.resolve_cyclestr(tag, cycle_dt)

    # Map Rocoto flags to strftime
    mapping = {
        "@Y": "%Y",
        "@m": "%m",
        "@d": "%d",
        "@H": "%H",
        "@M": "%M"
    }
    expected = cycle_dt.strftime(mapping[fmt])
    assert resolved == expected

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    offset_val=st.integers(min_value=-3600*24, max_value=3600*24),
    cycle_dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2050, 12, 31))
)
def test_resolve_cyclestr_offsets_seconds(parser, offset_val, cycle_dt):
    # Test offset as seconds (Rocoto supports colon-separated or just seconds)
    tag = f'<cyclestr offset="{offset_val}">@Y@m@d@H@M@S</cyclestr>'

    resolved = parser.resolve_cyclestr(tag, cycle_dt)

    expected_dt = cycle_dt + timedelta(seconds=offset_val)
    expected = expected_dt.strftime("%Y%m%d%H%M%S")
    assert resolved == expected

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    hours=st.integers(min_value=0, max_value=23),
    minutes=st.integers(min_value=0, max_value=59),
    seconds=st.integers(min_value=0, max_value=59),
    is_negative=st.booleans(),
    cycle_dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2050, 12, 31))
)
def test_resolve_cyclestr_offsets_hms(parser, hours, minutes, seconds, is_negative, cycle_dt):
    offset_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if is_negative:
        offset_str = "-" + offset_str

    tag = f'<cyclestr offset="{offset_str}">@Y@m@d@H@M@S</cyclestr>'
    resolved = parser.resolve_cyclestr(tag, cycle_dt)

    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if is_negative:
        expected_dt = cycle_dt - delta
    else:
        expected_dt = cycle_dt + delta

    expected = expected_dt.strftime("%Y%m%d%H%M%S")
    assert resolved == expected

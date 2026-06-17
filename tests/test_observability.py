"""M8 observability tests."""

from __future__ import annotations

import json
import logging

from emberforge.observability.logging import JsonLogFormatter, configure_logging
from emberforge.observability.timing import measure_phase, reset_request_timing
from emberforge.settings import Settings


def test_measure_phase_accumulates_llm_ms():
    reset_request_timing()
    with measure_phase("llm"):
        pass
    with measure_phase("llm"):
        pass
    from emberforge.observability.timing import get_request_timing

    timing = get_request_timing()
    assert timing is not None
    assert timing.llm_ms is not None
    assert timing.llm_ms >= 0


def test_json_log_formatter_emits_structured_record():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="emberforge.http",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.event = "http_request"
    record.request_id = "req-1"
    record.method = "POST"
    record.path = "/chat"
    record.status_code = 200
    record.duration_ms = 12.5
    record.timing = {"llm_ms": 8.2}

    payload = json.loads(formatter.format(record))
    assert payload["event"] == "http_request"
    assert payload["request_id"] == "req-1"
    assert payload["timing"]["llm_ms"] == 8.2


def test_configure_logging_json_mode():
    settings = Settings(_env_file=None)
    settings.log_json = True
    configure_logging(settings)
    root = logging.getLogger()
    assert any(isinstance(handler.formatter, JsonLogFormatter) for handler in root.handlers)
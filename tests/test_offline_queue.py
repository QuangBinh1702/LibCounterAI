import os
import tempfile
from unittest.mock import patch

import offline_queue

DB_PATH_HOLDER: list[str] = []

def setup_function():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    DB_PATH_HOLDER.append(path)
    offline_queue.DB_PATH = path

def teardown_function():
    if DB_PATH_HOLDER:
        try:
            os.unlink(DB_PATH_HOLDER[0])
        except OSError:
            pass
        DB_PATH_HOLDER.clear()

def test_enqueue_and_get_pending():
    offline_queue.enqueue("events", "INSERT", {"event_type": "ENTRY", "track_id": 1})
    offline_queue.enqueue("events", "INSERT", {"event_type": "EXIT", "track_id": 2})
    ops = offline_queue.get_pending()
    assert len(ops) == 2
    assert ops[0]["table_name"] == "events"
    assert ops[0]["operation"] == "INSERT"
    assert ops[0]["data"]["event_type"] == "ENTRY"
    assert ops[1]["data"]["event_type"] == "EXIT"

def test_remove_op():
    offline_queue.enqueue("events", "INSERT", {"track_id": 99})
    ops = offline_queue.get_pending()
    op_id = ops[0]["id"]
    offline_queue.remove(op_id)
    remaining = offline_queue.get_pending()
    assert len(remaining) == 0

def test_mark_error_increments_retries():
    offline_queue.enqueue("events", "INSERT", {"track_id": 1})
    ops = offline_queue.get_pending()
    op_id = ops[0]["id"]
    assert ops[0]["retries"] == 0
    offline_queue.mark_error(op_id, "timeout")
    ops = offline_queue.get_pending()
    assert ops[0]["retries"] == 1
    assert ops[0]["last_error"] == "timeout"

def test_mark_error_multiple():
    offline_queue.enqueue("events", "INSERT", {"track_id": 2})
    ops = offline_queue.get_pending()
    op_id = ops[0]["id"]
    offline_queue.mark_error(op_id, "err1")
    offline_queue.mark_error(op_id, "err2")
    ops = offline_queue.get_pending()
    assert ops[0]["retries"] == 2
    assert ops[0]["last_error"] == "err2"

def test_count_pending():
    offline_queue.enqueue("persons", "INSERT", {"full_name": "Alice"})
    offline_queue.enqueue("persons", "INSERT", {"full_name": "Bob"})
    assert offline_queue.count_pending() == 2

def test_get_pending_order():
    offline_queue.enqueue("events", "INSERT", {"seq": 1})
    offline_queue.enqueue("events", "INSERT", {"seq": 2})
    offline_queue.enqueue("events", "INSERT", {"seq": 3})
    ops = offline_queue.get_pending()
    seqs = [op["data"]["seq"] for op in ops]
    assert seqs == [1, 2, 3]

def test_remove_nonexistent():
    offline_queue.remove(99999)
    assert True

def test_enqueue_complex_data():
    data = {
        "event_type": "ENTRY",
        "person_id": 42,
        "metadata_json": {"source": "webcam", "score": 0.95},
        "timestamp": "2026-07-10T12:00:00+00:00",
    }
    offline_queue.enqueue("events", "INSERT", data)
    ops = offline_queue.get_pending()
    last = ops[-1]
    assert last["table_name"] == "events"
    assert last["data"]["metadata_json"]["source"] == "webcam"

def test_enqueue_all_table_types():
    tables = ["events", "visit_sessions", "unknown_identities", "persons"]
    for t in tables:
        offline_queue.enqueue(t, "INSERT", {"test": True})
    ops = offline_queue.get_pending()
    found_tables = {op["table_name"] for op in ops}
    for t in tables:
        assert t in found_tables

def test_get_pending_empty_after_clear():
    offline_queue.enqueue("events", "INSERT", {"x": 1})
    ops = offline_queue.get_pending()
    for op in ops:
        offline_queue.remove(op["id"])
    assert offline_queue.count_pending() == 0

def test_roundtrip_json_preserved():
    data = {"nested": {"a": [1, 2, 3], "b": None}, "flag": True}
    offline_queue.enqueue("events", "INSERT", data)
    ops = offline_queue.get_pending()
    assert ops[0]["data"] == data

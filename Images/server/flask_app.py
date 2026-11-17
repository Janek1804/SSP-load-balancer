
import os
import time
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import traceback
from urllib.parse import parse_qs

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
SERVER_ID = os.getenv("SERVER_ID", "unknown")

def _cgroup_stats():
    # cgroups v2; fallback do v1.
    cpu_max = _text('/sys/fs/cgroup/cpu.max')
    cpu_stat = _text('/sys/fs/cgroup/cpu.stat')
    memory_current = _text('/sys/fs/cgroup/memory.current')
    memory_max = _text('/sys/fs/cgroup/memory.max')

    if cpu_max is not None:
        quota, period = cpu_max.split()[:2]
        quota_cores = (int(quota) / int(period)) if quota != 'max' else None
        stat = {}
        for line in (cpu_stat or '').splitlines():
            parts = line.split()
            if len(parts) == 2:
                stat[parts[0]] = _as_int(parts[1])
        return {
            'version': 2,
            'cpu_quota_cores': quota_cores,
            'cpu_usage_usec': stat.get('usage_usec'),
            'cpu_nr_throttled': stat.get('nr_throttled'),
            'cpu_throttled_usec': stat.get('throttled_usec'),
            'memory_current_bytes': _as_int(memory_current),
            'memory_limit_bytes': _as_int(memory_max),
        }

    quota = _as_int(_text('/sys/fs/cgroup/cpu/cpu.cfs_quota_us'))
    period = _as_int(_text('/sys/fs/cgroup/cpu/cpu.cfs_period_us'))
    cpu_usage_ns = _as_int(_text('/sys/fs/cgroup/cpuacct/cpuacct.usage'))
    mem_used = _as_int(_text('/sys/fs/cgroup/memory/memory.usage_in_bytes'))
    mem_limit = _as_int(_text('/sys/fs/cgroup/memory/memory.limit_in_bytes'))
    return {
        'version': 1 if period else None,
        'cpu_quota_cores': quota / period if quota is not None and quota > 0 and period else None,
        'cpu_usage_usec': cpu_usage_ns // 1000 if cpu_usage_ns is not None else None,
        'cpu_nr_throttled': None,
        'cpu_throttled_usec': None,
        'memory_current_bytes': mem_used,
        'memory_limit_bytes': mem_limit if mem_limit is not None and mem_limit < (1 << 60) else None,
    }


def _consume_cpu(ms):
    if not ms:
        return
    deadline = time.thread_time_ns() + ms * 1_000_000
    digest = hashlib.sha256(b'sdn-load-lab').digest()
    while time.thread_time_ns() < deadline:
        digest = hashlib.sha256(digest).digest()


def _write_disk(kb):
    if not kb:
        return
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    block = b'z' * 65536
    remaining = kb * 1024
    with tempfile.TemporaryFile(mode='w+b', dir=DATA_DIR) as handle:
        while remaining > 0:
            size = min(remaining, len(block))
            handle.write(block[:size])
            remaining -= size
        handle.flush()
        os.fsync(handle.fileno())

@app.after_request
def add_headers(response):
    response.headers["X-Server-Id"] = SERVER_ID
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "server_id": SERVER_ID
    })


@app.get("/stats")
def stats():
    return jsonify({
        "server_id": SERVER_ID,
        "cgroup": _cgroup_stats()
    })


def get_param(name, default, maximum):
    env_name = "WORK_" + name.upper()
    raw = request.args.get(
        name, os.getenv(env_name, str(default))
    )

    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"Nieprawidłowy parametr: {name}")

    if not 0 <= value <= maximum:
        raise ValueError(
            f"{name} musi być w zakresie 0..{maximum}"
        )
    return value


@app.route("/work", methods=["GET", "POST"])
def work():
    try:
        cpu_ms = get_param("cpu_ms", 20, 30000)
        mem_mb = get_param("mem_mb", 0, 512)
        io_kb = get_param("io_kb", 0, 131072)
        sleep_ms = get_param("sleep_ms", 0, 30000)
        response_kb = get_param("response_kb", 0, 1024)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    body = request.get_data() if request.method == "POST" else b""
    started = time.perf_counter()

    try:
        buffer = bytearray(mem_mb * 1024 * 1024)

        for i in range(0, len(buffer), 4096):
            buffer[i] = 1

        _consume_cpu(cpu_ms)
        _write_disk(io_kb)

        if sleep_ms:
            time.sleep(sleep_ms / 1000)

        processing_ms = (
            time.perf_counter() - started
        ) * 1000

        result = {
            "server_id": SERVER_ID,
            "processing_ms": round(processing_ms, 3),
            "cpu_ms": cpu_ms,
            "mem_mb": mem_mb,
            "io_kb": io_kb,
            "sleep_ms": sleep_ms,
            "received_bytes": len(body)
        }

        if response_kb:
            result["padding"] = "x" * (response_kb * 1024)

        return jsonify(result)

    except Exception:
        app.logger.exception("Workload failed")
        return jsonify({"error": "workload failed"}), 500

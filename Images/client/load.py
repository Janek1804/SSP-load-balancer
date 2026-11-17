#!/usr/bin/env python3
import argparse
import asyncio
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

import aiohttp


def percentile(sorted_values, p):
    if not sorted_values:
        return None
    idx = (len(sorted_values) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_values) - 1)
    return round(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo), 3)


async def benchmark(args):
    semaphore = asyncio.Semaphore(args.concurrency)
    rows = []
    pending = set()
    payload = b'a' * (args.body_kb * 1024) if args.method == 'POST' else None
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    connector = aiohttp.TCPConnector(limit=args.concurrency)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector,
                                    headers={'User-Agent': 'sdn-load-lab/1.0'}) as session:
        async def one_request(request_id):
            started = time.perf_counter()
            ts = datetime.now(timezone.utc).isoformat()
            status = 0
            server_id = ''
            received = 0
            err = ''
            try:
                async with session.request(args.method, args.url,
                                           data=payload, ssl=False if args.insecure else None,
                                           allow_redirects=False) as response:
                    status = response.status
                    server_id = response.headers.get('X-Server-Id', '')
                    received = len(await response.read())
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                err = f'{type(exc).__name__}: {exc}'[:200]
            finally:
                rows.append({
                    'request_id': request_id, 'utc': ts,
                    'latency_ms': round((time.perf_counter() - started) * 1000, 3),
                    'status': status, 'server_id': server_id,
                    'bytes_received': received, 'error': err
                })
                semaphore.release()

        loop = asyncio.get_running_loop()
        began = loop.time()
        deadline = began + args.duration
        next_send = began
        count = 0
        interval = 1 / args.rps if args.rps > 0 else 0

        while loop.time() < deadline:
            if interval:
                wait = next_send - loop.time()
                if wait > 0:
                    await asyncio.sleep(min(wait, max(0, deadline - loop.time())))
            await semaphore.acquire()
            if loop.time() >= deadline:
                semaphore.release()
                break
            count += 1
            task = asyncio.create_task(one_request(count))
            pending.add(task)
            task.add_done_callback(pending.discard)
            if interval:
                next_send = max(next_send + interval, loop.time())

        if pending:
            await asyncio.gather(*pending)
        elapsed = loop.time() - began

    rows.sort(key=lambda record: record['request_id'])
    latencies = sorted(row['latency_ms'] for row in rows if 200 <= row['status'] < 300)
    failures = sum(not (200 <= row['status'] < 300) for row in rows)
    by_server = {}
    for row in rows:
        if row['server_id']:
            by_server[row['server_id']] = by_server.get(row['server_id'], 0) + 1
    summary = {
        'url': args.url, 'method': args.method,
        'configured_rps': args.rps, 'concurrency': args.concurrency,
        'configured_duration_s': args.duration,
        'actual_duration_including_drain_s': round(elapsed, 3),
        'requests': len(rows), 'success_2xx': len(latencies),
        'failures_non_2xx_or_transport': failures,
        'achieved_rps_including_drain': round(len(rows) / elapsed, 3) if elapsed else 0,
        'latency_success_ms': {
            'mean': round(statistics.mean(latencies), 3) if latencies else None,
            'p50': percentile(latencies, 50), 'p95': percentile(latencies, 95),
            'p99': percentile(latencies, 99)
        },
        'responses_by_server_id': dict(sorted(by_server.items())),
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=['request_id', 'utc', 'latency_ms',
                                                        'status', 'server_id', 'bytes_received', 'error'])
            writer.writeheader()
            writer.writerows(rows)
        summary['csv_file'] = str(out)
    if args.summary:
        dest = Path(args.summary)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if len(rows) > 0 and failures == 0 else 1


def main():
    parser = argparse.ArgumentParser(description='Generator HTTP/HTTPS do badań SDN')
    parser.add_argument('--url', required=True, help='URL /work serwera lub VIP load balancera')
    parser.add_argument('--method', choices=['GET', 'POST'], default='GET')
    parser.add_argument('--body-kb', type=int, default=0, help='wielkość ciała POST w KiB')
    parser.add_argument('--duration', type=float, default=10, help='czas emisji nowych żądań w sekundach')
    parser.add_argument('--rps', type=float, default=10, help='docelowe request/s; 0 = bez limitu')
    parser.add_argument('--concurrency', type=int, default=20, help='maksymalna liczba żądań in flight')
    parser.add_argument('--timeout', type=float, default=10, help='timeout pojedynczego żądania (s)')
    parser.add_argument('--insecure', action='store_true', help='tylko testy: nie weryfikuj certyfikatu HTTPS')
    parser.add_argument('--output', default='/results/requests.csv', help='CSV z wynikami; puste wyłącza')
    parser.add_argument('--summary', default='', help='opcjonalna ścieżka do podsumowania JSON')
    args = parser.parse_args()
    if args.concurrency < 1 or args.duration <= 0 or args.rps < 0 or args.timeout <= 0 or not 0 <= args.body_kb <= 16384:
        parser.error('concurrency >= 1, duration > 0, rps >= 0, timeout > 0, body-kb 0..16384')
    if not args.url.startswith(('http://', 'https://')):
        parser.error('--url musi zaczynać się od http:// lub https://')
    raise SystemExit(asyncio.run(benchmark(args)))


if __name__ == '__main__':
    main()

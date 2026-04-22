from __future__ import annotations

import argparse
import statistics
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load test for sync-admin/backend endpoints.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of the API")
    parser.add_argument("--requests", type=int, default=50, help="Total number of sync requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent workers")
    parser.add_argument("--empresa-id", default="12345678000199", help="Tenant identifier")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    payload = {
        "empresa_id": args.empresa_id,
        "records": [
            {
                "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "produto": "Carga",
                "valor": "9.90",
                "data": "2026-04-16",
                "data_atualizacao": "2026-04-16T12:00:00+00:00",
            }
        ],
    }

    sync_latencies: list[float] = []
    errors: list[str] = []

    with httpx.Client(timeout=15.0) as client:
        health = client.get(f"{base_url}/health")
        health.raise_for_status()

        admin_token = os.getenv("ADMIN_TOKEN", "admin-token-test")
        provision = client.post(
            f"{base_url}/admin/tenants",
            headers={"X-Admin-Token": admin_token, "X-Audit-Actor": "load.test"},
            json={"empresa_id": args.empresa_id, "nome": "Load Test"},
        )
        provision.raise_for_status()
        api_key = provision.json()["api_key"]

        def do_request() -> float:
            started = time.perf_counter()
            with httpx.Client(timeout=15.0) as thread_client:
                resp = thread_client.post(
                    f"{base_url}/sync",
                    headers={"X-API-Key": api_key, "X-Empresa-Id": args.empresa_id},
                    json=payload,
                )
            elapsed = (time.perf_counter() - started) * 1000.0
            if resp.status_code != 200:
                raise RuntimeError(f"sync failed: {resp.status_code} {resp.text}")
            return elapsed

        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            futures = [executor.submit(do_request) for _ in range(max(1, args.requests))]
            for future in as_completed(futures):
                try:
                    sync_latencies.append(future.result())
                except Exception as exc:
                    errors.append(str(exc))

        metrics = client.get(f"{base_url}/metrics")
        metrics.raise_for_status()

    if errors:
        print("LOAD TEST FAIL")
        for error in errors[:10]:
            print(error)
        return 1

    if not sync_latencies:
        print("LOAD TEST FAIL: no successful requests")
        return 1

    average = statistics.mean(sync_latencies)
    p95 = statistics.quantiles(sync_latencies, n=20)[18] if len(sync_latencies) >= 20 else max(sync_latencies)
    print("LOAD TEST PASS")
    print(f"requests={len(sync_latencies)} concurrency={max(1, args.concurrency)}")
    print(f"avg_ms={average:.2f} p95_ms={p95:.2f} max_ms={max(sync_latencies):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""轻量负载基准（开发环境自测用，非压测平台替代品）。

用法：
    python scripts/load_baseline.py [duration_seconds] [concurrency]

对运行中的后端执行三类请求（登录态）：
  - GET /api/v1/health          （无 DB 压力的探针）
  - GET /api/v1/assets?limit=50 （DB 查询）
  - GET /api/v1/dashboard/stats （聚合查询）
输出 P50/P95/P99 与 RPS，写入 stdout。
"""

import asyncio
import statistics
import sys
import time

import httpx

BASE = "http://localhost:8000"
USERNAME = "admin"


async def get_password() -> str:
    from pathlib import Path

    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("BOOTSTRAP_ADMIN_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD not found in backend/.env")


async def login(client: httpx.AsyncClient, password: str) -> httpx.Cookies:
    r = await client.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": USERNAME, "password": password},
    )
    r.raise_for_status()
    return r.cookies


async def worker(
    client: httpx.AsyncClient,
    paths: list[str],
    stop_at: float,
    latencies: dict[str, list[float]],
    errors: dict[str, int],
):
    while time.monotonic() < stop_at:
        for path in paths:
            start = time.perf_counter()
            try:
                r = await client.get(f"{BASE}{path}")
                elapsed = (time.perf_counter() - start) * 1000
                latencies[path].append(elapsed)
                if r.status_code >= 500:
                    errors[path] = errors.get(path, 0) + 1
            except Exception:
                errors[path] = errors.get(path, 0) + 1


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, int(len(values) * p / 100))
    return values[idx]


async def main() -> None:
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    password = await get_password()

    async with httpx.AsyncClient(cookies=await _login_cookie(password)) as client:
        paths = [
            "/api/v1/health",
            "/api/v1/assets?limit=50",
            "/api/v1/dashboard/stats",
        ]
        latencies: dict[str, list[float]] = {p: [] for p in paths}
        errors: dict[str, int] = {}
        stop_at = time.monotonic() + duration
        started = time.monotonic()

        await asyncio.gather(
            *[
                worker(client, paths, stop_at, latencies, errors)
                for _ in range(concurrency)
            ]
        )
        elapsed = time.monotonic() - started

        total = 0
        print(f"duration={elapsed:.1f}s concurrency={concurrency}")
        for path in paths:
            vals = latencies[path]
            total += len(vals)
            if not vals:
                print(f"{path}: no samples")
                continue
            print(
                f"{path}: n={len(vals)} "
                f"P50={statistics.median(vals):.0f}ms "
                f"P95={pct(vals, 95):.0f}ms "
                f"P99={pct(vals, 99):.0f}ms "
                f"errors={errors.get(path, 0)}"
            )
        print(f"total requests: {total}, RPS: {total / elapsed:.1f}")


async def _login_cookie(password: str) -> httpx.Cookies:
    async with httpx.AsyncClient() as c:
        return await login(c, password)


if __name__ == "__main__":
    asyncio.run(main())

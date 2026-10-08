"""Run models over verified tasks and save every raw response."""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Protocol

from .adapters.base import AdapterError, Settings
from .cache import ResponseCache, cache_key

TEMPERATURE = 0.0


class ModelLike(Protocol):
    provider: str
    model: str
    settings: Settings

    def generate(self, prompt: str, system: str | None = None) -> str: ...


@dataclass
class RunSummary:
    run_id: str
    out_dir: Path
    total: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    errors: int = 0


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(adapters: Iterable[ModelLike], tasks: list[dict], cache: ResponseCache, results_dir: Path, *,
        run_id: str | None = None, system: str | None = None,
        log: Callable[[str], None] = lambda _m: None) -> RunSummary:
    """Call every adapter on every task. Unverified tasks are refused outright."""
    adapters = list(adapters)
    unverified = [t["id"] for t in tasks if t.get("verified") is not True]
    if unverified:
        raise ValueError(f"refusing to run unverified tasks: {', '.join(unverified[:5])}")
    for a in adapters:
        if a.settings.temperature != TEMPERATURE:
            raise ValueError(f"{a.provider}/{a.model}: temperature must be {TEMPERATURE}")

    run_id = run_id or new_run_id()
    out_dir = Path(results_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=False)  # never overwrite an earlier run
    summary = RunSummary(run_id=run_id, out_dir=out_dir)

    meta = {
        "run_id": run_id,
        "started": datetime.now(timezone.utc).isoformat(),
        "models": [{"provider": a.provider, "model": a.model} for a in adapters],
        "temperature": TEMPERATURE,
        "task_ids": [t["id"] for t in tasks],
        "system": system,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    lock = threading.Lock()

    with (out_dir / "responses.jsonl").open("w", encoding="utf-8") as f:
        def work(a: ModelLike) -> None:
            # Models run side by side (each has its own rate limiter); tasks run in order per model.
            for t in tasks:
                key = cache_key(a.provider, a.model, t["prompt"], system, a.settings)
                response, cached, error = cache.get(key), True, None
                if response is None:
                    cached = False
                    try:
                        response = a.generate(t["prompt"], system)
                        cache.put(key, response, provider=a.provider, model=a.model)
                    except AdapterError as e:
                        error = str(e)
                row = {
                    "run_id": run_id, "task_id": t["id"], "category": t["category"],
                    "provider": a.provider, "model": a.model, "temperature": a.settings.temperature,
                    "system": system, "prompt": t["prompt"], "response": response,
                    "cached": cached, "error": error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                with lock:
                    summary.total += 1
                    if error:
                        summary.errors += 1
                        log(f"ERROR {a.model} {t['id']}: {error}")
                    elif cached:
                        summary.cache_hits += 1
                    else:
                        summary.api_calls += 1
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    log(f"{a.model} {t['id']} {'cache' if cached else ('ERROR' if error else 'api')}")

        if adapters:
            with ThreadPoolExecutor(max_workers=len(adapters)) as pool:
                for fut in [pool.submit(work, a) for a in adapters]:
                    fut.result()
    return summary

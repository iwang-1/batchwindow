"""Discrete-event simulator for a single padded inference device."""
import argparse
import csv
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Request:
    id: str
    arrival: int
    tokens: int
    deadline: int


def read_trace(path):
    with Path(path).open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["id", "arrival", "tokens", "deadline"]:
            raise ValueError("expected CSV columns id,arrival,tokens,deadline")
        return [Request(r["id"], int(r["arrival"]), int(r["tokens"]), int(r["deadline"])) for r in reader]


def cost(batch, setup):
    return setup + len(batch) * max(r.tokens for r in batch)


def simulate(requests, policy, *, capacity=4, budget=256, wait=15, setup=12):
    if policy not in ("single", "fifo", "deadline"):
        raise ValueError("unknown policy")
    if min(capacity, budget) < 1 or min(wait, setup) < 0:
        raise ValueError("invalid device or batching limits")
    if len({r.id for r in requests}) != len(requests):
        raise ValueError("duplicate request id")
    for r in requests:
        if not r.id or r.arrival < 0 or r.deadline < r.arrival or not 1 <= r.tokens <= budget:
            raise ValueError(f"invalid request: {r.id}")
    future = deque(sorted(requests, key=lambda r: (r.arrival, r.id)))
    pending, batches, latencies = [], [], []
    now = misses = busy = padding = 0
    while future or pending:
        if not pending and future:
            now = max(now, future[0].arrival)
        while future and future[0].arrival <= now:
            pending.append(future.popleft())
        if policy == "deadline":
            ordered = sorted(pending, key=lambda r: (r.deadline, r.arrival, r.id))
        else:
            ordered = pending
        batch = [ordered[0]]
        max_count = 1 if policy == "single" else capacity
        for r in ordered[1:]:
            if len(batch) == max_count:
                break
            candidate = batch + [r]
            duration = cost(candidate, setup)
            if duration - setup > budget:
                if policy == "fifo":
                    break
                continue
            if policy == "deadline" and now + duration > min(x.deadline for x in batch):
                continue
            batch = candidate
        wake = min(r.arrival for r in pending) + wait
        if policy == "deadline":
            wake = min(wake, min(r.deadline for r in batch) - cost(batch, setup))
        if len(batch) < max_count and now < wake:
            now = min(wake, future[0].arrival) if future else wake
            continue
        ids = {r.id for r in batch}
        pending = [r for r in pending if r.id not in ids]
        duration = cost(batch, setup)
        finish = now + duration
        late = [r.id for r in batch if finish > r.deadline]
        waste = duration - setup - sum(r.tokens for r in batch)
        batches.append(dict(start=now, finish=finish, ids=[r.id for r in batch], late=late, padding=waste))
        misses += len(late)
        padding += waste
        busy += duration
        latencies.extend(finish - r.arrival for r in batch)
        now = finish
    latencies.sort()
    return {"policy": policy, "batches": batches, "metrics": {
        "requests": len(requests), "batches": len(batches), "late": misses, "device_ticks": busy,
        "padding_tokens": padding, "p95_latency_ticks": latencies[(95 * len(latencies) - 1) // 100] if latencies else None}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--policy", choices=["single", "fifo", "deadline", "all"], default="all")
    parser.add_argument("--capacity", type=int, default=4)
    parser.add_argument("--budget", type=int, default=256)
    parser.add_argument("--wait", type=int, default=15)
    parser.add_argument("--setup", type=int, default=12)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()
    try:
        trace = read_trace(args.trace)
        policies = ["single", "fifo", "deadline"] if args.policy == "all" else [args.policy]
        reports = [simulate(trace, p, capacity=args.capacity, budget=args.budget,
                            wait=args.wait, setup=args.setup) for p in policies]
        if not args.details:
            for report in reports:
                del report["batches"]
        print(json.dumps(reports, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"batchwindow: {exc}\n")


if __name__ == "__main__":
    main()

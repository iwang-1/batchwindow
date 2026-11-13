"""Find the minimum feasible miss count with advance knowledge of a small trace."""
import argparse
import itertools
import json

from planner import cost, read_trace, simulate


def optimal_schedule(rows, capacity=4, budget=256, setup=12):
    if len(rows) > 10:
        raise ValueError("exact search supports up to ten requests")
    simulate(rows, "single", capacity=capacity, budget=budget, setup=setup)
    full = (1 << len(rows)) - 1
    # For identical completed work and miss count, an earlier finish dominates.
    states = [{} for _ in range(full + 1)]
    states[0][0] = 0
    parents = {}
    for mask in range(full):
        available = [i for i in range(len(rows)) if not mask & (1 << i)]
        for size in range(1, min(capacity, len(available)) + 1):
            for indices in itertools.combinations(available, size):
                batch = [rows[i] for i in indices]
                duration = cost(batch, setup)
                if duration - setup > budget:
                    continue
                ready = max(r.arrival for r in batch)
                next_mask = mask | sum(1 << i for i in indices)
                target = states[next_mask]
                for missed, end in states[mask].items():
                    finish = max(end, ready) + duration
                    score = missed + sum(finish > r.deadline for r in batch)
                    if score not in target or finish < target[score]:
                        target[score] = finish
                        parents[next_mask, score] = (mask, missed, indices)
    score = min(states[full])
    mask, missed = full, score
    batches = []
    while mask:
        finish = states[mask][missed]
        mask, missed, indices = parents[mask, missed]
        batch = [rows[i] for i in indices]
        batches.append({"ids": [r.id for r in batch], "start": finish - cost(batch, setup),
                        "finish": finish, "late": [r.id for r in batch if r.deadline < finish]})
    return {"minimum_deadline_misses": score, "batches": batches[::-1]}


def minimum_misses(rows, capacity=4, budget=256, setup=12):
    return optimal_schedule(rows, capacity, budget, setup)["minimum_deadline_misses"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()
    try:
        report = optimal_schedule(read_trace(args.trace))
        if not args.schedule:
            del report["batches"]
        print(json.dumps(report, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"oracle: {exc}\n")

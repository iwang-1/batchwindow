"""Find the minimum feasible miss count with advance knowledge of a small trace."""
import argparse
import itertools
import json

from planner import cost, read_trace, simulate


def minimum_misses(rows, capacity=4, budget=256, setup=12):
    if len(rows) > 10:
        raise ValueError("exact search supports up to ten requests")
    simulate(rows, "single", capacity=capacity, budget=budget, setup=setup)
    full = (1 << len(rows)) - 1
    # For identical completed work and miss count, an earlier finish dominates.
    states = [{} for _ in range(full + 1)]
    states[0][0] = 0
    for mask in range(full):
        available = [i for i in range(len(rows)) if not mask & (1 << i)]
        for size in range(1, min(capacity, len(available)) + 1):
            for indices in itertools.combinations(available, size):
                batch = [rows[i] for i in indices]
                duration = cost(batch, setup)
                if duration - setup > budget:
                    continue
                ready = max(r.arrival for r in batch)
                target = states[mask | sum(1 << i for i in indices)]
                for missed, end in states[mask].items():
                    finish = max(end, ready) + duration
                    score = missed + sum(finish > r.deadline for r in batch)
                    if score not in target or finish < target[score]:
                        target[score] = finish
    return min(states[full])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    args = parser.parse_args()
    try:
        print(json.dumps({"minimum_deadline_misses": minimum_misses(read_trace(args.trace))}))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"oracle: {exc}\n")

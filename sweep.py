"""Compare online schedulers with an exact reference across seeded workload shapes."""
import argparse
import json
import random
import statistics

from oracle import minimum_misses
from planner import Request, simulate


def generate(profile, seed):
    rng = random.Random(seed)
    rows = []
    arrival = 0
    for i in range(8):
        if profile == "bursty":
            arrival = (i // 4) * 75 + rng.randrange(5)
            length = rng.choice([4, 8, 32])
        elif profile == "uniform":
            arrival = i * 12
            length = 8
        elif profile == "mixed":
            arrival += rng.randrange(16)
            length = rng.choice([4, 8, 16, 48])
        else:
            raise ValueError("unknown workload")
        rows.append(Request(str(i), arrival, length, arrival + length + rng.randint(12, 80)))
    return rows


def sweep(seeds):
    summaries = []
    for profile in ("bursty", "uniform", "mixed"):
        samples = {p: [] for p in ("single", "fifo", "deadline")}
        for seed in range(seeds):
            rows = generate(profile, seed)
            optimum = minimum_misses(rows)
            for policy, values in samples.items():
                misses = simulate(rows, policy)["metrics"]["late"]
                if misses < optimum:
                    raise AssertionError("online result beat exact reference")
                values.append(misses - optimum)
        for policy, gaps in samples.items():
            summaries.append(dict(profile=profile, policy=policy, traces=seeds,
                                  optimal_count=gaps.count(0), median_extra_misses=statistics.median(gaps),
                                  worst_extra_misses=max(gaps)))
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=16)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error("positive seed count required")
    print(json.dumps(sweep(args.seeds), indent=2))

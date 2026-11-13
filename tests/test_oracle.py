import itertools
import random
import unittest

from oracle import minimum_misses
from planner import Request, simulate


class OracleTests(unittest.TestCase):
    def test_against_exhaustive_orders_and_batch_cuts(self):
        for seed in range(12):
            rng = random.Random(seed)
            rows = [Request(str(i), rng.randrange(5), rng.randint(1, 4), rng.randrange(5, 25)) for i in range(4)]
            best = len(rows)
            for order in itertools.permutations(rows):
                for cuts in range(8):
                    groups = [[order[0]]]
                    for i, row in enumerate(order[1:]):
                        if cuts & (1 << i):
                            groups.append([])
                        groups[-1].append(row)
                    if any(len(g) > 2 or len(g)*max(r.tokens for r in g) > 6 for g in groups):
                        continue
                    end = missed = 0
                    for g in groups:
                        end = max(end, *(r.arrival for r in g)) + 2 + len(g)*max(r.tokens for r in g)
                        missed += sum(end > r.deadline for r in g)
                    best = min(best, missed)
            self.assertEqual(minimum_misses(rows, 2, 6, 2), best)
            for p in ("single", "fifo", "deadline"):
                self.assertGreaterEqual(simulate(rows, p, capacity=2, budget=6, setup=2)["metrics"]["late"], best)

    def test_witness_is_feasible_and_attains_score(self):
        from oracle import optimal_schedule
        from planner import cost
        for seed in range(30):
            rng = random.Random(seed)
            rows = [Request(str(i), rng.randrange(15), rng.randint(1, 6), rng.randrange(15, 48)) for i in range(6)]
            report = optimal_schedule(rows, 3, 12, 3)
            previous = late = 0
            seen = []
            for b in report["batches"]:
                batch = [rows[int(i)] for i in b["ids"]]
                self.assertLessEqual(len(batch), 3)
                self.assertLessEqual(cost(batch, 0), 12)
                self.assertGreaterEqual(b["start"], max(previous, *(r.arrival for r in batch)))
                self.assertEqual(b["finish"], b["start"] + cost(batch, 3))
                previous = b["finish"]
                late += sum(previous > r.deadline for r in batch)
                seen.extend(b["ids"])
            self.assertCountEqual(seen, [r.id for r in rows])
            self.assertEqual(late, report["minimum_deadline_misses"])

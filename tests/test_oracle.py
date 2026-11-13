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

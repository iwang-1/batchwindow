import random
import unittest

from planner import Request, simulate


class SchedulingTests(unittest.TestCase):
    def test_deadline_limits_wait(self):
        request = Request("a", 10, 8, 32)
        result = simulate([request], "deadline", wait=100)
        batch, = result["batches"]
        self.assertEqual((batch["start"], batch["finish"]), (12, 32))

    def test_padding_creates_deadline_miss(self):
        requests = [Request("a", 0, 2, 20), Request("b", 0, 16, 100)]
        self.assertEqual(simulate(requests, "fifo", wait=0)["metrics"]["late"], 1)
        self.assertEqual(simulate(requests, "deadline", wait=0)["metrics"]["late"], 0)

    def test_future_arrival_cannot_change_dispatched_batch(self):
        original = [Request("a", 0, 8, 100)]
        extra = Request("b", 16, 3, 90)
        for policy in ("single", "fifo", "deadline"):
            self.assertEqual(simulate(original, policy)["batches"][0],
                             simulate(original + [extra], policy)["batches"][0])

    def test_randomized_accounting(self):
        for seed in range(50):
            rng = random.Random(seed)
            rows = [Request(str(i), rng.randrange(100), rng.randint(1, 32), 160+i) for i in range(30)]
            by_id = {r.id: r for r in rows}
            for policy in ("single", "fifo", "deadline"):
                result = simulate(rows, policy, budget=64)
                seen, previous, device, padding, late = [], 0, 0, 0, 0
                for b in result["batches"]:
                    members = [by_id[i] for i in b["ids"]]
                    work = len(members) * max(r.tokens for r in members)
                    self.assertLessEqual(work, 64)
                    self.assertLessEqual(len(members), 4)
                    self.assertGreaterEqual(b["start"], max(previous, max(r.arrival for r in members)))
                    self.assertEqual(b["finish"] - b["start"], 12 + work)
                    previous = b["finish"]
                    device += 12 + work
                    padding += work - sum(r.tokens for r in members)
                    late += sum(previous > r.deadline for r in members)
                    seen.extend(b["ids"])
                self.assertCountEqual(seen, by_id.keys())
                for key, expected in [("device_ticks", device), ("padding_tokens", padding), ("late", late)]:
                    self.assertEqual(result["metrics"][key], expected)

    def test_empty_or_invalid(self):
        self.assertIsNone(simulate([], "fifo")["metrics"]["p95_latency_ticks"])
        with self.assertRaises(ValueError):
            simulate([Request("a", 0, 65, 1)], "fifo", budget=64)

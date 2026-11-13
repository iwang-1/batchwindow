# BatchWindow

A trace-driven simulator for deadline-aware inference batching. Packing more requests into each batch saves launch overhead. A single long input can undo that saving because every input in the batch gets padded to its length. BatchWindow compares three online scheduling policies on the same arrival stream and includes an exact offline reference for small traces.

## Run it

Python 3.11+, standard library only.

```sh
python3 planner.py examples/burst.csv
python3 planner.py examples/burst.csv --policy deadline --details
python3 oracle.py examples/oracle-burst.csv
python3 -m unittest discover -v
```

Supply a CSV with columns `id,arrival,tokens,deadline`. Arrival and absolute deadline use integer ticks. Set capacity, padded-token budget, maximum batching wait and launch overhead with `--capacity`, `--budget`, `--wait` and `--setup`. Detailed output gives dispatch and finish ticks, batch membership, missed deadlines and wasted padding per batch.

## Recorded synthetic experiment

| Policy | Late requests out of 12 | Device ticks | Padding tokens | p95 latency in ticks |
| --- | ---: | ---: | ---: | ---: |
| Single request | 7 | 372 | 0 | 202 |
| FIFO batching | 12 | 484 | 220 | 330 |
| Deadline-aware batching | 4 | 338 | 2 | 216 |

The deadline policy completes more requests on time here while its p95 latency exceeds single-request serving. Each request has its own absolute deadline. Deadline misses and tail latency measure different objectives. [Input trace](examples/burst.csv) · [Reproducible output](examples/results.json)

## Model and algorithms

One non-preemptive device executes one batch at a time. Batch duration is launch overhead plus batch size times the longest input length. Padding is the difference between padded and useful tokens. At a decision point the scheduler sees arrived requests. A future arrival can wake a waiting scheduler but cannot revise an already dispatched batch.

Single-request serving drains by arrival order. FIFO batching packs the oldest contiguous prefix within the limits. Deadline-aware batching anchors on the earliest deadline, skips additions that would make the selected members late and caps waiting by remaining deadline slack. Late work is still served. P95 uses the nearest-rank definition. Times describe this cost model only. There are no hardware throughput measurements or autoregressive decode stages.

The offline reference minimizes total misses with advance knowledge of up to ten requests. It enumerates feasible next batches and retains the earliest finish for each completed-request subset and miss count. An earlier finish can reproduce every later schedule by waiting. For a fixed batch ordering, starting as soon as its members are available can only improve completion times. These two properties let the search discard dominated schedules.

The regression suite checks resource limits, causality, completion and accounting across 50 seeded traces under all three policies. A separate test compares the exact solver against exhaustive orderings and batch cuts on twelve four-request fixtures.

## How far are the online policies from optimal?

Run `python3 sweep.py` to compare all three policies against the exact miss count on 48 eight-request traces, across bursty arrivals, uniform lengths and mixed lengths. Under bursty arrivals FIFO missed a median of six more deadlines than the optimum, while the deadline-aware scheduler missed three more. Under uniform lengths their median gaps were both two, and the deadline policy's worst gap was five versus three for FIFO. With these inputs, optimizing the dispatch decision for the earliest deadline can still leave other requests waiting. [Full results and denominators](examples/oracle-sweep.json)

# TPP Direct Plan Writer

Generates valid text plans for Traveling Purchaser Problem PDDL tasks by reading each domain/problem pair, constructing a grounded purchase-and-delivery action sequence, validating it against the parsed state, and writing the final plan to the required output path.

## When to Use

Use when `problem.json` lists PDDL `domain`, `problem`, and `plan_output` paths for TPP-style purchase/logistics tasks and the required artifact is a valid executable plan file.

## How to Use

1. Read `problem.json`; for each task load only the referenced `domain` and `problem` files.
2. Extract the exact action schemas, object names, init facts, and goal facts. Preserve symbol spelling/case and each action's argument order exactly.
3. Prefer direct TPP synthesis over broad planner search: identify required goods, find markets that provide them, route the vehicle through the needed `drive`/`buy`/`load`/`unload` style actions, and reuse any level/capacity arguments already present in the problem.
4. Validate the draft plan by simulating actions step by step: every precondition must hold, effects must update state correctly, and the final state must satisfy all goals. Repair the first failing step locally instead of restarting from scratch.
5. Write only the final grounded plan to `plan_output`, one action per line, with no extra text or sidecar files.
6. If the domain is not clearly TPP-like or direct synthesis stalls, use a classical planner once as fallback, then validate and emit the same text format.


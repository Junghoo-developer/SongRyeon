from __future__ import annotations

from songryeon_core.runtime.dry_run import run_dry_turn


if __name__ == "__main__":
    result = run_dry_turn()
    print("DRY_RUN_OK")
    print(f"turn_id={result['turn_id']}")
    print(f"trace_count={result['trace_count']}")
    print(f"data_record_count={result['data_record_count']}")
    print(f"movement_count={result['movement_count']}")
    print(f"current_route={result['current_route']}")
    print(f"capsule_trace_count={result['capsule_trace_count']}")
    print(result["report"])

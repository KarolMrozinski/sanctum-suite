from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sanctum_suite.core.smpc import _read_party_input

try:
    from mpyc.runtime import mpc
except ImportError as error:
    raise SystemExit(
        "SMPC support requires the optional sanctum-suite[smpc] dependencies"
    ) from error


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--decision-threshold", required=True, type=int)
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    if len(mpc.parties) != 3 or mpc.threshold != 1:
        raise SystemExit("The local SMPC protocol requires 3 parties and threshold 1")
    if not 0 <= arguments.decision_threshold <= 3_000_000:
        raise SystemExit("The public decision threshold is outside the supported range")

    local_value = _read_party_input(arguments.input_file)
    secure_int = mpc.SecInt(32)

    async def compute() -> None:
        await mpc.start()
        inputs = mpc.input(
            secure_int(local_value),
            senders=range(len(mpc.parties)),
        )
        aggregate = mpc.sum(inputs)
        threshold_reached = aggregate >= secure_int(arguments.decision_threshold)
        aggregate_value, reached = await mpc.output([aggregate, threshold_reached])
        if mpc.pid == 0:
            print(
                "SANCTUM_SMPC_RESULT="
                + json.dumps(
                    {
                        "aggregate_value": int(aggregate_value),
                        "threshold_reached": bool(reached),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        await mpc.shutdown()

    mpc.run(compute())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"SMPC participant failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from error

from __future__ import annotations

import importlib.util
import json
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_PARTY_COUNT = 3
_PARTY_THRESHOLD = 1
_MAX_PARTY_INPUT_BYTES = 16 * 1024
_MAX_PARTY_VALUE = 1_000_000
_PROCESS_TIMEOUT_SECONDS = 45


class SMPCError(RuntimeError):
    """Raised when the local SMPC demonstration cannot complete safely."""


def _read_party_input(path: Path) -> int:
    try:
        with path.open("rb") as source:
            raw = source.read(_MAX_PARTY_INPUT_BYTES + 1)
    except OSError as error:
        raise SMPCError("Cannot read a participant input file") from error
    if len(raw) > _MAX_PARTY_INPUT_BYTES:
        raise SMPCError("Participant input file exceeds the 16 KiB limit")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SMPCError("Participant input must be valid UTF-8 JSON") from error
    if (
        not isinstance(document, dict)
        or set(document) != {"value"}
        or not isinstance(document["value"], int)
        or isinstance(document["value"], bool)
        or not 0 <= document["value"] <= _MAX_PARTY_VALUE
    ):
        raise SMPCError("Participant input must contain one integer value from 0 to 1000000")
    return document["value"]


def _validate_input_files(paths: list[Path]) -> None:
    for path in paths:
        try:
            if not path.is_file() or path.stat().st_size > _MAX_PARTY_INPUT_BYTES:
                raise SMPCError(
                    "Each participant input must be a file no larger than 16 KiB"
                )
        except OSError as error:
            raise SMPCError("Cannot access a participant input file") from error


def _choose_base_port() -> int:
    for _ in range(20):
        base_port = random.randint(20_000, 55_000)
        probes: list[socket.socket] = []
        try:
            for port in range(base_port, base_port + _PARTY_COUNT):
                probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                probes.append(probe)
                probe.bind(("127.0.0.1", port))
            return base_port
        except OSError:
            continue
        finally:
            for probe in probes:
                probe.close()
    raise SMPCError("Could not reserve loopback ports for the local SMPC demo")


def _parse_party_result(stdout: str) -> dict[str, Any]:
    reports = []
    for line in stdout.splitlines():
        if line.startswith("SANCTUM_SMPC_RESULT="):
            try:
                reports.append(json.loads(line.partition("=")[2]))
            except json.JSONDecodeError as error:
                raise SMPCError("SMPC participant returned an invalid result") from error
    if len(reports) != 1:
        raise SMPCError("SMPC participants did not produce exactly one aggregate result")
    report = reports[0]
    if (
        not isinstance(report, dict)
        or set(report) != {"aggregate_value", "threshold_reached"}
        or not isinstance(report["aggregate_value"], int)
        or isinstance(report["aggregate_value"], bool)
        or not isinstance(report["threshold_reached"], bool)
    ):
        raise SMPCError("SMPC aggregate result has an invalid schema")
    return report


def run_local_smpc_demo(
    *,
    participant_input_files: list[Path],
    decision_threshold: int,
) -> dict[str, Any]:
    """Run three separate loopback MPyC processes for a demo-only private sum."""
    if len(participant_input_files) != _PARTY_COUNT:
        raise SMPCError("The local SMPC demo requires exactly three participant input files")
    resolved_inputs = [path.resolve() for path in participant_input_files]
    if len(set(resolved_inputs)) != _PARTY_COUNT:
        raise SMPCError("Each SMPC participant must use a separate input file")
    if (
        not isinstance(decision_threshold, int)
        or isinstance(decision_threshold, bool)
        or not 0 <= decision_threshold <= _PARTY_COUNT * _MAX_PARTY_VALUE
    ):
        raise SMPCError("Decision threshold must be an integer from 0 to 3000000")
    if importlib.util.find_spec("mpyc") is None:
        raise SMPCError("Install the optional SMPC dependencies with sanctum-suite[smpc]")
    _validate_input_files(resolved_inputs)

    base_port = _choose_base_port()
    processes: list[subprocess.Popen[str]] = []
    try:
        for party_index, input_file in enumerate(resolved_inputs):
            command = [
                sys.executable,
                "-m",
                "sanctum_suite.core.smpc_worker",
                "--input-file",
                str(input_file),
                "--decision-threshold",
                str(decision_threshold),
                "-M",
                str(_PARTY_COUNT),
                "-I",
                str(party_index),
                "-T",
                str(_PARTY_THRESHOLD),
                "-B",
                str(base_port),
                "--no-log",
            ]
            processes.append(
                subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            )
        deadline = time.monotonic() + _PROCESS_TIMEOUT_SECONDS
        while True:
            exit_codes = [process.poll() for process in processes]
            if any(code not in {None, 0} for code in exit_codes):
                raise SMPCError(
                    "At least one MPyC participant failed; no result was accepted"
                )
            if all(code == 0 for code in exit_codes):
                break
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(
                    processes[0].args, _PROCESS_TIMEOUT_SECONDS
                )
            time.sleep(0.05)
        outputs = [process.communicate()[0] for process in processes]
        result = _parse_party_result(outputs[0])
    except subprocess.TimeoutExpired as error:
        raise SMPCError("The local SMPC protocol timed out; no result was accepted") from error
    except OSError as error:
        raise SMPCError("Could not start the local MPyC participants") from error
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass

    return {
        "status": "LOCAL_SMPC_DEMO_COMPLETED",
        "backend": "MPyC",
        "participant_count": _PARTY_COUNT,
        "threshold": _PARTY_THRESHOLD,
        "security_model": "semi-honest; experimental local demonstration only",
        **result,
        "limitations": [
            "Each participant's input is secret-shared during the computation; only the aggregate and threshold bit are revealed.",
            "This local demo runs all three participants on one host and does not provide organizational separation.",
            "It is not secure against actively malicious participants, a compromised host, or network observation outside the loopback interface.",
            "It is not approved for production, regulated, or classified data.",
        ],
    }

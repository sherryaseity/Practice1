#!/usr/bin/env python3
"""Report CPU and GPU configuration/status."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess


def _read_cpu_model() -> str:
    cpuinfo_path = "/proc/cpuinfo"
    if os.path.exists(cpuinfo_path):
        try:
            with open(cpuinfo_path, "r", encoding="utf-8") as cpuinfo:
                for line in cpuinfo:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "Unknown"


def get_cpu_status() -> dict[str, object]:
    status: dict[str, object] = {
        "architecture": platform.machine(),
        "logical_cores": os.cpu_count(),
        "model": _read_cpu_model(),
    }

    if hasattr(os, "getloadavg"):
        try:
            one, five, fifteen = os.getloadavg()
            status["load_average"] = {
                "1min": round(one, 2),
                "5min": round(five, 2),
                "15min": round(fifteen, 2),
            }
        except OSError:
            status["load_average"] = "Unavailable"

    return status


def get_gpu_status() -> dict[str, object]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"status": "nvidia-smi not found (NVIDIA GPU may be unavailable)"}

    query_fields = [
        "name",
        "driver_version",
        "memory.total",
        "memory.used",
        "utilization.gpu",
        "temperature.gpu",
    ]
    command = [
        nvidia_smi,
        f"--query-gpu={','.join(query_fields)}",
        "--format=csv,noheader,nounits",
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as err:
        return {
            "status": "Failed to query GPU status",
            "error": err.stderr.strip() or str(err),
        }

    gpus = []
    for line in result.stdout.strip().splitlines():
        values = [part.strip() for part in line.split(",")]
        if len(values) != len(query_fields):
            continue
        gpus.append(
            {
                "name": values[0],
                "driver_version": values[1],
                "memory_total_mb": values[2],
                "memory_used_mb": values[3],
                "utilization_percent": values[4],
                "temperature_c": values[5],
            }
        )

    if not gpus:
        return {"status": "No GPUs reported by nvidia-smi"}

    return {"status": "OK", "gpus": gpus}


def main() -> None:
    report = {
        "cpu": get_cpu_status(),
        "gpu": get_gpu_status(),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

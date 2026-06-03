"""GPU availability and memory diagnostics for the /health endpoint."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_gpu_info() -> Dict[str, Any]:
    """
    Return GPU availability and memory stats.
    Safe to call even when TensorFlow is not installed.
    """
    try:
        import tensorflow as tf

        gpus: List = tf.config.list_physical_devices("GPU")

        if not gpus:
            return {
                "available": False,
                "count": 0,
                "devices": [],
                "framework": f"TensorFlow {tf.__version__}",
            }

        devices = []
        for i, gpu in enumerate(gpus):
            device_info: Dict[str, Any] = {
                "index": i,
                "name": gpu.name,
                "device_type": gpu.device_type,
            }
            try:
                mem = tf.config.experimental.get_memory_info(f"GPU:{i}")
                device_info["memory_mb"] = {
                    "current": round(mem["current"] / (1024 ** 2), 2),
                    "peak": round(mem["peak"] / (1024 ** 2), 2),
                }
            except Exception:
                device_info["memory_mb"] = None

            devices.append(device_info)

        return {
            "available": True,
            "count": len(gpus),
            "devices": devices,
            "framework": f"TensorFlow {tf.__version__}",
        }

    except ImportError:
        return {
            "available": False,
            "count": 0,
            "devices": [],
            "framework": "TensorFlow not installed",
        }
    except Exception as exc:
        logger.warning(f"Could not retrieve GPU info: {exc}")
        return {
            "available": False,
            "count": 0,
            "devices": [],
            "error": str(exc),
        }

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    import rclpy
    from rclpy.node import Node
    from px4_msgs.msg import VehicleStatus
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError(
        "ROS 2 dependencies not available. Ensure rclpy and px4_msgs are installed."
    ) from exc

from .config import load_raw_config
from .logging_manager import RecorderManager


class AutoStartLoggerNode(Node):
    def __init__(self, config_path: Path) -> None:
        super().__init__("agi_logger_autostart")
        self._config_path = config_path
        self._config = load_raw_config(config_path)
        self._logger_cfg = self._config["agi_logger"]["logger"]
        self._auto_start = bool(self._logger_cfg.get("auto_start", False))
        self._behavior = str(self._logger_cfg.get("auto_start_behavior", "toggle_arm"))
        self._manager = RecorderManager(self._config, config_path)
        self._last_arming_state = None

        self._sub = self.create_subscription(
            VehicleStatus,
            "/fmu/out/vehicle_status",
            self._on_vehicle_status,
            10,
        )
        self.get_logger().info("AGI logger autostart node initialized")

    def _on_vehicle_status(self, msg: VehicleStatus) -> None:
        if not self._auto_start:
            return

        armed = msg.arming_state == msg.ARMING_STATE_ARMED
        if self._behavior == "toggle_arm":
            if self._last_arming_state is None:
                self._last_arming_state = msg.arming_state
                return
            if not self._manager.is_recording() and armed and self._last_arming_state != msg.arming_state:
                self.get_logger().info("Vehicle armed: starting bag recording")
                try:
                    self._manager.start_recording()
                except Exception as exc:  # pragma: no cover
                    self.get_logger().error(f"Failed to start recording: {exc}")
        else:
            if armed and not self._manager.is_recording():
                self.get_logger().info("Vehicle armed: starting bag recording")
                try:
                    self._manager.start_recording()
                except Exception as exc:  # pragma: no cover
                    self.get_logger().error(f"Failed to start recording: {exc}")

        self._last_arming_state = msg.arming_state


def run_autostart_node(config_path: Path) -> None:
    rclpy.init()
    node = AutoStartLoggerNode(config_path)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

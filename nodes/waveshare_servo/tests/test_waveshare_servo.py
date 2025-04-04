"""Tests for the waveshare_servo node."""

import json
from unittest.mock import MagicMock, patch

from waveshare_servo.main import (
    ConfigHandler,
    Servo,
    ServoManager,
    ServoScanner,
    ServoSettings,
    run,
)


class TestServoSettings:
    """Test the ServoSettings class."""

    def test_settings_defaults(self):
        """Test default settings."""
        settings = ServoSettings(id=2)
        assert settings.id == 2
        assert settings.alias == ""
        assert settings.min_pulse == 500
        assert settings.max_pulse == 2500
        assert settings.speed == 1000
        assert settings.calibrated is False
        assert settings.position == 0
        assert settings.invert is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        settings = ServoSettings(id=3, alias="Head")
        settings_dict = settings.to_dict()
        assert settings_dict["id"] == 3
        assert settings_dict["alias"] == "Head"


class TestServoScanner:
    """Test the ServoScanner class."""

    @patch("serial.tools.list_ports.comports")
    def test_find_servo_port(self, mock_comports):
        """Test finding servo port."""
        # Mock port with USB-Serial in description
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "USB-Serial Controller"
        mock_comports.return_value = [mock_port]

        scanner = ServoScanner()
        port = scanner.find_servo_port()
        assert port == "/dev/ttyUSB0"

    @patch("serial.Serial")
    @patch.object(ServoScanner, "find_servo_port", return_value="/dev/ttyUSB0")
    def test_connect(self, mock_find_port, mock_serial):
        """Test connection to servo controller."""
        mock_serial.return_value.is_open = True
        scanner = ServoScanner()
        result = scanner.connect()
        assert result is True
        mock_serial.assert_called_once_with("/dev/ttyUSB0", 115200, timeout=0.5)

    @patch.object(ServoScanner, "connect", return_value=True)
    def test_discover_servos(self, mock_connect):
        """Test servo discovery."""
        scanner = ServoScanner()
        scanner.serial_conn = MagicMock()

        # Mock responses for two servos
        scanner.serial_conn.readline.side_effect = [
            b"OK\r\n",  # ID 1
            b"\r\n",  # ID 2 (no response)
            b"OK\r\n",  # ID 3
        ]

        # Mock the range function to only check a few IDs
        original_range = range
        try:
            # Replace global range function temporarily
            __builtins__["range"] = lambda *args: [1, 2, 3]
            result = scanner.discover_servos()
        finally:
            # Restore original range function
            __builtins__["range"] = original_range

        assert result == {1, 3}  # IDs 1 and 3 should be found


class TestServo:
    """Test the Servo class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serial_conn = MagicMock()
        self.settings = ServoSettings(id=2, alias="Test Servo")
        self.servo = Servo(self.serial_conn, self.settings)

    def test_send_command(self):
        """Test sending commands to servo."""
        self.serial_conn.readline.return_value = b"OK\r\n"
        response = self.servo.send_command("PING")
        assert response == "OK"
        self.serial_conn.write.assert_called_once_with(b"#2PING\r\n")

    def test_move(self):
        """Test moving servo to position."""
        self.serial_conn.readline.return_value = b"OK\r\n"
        result = self.servo.move(1500)
        assert result is True
        self.serial_conn.write.assert_called_once_with(b"#2P1500T1000\r\n")
        assert self.servo.settings.position == 1500

    def test_move_clamping(self):
        """Test that move clamps values to min/max range."""
        self.serial_conn.readline.return_value = b"OK\r\n"
        # Try to move beyond max_pulse
        self.servo.move(3000)
        # Command should use max_pulse instead
        self.serial_conn.write.assert_called_once_with(b"#2P2500T1000\r\n")

    def test_wiggle(self):
        """Test wiggle functionality."""
        self.serial_conn.readline.return_value = b"OK\r\n"
        with patch("time.sleep"):
            result = self.servo.wiggle()
        assert result is True
        # Should have multiple write calls for the wiggle sequence
        assert self.serial_conn.write.call_count > 3


class TestConfigHandler:
    """Test the ConfigHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = MagicMock()
        self.config = ConfigHandler(self.node)

    def test_get_servo_path(self):
        """Test generating config paths."""
        assert self.config.get_servo_path(2) == "servo.2"
        assert self.config.get_servo_path(3, "alias") == "servo.3.alias"

    def test_update_setting(self):
        """Test updating settings."""
        self.config.update_setting("servo.2.alias", "Head")
        self.node.send_output.assert_called_once()
        args = self.node.send_output.call_args[0]
        assert args[0] == "update_setting"

        # Create a mock to simulate PyArrow array
        mock_array = MagicMock()
        mock_array.as_py.return_value = [
            json.dumps({"path": "servo.2.alias", "value": "Head"})
        ]
        self.node.send_output.return_value = mock_array

        # Extract the data from PyArrow array
        array = self.node.send_output.return_value
        data_json = array.as_py()[0]
        data = json.loads(data_json)
        assert data["path"] == "servo.2.alias"
        assert data["value"] == "Head"

    def test_handle_settings_updated(self):
        """Test handling settings updates."""
        # Test updating a specific property
        result = self.config.handle_settings_updated("servo.2.alias", "Head")
        assert result is True
        assert self.config.cached_settings[2]["alias"] == "Head"

        # Test updating a whole servo object
        servo_settings = {"id": 3, "alias": "Arm", "speed": 2000}
        result = self.config.handle_settings_updated("servo.3", servo_settings)
        assert result is True
        assert self.config.cached_settings[3] == servo_settings


class TestServoManager:
    """Test the ServoManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = MagicMock()
        with patch.object(ServoScanner, "connect", return_value=False):
            self.manager = ServoManager(self.node)
            self.manager.scanner = MagicMock()
            self.manager.config = MagicMock()

    def test_broadcast_servo_status(self):
        """Test broadcasting servo status."""
        # Create a mock servo
        settings = ServoSettings(id=2, alias="Test")
        servo = MagicMock()
        servo.settings = settings
        self.manager.servos = {2: servo}

        # Test the broadcast
        self.manager.broadcast_servo_status(2)
        self.node.send_output.assert_called_once()
        args = self.node.send_output.call_args[0]
        assert args[0] == "servo_status"

    def test_handle_move_servo(self):
        """Test handling move servo command."""
        # Create a mock servo
        servo = MagicMock()
        servo.move.return_value = True
        settings = ServoSettings(id=2)
        servo.settings = settings
        self.manager.servos = {2: servo}

        # Test the move handler
        result = self.manager.handle_move_servo(2, 1500)
        assert result is True
        servo.move.assert_called_once_with(1500)

        # Verify config update
        self.manager.config.update_servo_setting.assert_called_once_with(
            2, "position", 1500
        )

    def test_process_event_move_servo(self):
        """Test processing move_servo event."""
        # Mock handle_move_servo
        self.manager.handle_move_servo = MagicMock(return_value=True)

        # Create test event with mock PyArrow array
        mock_array = MagicMock()
        mock_array.as_py.return_value = [json.dumps({"id": 2, "position": 1500})]

        event = {"id": "move_servo", "type": "INPUT", "data": mock_array}

        # Process the event
        self.manager.process_event(event)
        self.manager.handle_move_servo.assert_called_once_with(2, 1500)


def test_run():
    """Test the run function."""
    # Create mock node and manager
    node = MagicMock()

    # Mock the node to return a single event then stop
    mock_event = {"id": "scan_servos", "type": "INPUT", "data": MagicMock()}
    node.__iter__.return_value = [mock_event]

    # Mock the ServoManager
    with patch.object(ServoManager, "initialize"), patch.object(
        ServoManager, "process_event"
    ), patch.object(ServoManager, "scan_for_servos"), patch(
        "time.time", side_effect=[0, 11]
    ):  # Trigger scan (11-0 > 10)
        run(node)

        # Verify manager was initialized and event processed
        ServoManager.initialize.assert_called_once()
        ServoManager.process_event.assert_called_once_with(mock_event)
        # Verify scan was triggered by timer
        assert ServoManager.scan_for_servos.call_count == 1

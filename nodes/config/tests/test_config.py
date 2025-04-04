import os
import json
import pytest
import tempfile
from config.main import ConfigManager


def test_import_main():
    from config.main import main

    # Check that everything is working, and catch dora Runtime Exception as we're not running in a dora dataflow.
    with pytest.raises(RuntimeError):
        main()


class TestConfigManager:
    def setup_method(self):
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_settings.json")
        self.config_manager = ConfigManager(self.config_path)

    def teardown_method(self):
        # Clean up temporary files
        self.temp_dir.cleanup()

    def test_init_creates_empty_config(self):
        assert os.path.exists(self.config_path)
        with open(self.config_path, "r") as f:
            data = json.load(f)
        assert data == {}

    def test_update_setting_root_level(self):
        result = self.config_manager.update_setting("test_key", "test_value")
        assert result == {"path": "test_key", "value": "test_value"}
        assert self.config_manager.get_setting("test_key") == "test_value"

        # Verify file was updated
        with open(self.config_path, "r") as f:
            data = json.load(f)
        assert data["test_key"] == "test_value"

    def test_update_setting_nested(self):
        result = self.config_manager.update_setting("parent.child", "child_value")
        assert result == {"path": "parent.child", "value": "child_value"}
        assert self.config_manager.get_setting("parent.child") == "child_value"

        # Verify the structure
        with open(self.config_path, "r") as f:
            data = json.load(f)
        assert data["parent"]["child"] == "child_value"

    def test_update_setting_with_list(self):
        # Setting array elements
        self.config_manager.update_setting("servo.0.speed", 10)
        self.config_manager.update_setting("servo.1.speed", 20)
        self.config_manager.update_setting("servo.2.speed", 30)

        # Verify values
        assert self.config_manager.get_setting("servo.0.speed") == 10
        assert self.config_manager.get_setting("servo.1.speed") == 20
        assert self.config_manager.get_setting("servo.2.speed") == 30

        # Verify the structure
        with open(self.config_path, "r") as f:
            data = json.load(f)
        assert data["servo"][0]["speed"] == 10
        assert data["servo"][1]["speed"] == 20
        assert data["servo"][2]["speed"] == 30

    def test_update_creates_intermediate_structures(self):
        # Setting a deeply nested value
        self.config_manager.update_setting("a.b.c.d.e", "deep_value")
        
        # Verify value
        assert self.config_manager.get_setting("a.b.c.d.e") == "deep_value"
        
        # Verify intermediate structures were created
        assert self.config_manager.get_setting("a.b.c.d") == {"e": "deep_value"}
        assert isinstance(self.config_manager.get_setting("a"), dict)
        assert isinstance(self.config_manager.get_setting("a.b"), dict)

    def test_get_nonexistent_setting(self):
        # Get non-existent value
        assert self.config_manager.get_setting("nonexistent") is None
        assert self.config_manager.get_setting("a.b.nonexistent") is None

    def test_get_all_settings(self):
        # Add some settings
        self.config_manager.update_setting("key1", "value1")
        self.config_manager.update_setting("key2.nested", "value2")
        
        # Get all settings
        settings = self.config_manager.get_all_settings()
        
        # Verify
        assert settings["key1"] == "value1"
        assert settings["key2"]["nested"] == "value2"


if __name__ == "__main__":
    pytest.main(["-v", "test_config.py"])

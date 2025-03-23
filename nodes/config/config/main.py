from dora import Node
import pyarrow as pa
import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config_file_path = Path(config_file_path)
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or create new if not exists."""
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, "r") as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                print("Error parsing config file. Using empty configuration.")
                self.config = {}
        else:
            # Create directory if it doesn't exist
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        with open(self.config_file_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_setting(self, path: str) -> Any:
        """Get a setting by dot notation path.
        
        Args:
            path: Dot notation path (e.g., 'servo.3.speed')
        
        Returns:
            The setting value or None if not found
        """
        parts = path.split(".")
        current = self.config
        
        for part in parts:
            # Handle array indices in path
            if part.isdigit() and isinstance(current, list):
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            elif part in current:
                current = current[part]
            else:
                return None
        
        return current

    def update_setting(self, path: str, value: Any) -> Dict[str, Any]:
        """Update a setting by dot notation path.
        
        Args:
            path: Dot notation path (e.g., 'servo.3.speed')
            value: The value to set
        
        Returns:
            Dict containing the path and new value
        """
        parts = path.split(".")
        
        # Handle the case where we're setting a root-level property
        if len(parts) == 1:
            self.config[parts[0]] = value
            self._save_config()
            return {"path": path, "value": value}
            
        # Navigate to the correct nested location
        current = self.config
        for i, part in enumerate(parts[:-1]):
            # Handle list indices for the current level
            if part.isdigit() and isinstance(current, list):
                index = int(part)
                # Extend list if needed
                while len(current) <= index:
                    current.append({})
                current = current[index]
                continue
                
            # Create path if it doesn't exist
            if part not in current:
                # If next part is a number, create a list
                if i + 1 < len(parts) - 1 and parts[i + 1].isdigit():
                    current[part] = []
                else:
                    current[part] = {}
            
            # Move to the next level
            current = current[part]
                
        # Set the final value
        last_part = parts[-1]
        if last_part.isdigit() and isinstance(current, list):
            index = int(last_part)
            while len(current) <= index:
                current.append(None)
            current[index] = value
        else:
            current[last_part] = value
            
        self._save_config()
        return {"path": path, "value": value}

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings.
        
        Returns:
            The entire configuration dictionary
        """
        return self.config


def main():
    node = Node()
    config_path = os.path.join(os.getcwd(), "config", "settings.json")
    config_manager = ConfigManager(config_path)
    
    print(f"Config node started. Config file path: {config_path}")

    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "update_setting":
                try:
                    # Expect input as {path: string, value: any}
                    data = event["value"].to_pylist()[0]
                    if isinstance(data, dict) and "path" in data and "value" in data:
                        path = data["path"]
                        value = data["value"]
                        
                        # Update the setting
                        result = config_manager.update_setting(path, value)
                        
                        # Notify about the change
                        node.send_output(
                            output_id="setting_updated",
                            data=pa.array([result]),
                            metadata={}
                        )
                        print(f"Updated setting {path} to {value}")
                    else:
                        print(f"Invalid update_setting format: {data}")
                except Exception as e:
                    print(f"Error processing update_setting: {e}")
            
            elif event["id"] == "tick":
                try:
                    # Send all settings on the tick event
                    settings = config_manager.get_all_settings()
                    node.send_output(
                        output_id="settings",
                        data=pa.array([settings]),
                        metadata={}
                    )
                except Exception as e:
                    print(f"Error sending settings on tick: {e}")


if __name__ == "__main__":
    main()
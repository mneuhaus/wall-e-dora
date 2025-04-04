"""Event data extraction utility for the Waveshare Servo Node."""

import json
import traceback
from typing import Any, Dict, Optional, Tuple


def extract_event_data(event: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    """Extract data payload from a Dora input event.

    Handles various potential formats, including checking both 'data' and 'value'
    fields, converting PyArrow arrays (including StructArrays) to Python objects,
    and attempting to parse JSON strings.

    Args:
        event: The Dora input event dictionary.

    Returns:
        A tuple containing:
            - The extracted data payload (can be dict, list, str, etc.) or None if extraction fails.
            - An error message string if an error occurred, otherwise None.
    """
    if event["type"] != "INPUT":
        return None, "Not an INPUT event"
        
    try:
        # Try to get data either from "data" or "value" field
        data_field = None
        
        # Try primary data field
        if "data" in event and event["data"] is not None:
            data_field = event["data"]
        # Try value field as backup
        elif "value" in event and event["value"] is not None:
            data_field = event["value"]
        
        if data_field is None:
            return None, "No data or value field in event"
            
        # Convert Arrow array to Python objects
        if hasattr(data_field, "as_py"):
            data_list = data_field.as_py()
            if not data_list or len(data_list) == 0:
                return None, "Empty data list"
                
            # Try to parse JSON if it's a string
            data = data_list[0]
            if isinstance(data, str):
                try:
                    return json.loads(data), None
                except json.JSONDecodeError as e:
                    return data, None  # Return raw string if not valid JSON
            else:
                return data, None  # Return whatever we got
        
        # Handle StructArray or other Arrow types
        elif hasattr(data_field, "to_pylist"):
            data_list = data_field.to_pylist()
            if not data_list or len(data_list) == 0:
                return None, "Empty data list"
            return data_list[0], None
            
        # Direct access for dictionary
        elif isinstance(data_field, dict):
            return data_field, None
            
        # Fallback
        return data_field, None
            
    except Exception as e:
        return None, f"Error extracting data: {str(e)}"

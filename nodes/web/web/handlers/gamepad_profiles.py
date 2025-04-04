"""Module for handling gamepad profile management.

Provides storage, retrieval, and management of gamepad control mappings,
persisting profiles to JSON files in both the project config directory
and the user's home directory. Includes handlers for Dora events related
to gamepad profiles.
"""

import os
import json
import pyarrow as pa
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List


class GamepadProfileManager:
    """Manages gamepad profiles with persistence to JSON files.

    Handles loading, saving, retrieving, and deleting gamepad profiles.
    Profiles are stored in two locations: the project's `config/gamepad_profiles`
    directory (intended for version control) and the user's home directory
    at `~/.wall-e-dora/gamepad_profiles` (for user-specific overrides).
    """

    def __init__(self, profiles_dir: str = None):
        """Initialize the profile manager.

        Args:
            profiles_dir: Optional path to the user-specific profiles directory.
                          If None, defaults to `~/.wall-e-dora/gamepad_profiles/`.
        """
        # Store profiles in two locations
        # 1. Project config directory (for version control)
        self.project_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
        self.config_profiles_dir = self.project_dir / "config" / "gamepad_profiles"
        os.makedirs(self.config_profiles_dir, exist_ok=True)
        print(f"DEBUG - GamepadProfileManager: Project config profiles dir: {self.config_profiles_dir}")
        
        # 2. User's home directory (for per-user settings)
        if profiles_dir is None:
            home_dir = os.path.expanduser("~")
            profiles_dir = os.path.join(home_dir, ".wall-e-dora", "gamepad_profiles")
            
        self.profiles_dir = Path(profiles_dir)
        # Create directory if it doesn't exist
        os.makedirs(self.profiles_dir, exist_ok=True)
        print(f"DEBUG - GamepadProfileManager: User profiles dir: {self.profiles_dir}")
        
        # Cache of loaded profiles
        # Primary key is gamepad ID, secondary index by vendor+product
        self.profiles = {}
        self.profiles_by_vendor_product = {}
        
        # Load all existing profiles
        self.load_all_profiles()

    def load_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load all existing profiles from both storage locations.

        Reads all `.json` files from the project config directory and the
        user profiles directory. Profiles are indexed by their full gamepad ID
        and optionally by a `vendorId:productId` key if available.

        Returns:
            A dictionary mapping gamepad IDs to their loaded profile data.
        """
        self.profiles = {}
        self.profiles_by_vendor_product = {}
        
        # Find all JSON files in both directories
        profile_dirs = [self.profiles_dir, self.config_profiles_dir]
        
        for directory in profile_dirs:
            print(f"DEBUG - load_all_profiles: Loading profiles from {directory}")
            json_files = list(directory.glob("*.json"))
            print(f"DEBUG - load_all_profiles: Found {len(json_files)} files in {directory}")
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r') as f:
                        profile = json.load(f)
                        
                    if 'id' in profile:
                        # Use the gamepad ID as the primary key
                        self.profiles[profile['id']] = profile
                        
                        # Also index by vendor+product if available
                        vendor_id = profile.get('vendorId')
                        product_id = profile.get('productId')
                        
                        if vendor_id and product_id:
                            vendor_product_key = f"{vendor_id}:{product_id}".lower()
                            self.profiles_by_vendor_product[vendor_product_key] = profile
                            print(f"DEBUG - load_all_profiles: Indexed profile by vendor+product '{vendor_product_key}'")
                        
                        print(f"DEBUG - load_all_profiles: Loaded profile for '{profile['id']}' from {file_path}")
                except Exception as e:
                    print(f"Error loading profile from {file_path}: {e}")
        
        print(f"Loaded {len(self.profiles)} gamepad profiles")
        return self.profiles

    def save_profile(self, profile: Dict[str, Any]) -> bool:
        """Save a gamepad profile to both storage locations.

        Generates a filename based on vendor/product IDs if available, otherwise
        uses a sanitized version of the gamepad ID. Writes the profile data
        as JSON to both the project config and user profile directories.

        Args:
            profile: The profile data dictionary. Must include an 'id' key.
                     Should ideally include 'name', 'vendorId', 'productId',
                     and 'mapping'.

        Returns:
            True if the profile was saved successfully to at least one location
            and updated in the cache, False otherwise.
        """
        if not profile or 'id' not in profile:
            print("Cannot save profile: missing required 'id' field")
            return False
        
        gamepad_id = profile['id']
        vendor_id = profile.get('vendorId')
        product_id = profile.get('productId')
        
        # Generate filename based on vendor+product IDs if available, otherwise use gamepad ID
        if vendor_id and product_id:
            filename_base = f"{vendor_id}_{product_id}"
            vendor_product_key = f"{vendor_id}:{product_id}".lower()
        else:
            filename_base = "".join(c if c.isalnum() else "_" for c in gamepad_id)
            vendor_product_key = None
        
        # Ensure the filename is safe
        safe_name = "".join(c if c.isalnum() else "_" for c in filename_base)
        
        # Save to both user directory and project config directory
        user_file_path = self.profiles_dir / f"{safe_name}.json"
        config_file_path = self.config_profiles_dir / f"{safe_name}.json"
        
        print(f"DEBUG - save_profile: Writing profile to user directory: {user_file_path}")
        print(f"DEBUG - save_profile: Writing profile to config directory: {config_file_path}")
        
        # Check directories
        print(f"DEBUG - save_profile: User directory exists: {self.profiles_dir.exists()}")
        print(f"DEBUG - save_profile: User directory is writable: {os.access(self.profiles_dir, os.W_OK)}")
        print(f"DEBUG - save_profile: Config directory exists: {self.config_profiles_dir.exists()}")
        print(f"DEBUG - save_profile: Config directory is writable: {os.access(self.config_profiles_dir, os.W_OK)}")
        
        success = True
        
        # Save to user directory
        try:
            with open(user_file_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            print(f"DEBUG - save_profile: Successfully wrote profile to {user_file_path}")
            print(f"DEBUG - save_profile: File exists after writing: {user_file_path.exists()}")
            print(f"DEBUG - save_profile: File size: {user_file_path.stat().st_size} bytes")
        except Exception as e:
            print(f"Error saving profile to user directory: {e}")
            print(f"DEBUG - save_profile: Exception details: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            success = False
        
        # Save to config directory
        try:
            with open(config_file_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            print(f"DEBUG - save_profile: Successfully wrote profile to {config_file_path}")
            print(f"DEBUG - save_profile: File exists after writing: {config_file_path.exists()}")
            print(f"DEBUG - save_profile: File size: {config_file_path.stat().st_size} bytes")
        except Exception as e:
            print(f"Error saving profile to config directory: {e}")
            print(f"DEBUG - save_profile: Exception details: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            success = False
        
        # Update the cache
        if success or user_file_path.exists() or config_file_path.exists():
            # Update primary index by gamepad ID
            self.profiles[gamepad_id] = profile
            
            # Update secondary index by vendor+product if available
            if vendor_product_key:
                self.profiles_by_vendor_product[vendor_product_key] = profile
                print(f"DEBUG - save_profile: Added to vendor+product index: {vendor_product_key}")
            
            print(f"Saved gamepad profile for '{gamepad_id}' to both locations")
            return True
        else:
            return False

    def get_profile(self, gamepad_id: str) -> Optional[Dict[str, Any]]:
        """Get a gamepad profile by its full ID or vendor/product ID.

        First attempts a direct lookup using the full gamepad ID string.
        If not found, it tries to extract vendor and product IDs from the
        string (e.g., "Vendor: XXXX Product: YYYY") and looks up using
        the `vendorId:productId` key.

        Args:
            gamepad_id: The unique identifier string for the gamepad.

        Returns:
            The profile data dictionary if found, otherwise None.
        """
        # First, try direct lookup by full gamepad ID
        profile = self.profiles.get(gamepad_id)
        if profile:
            print(f"DEBUG - get_profile: Found profile by ID: {gamepad_id}")
            return profile
            
        # If not found, try to extract vendor and product IDs and look up by those
        try:
            # Extract vendor and product IDs from the gamepad ID
            import re
            vendor_match = re.search(r'Vendor:\s*([0-9a-fA-F]+)', gamepad_id)
            product_match = re.search(r'Product:\s*([0-9a-fA-F]+)', gamepad_id)
            
            if vendor_match and product_match:
                vendor_id = vendor_match.group(1).strip().lower()
                product_id = product_match.group(1).strip().lower()
                vendor_product_key = f"{vendor_id}:{product_id}"
                
                print(f"DEBUG - get_profile: Extracted vendor+product: {vendor_product_key}")
                
                # Look up by vendor+product
                profile = self.profiles_by_vendor_product.get(vendor_product_key)
                if profile:
                    print(f"DEBUG - get_profile: Found profile by vendor+product: {vendor_product_key}")
                    return profile
        except Exception as e:
            print(f"DEBUG - get_profile: Error extracting vendor/product: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"DEBUG - get_profile: No profile found for gamepad: {gamepad_id}")
        return None

    def get_profile_by_vendor_product(self, vendor_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a gamepad profile directly by vendor and product IDs.

        Args:
            vendor_id: The vendor ID string (e.g., "2dc8").
            product_id: The product ID string (e.g., "200b").

        Returns:
            The profile data dictionary if found, otherwise None.
        """
        vendor_product_key = f"{vendor_id}:{product_id}".lower()
        profile = self.profiles_by_vendor_product.get(vendor_product_key)
        
        if profile:
            print(f"DEBUG - get_profile_by_vendor_product: Found profile for {vendor_product_key}")
        else:
            print(f"DEBUG - get_profile_by_vendor_product: No profile found for {vendor_product_key}")
            
        return profile

    def delete_profile(self, gamepad_id: str) -> bool:
        """Delete a gamepad profile from the user directory and cache.

        Note: This currently only deletes from the user directory, not the
              project config directory, to avoid accidental deletion of
              version-controlled profiles.

        Args:
            gamepad_id: The unique identifier string for the gamepad.

        Returns:
            True if the profile was successfully deleted, False otherwise.
        """
        if gamepad_id not in self.profiles:
            print(f"No profile found for gamepad '{gamepad_id}'")
            return False
        
        # Generate the filename
        safe_name = "".join(c if c.isalnum() else "_" for c in gamepad_id)
        file_path = self.profiles_dir / f"{safe_name}.json"
        
        try:
            if file_path.exists():
                os.remove(file_path)
            
            # Remove from cache
            del self.profiles[gamepad_id]
            print(f"Deleted gamepad profile for '{gamepad_id}'")
            return True
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False

    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        """List all currently loaded profiles.

        Returns:
            A dictionary mapping gamepad IDs to their profile data.
        """
        return self.profiles


# -----------------------------------------------------------------------------
# Dora Event Handlers
# -----------------------------------------------------------------------------

def handle_save_gamepad_profile(event: Dict, node, profile_manager: GamepadProfileManager):
    """Handle the 'save_gamepad_profile' Dora input event.

    Extracts profile data from the event, validates it, saves it using the
    profile manager, and emits an updated list of profiles.

    Args:
        event: The Dora input event dictionary. Expected value is a PyArrow
               array containing a single dictionary representing the profile.
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    print(f"DEBUG - handle_save_gamepad_profile: Got event: {event}")
    print(f"DEBUG - handle_save_gamepad_profile: Event type: {type(event)}")
    
    try:
        # Get the value from the event and convert from pyarrow array if needed
        if hasattr(event['value'], 'to_pylist'):
            profile_data = event['value'].to_pylist()
            print(f"DEBUG - handle_save_gamepad_profile: Converted pyarrow to list: {profile_data}")
        else:
            profile_data = event['value']
        
        print(f"DEBUG - handle_save_gamepad_profile: Profile data type: {type(profile_data)}")
        
        if not profile_data:
            print("No profile data provided in event")
            return
        
        # Handle StructArray by converting to dictionaries
        if isinstance(profile_data, list) and len(profile_data) > 0:
            if hasattr(profile_data[0], 'keys') and callable(profile_data[0].keys):
                # Already a dict-like object
                profile_data = profile_data[0]
            else:
                # Try to convert pyarrow struct to dict
                try:
                    print(f"DEBUG - Attempting to convert StructArray to dict")
                    # Handle the case of a StructArray
                    import pyarrow as pa
                    if isinstance(event['value'], pa.lib.StructArray):
                        profile_dict = {}
                        struct_array = event['value']
                        
                        # Get the schema fields
                        fields = struct_array.type
                        
                        # Extract values for each field
                        for i, field in enumerate(fields):
                            name = field.name
                            profile_dict[name] = struct_array.field(i).to_pylist()[0]
                        
                        print(f"DEBUG - Converted to dict: {profile_dict}")
                        profile_data = profile_dict
                    else:
                        # For any other PyArrow array
                        profile_data = profile_data[0] if isinstance(profile_data, list) else profile_data
                except Exception as e:
                    print(f"DEBUG - Error converting StructArray: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: try again with to_pydict if available
                    try:
                        if hasattr(event['value'], 'to_pydict'):
                            profile_dict = event['value'].to_pydict()
                            print(f"DEBUG - Used to_pydict: {profile_dict}")
                            # Construct a single dictionary from the first elements of each column
                            profile_data = {k: v[0] for k, v in profile_dict.items()}
                    except Exception as e2:
                        print(f"DEBUG - Second conversion error: {e2}")
                        traceback.print_exc()
        
        print(f"DEBUG - Final profile data structure: {profile_data}")
        
        # Validate profile data
        if not isinstance(profile_data, dict):
            print(f"Profile data is not a dict: {type(profile_data)}")
            return
            
        if 'id' not in profile_data:
            print(f"Missing 'id' field in profile data")
            return
            
        if 'mapping' not in profile_data:
            print(f"Missing 'mapping' field in profile data")
            return
        
        # Ensure profile has a name
        if 'name' not in profile_data or not profile_data['name']:
            profile_data['name'] = f"Profile for {profile_data['id']}"
        
        print(f"DEBUG - handle_save_gamepad_profile: About to save profile: {profile_data}")
        
        # Save the profile
        success = profile_manager.save_profile(profile_data)
        print(f"DEBUG - handle_save_gamepad_profile: Save result: {success}")
        
        # Emit the updated list of profiles
        if success:
            # Use node.send_output instead of emit
            try:
                emit_profiles_list(node, profile_manager)
                print(f"DEBUG - handle_save_gamepad_profile: Emitted updated profiles list")
            except Exception as e:
                print(f"DEBUG - Error in emit_profiles_list: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"DEBUG - Unexpected error in handle_save_gamepad_profile: {e}")
        import traceback
        traceback.print_exc()


def handle_get_gamepad_profile(event: Dict, node, profile_manager: GamepadProfileManager):
    """Handle the 'get_gamepad_profile' Dora input event.

    Extracts the requested gamepad ID, retrieves the profile using the
    profile manager, and emits the profile data (or a not found status)
    back via the 'gamepad_profile' output.

    Args:
        event: The Dora input event dictionary. Expected value contains
               a dictionary with a 'gamepad_id' key.
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    request_data = event.get('value')
    if not request_data:
        print("No request data provided in event")
        return
    
    # Extract the first element if it's a list
    if isinstance(request_data, list) and len(request_data) > 0:
        request_data = request_data[0]
    
    # Get the gamepad ID
    gamepad_id = request_data.get('gamepad_id')
    if not gamepad_id:
        print("No gamepad_id provided in request")
        return
    
    # Get the profile
    profile = profile_manager.get_profile(gamepad_id)
    
    # Emit the profile (or None if not found)
    if profile:
        response = {
            'gamepad_id': gamepad_id,
            'name': profile.get('name', ''),
            'mapping': profile.get('mapping', {})
        }
        node.emit('gamepad_profile', pa.array([response]))
    else:
        node.emit('gamepad_profile', pa.array([{'gamepad_id': gamepad_id, 'exists': False}]))


def handle_check_gamepad_profile(event: Dict, node, profile_manager: GamepadProfileManager):
    """Handle the 'check_gamepad_profile' Dora input event.

    Checks if a profile exists for the given gamepad ID or vendor/product IDs.
    Emits the result (existence status, profile name) via the
    'gamepad_profile_status' output.

    Args:
        event: The Dora input event dictionary. Expected value contains a
               dictionary with 'gamepad_id' and optionally 'vendorId' and
               'productId'.
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    request_data = event.get('value')
    if not request_data:
        print("No request data provided in event")
        return
    
    # Extract the first element if it's a list
    if isinstance(request_data, list) and len(request_data) > 0:
        request_data = request_data[0]
    
    # Get the gamepad ID
    gamepad_id = request_data.get('gamepad_id')
    vendor_id = request_data.get('vendorId')
    product_id = request_data.get('productId')
    
    print(f"DEBUG - check_gamepad_profile: Request data - ID: {gamepad_id}, vendor: {vendor_id}, product: {product_id}")
    
    if not gamepad_id and not (vendor_id and product_id):
        print("No gamepad_id or vendor/product IDs provided in request")
        return
    
    # Check if profile exists by gamepad ID
    profile = None
    
    if gamepad_id:
        profile = profile_manager.get_profile(gamepad_id)
    
    # If not found and vendor/product IDs are provided, try looking up by those
    if not profile and vendor_id and product_id:
        profile = profile_manager.get_profile_by_vendor_product(vendor_id, product_id)
    
    # If we have a gamepad ID but no vendor/product IDs, try to extract them
    if gamepad_id and not profile and not (vendor_id and product_id):
        try:
            import re
            vendor_match = re.search(r'Vendor:\s*([0-9a-fA-F]+)', gamepad_id)
            product_match = re.search(r'Product:\s*([0-9a-fA-F]+)', gamepad_id)
            
            if vendor_match and product_match:
                extracted_vendor = vendor_match.group(1).strip()
                extracted_product = product_match.group(1).strip()
                print(f"DEBUG - check_gamepad_profile: Extracted vendor: {extracted_vendor}, product: {extracted_product}")
                
                profile = profile_manager.get_profile_by_vendor_product(extracted_vendor, extracted_product)
        except Exception as e:
            print(f"DEBUG - check_gamepad_profile: Error extracting vendor/product: {e}")
    
    # Emit the result
    response = {
        'gamepad_id': gamepad_id,
        'exists': profile is not None,
        'profile_name': profile.get('name', '') if profile else '',
        'vendorId': profile.get('vendorId', '') if profile else vendor_id,
        'productId': profile.get('productId', '') if profile else product_id
    }
    
    try:
        if hasattr(node, 'send_output'):
            node.send_output('gamepad_profile_status', pa.array([response]))
            print(f"DEBUG - check_gamepad_profile: Sent profile status via send_output")
        else:
            node.emit('gamepad_profile_status', pa.array([response]))
            print(f"DEBUG - check_gamepad_profile: Sent profile status via emit")
    except Exception as e:
        print(f"DEBUG - check_gamepad_profile: Error sending profile status: {e}")
        import traceback
        traceback.print_exc()


def handle_delete_gamepad_profile(event: Dict, node, profile_manager: GamepadProfileManager):
    """Handle the 'delete_gamepad_profile' Dora input event.

    Extracts the gamepad ID, deletes the corresponding profile using the
    profile manager, and emits an updated list of profiles.

    Args:
        event: The Dora input event dictionary. Expected value contains a
               dictionary with a 'gamepad_id' key.
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    request_data = event.get('value')
    if not request_data:
        print("No request data provided in event")
        return
    
    # Extract the first element if it's a list
    if isinstance(request_data, list) and len(request_data) > 0:
        request_data = request_data[0]
    
    # Get the gamepad ID
    gamepad_id = request_data.get('gamepad_id')
    if not gamepad_id:
        print("No gamepad_id provided in request")
        return
    
    # Delete the profile
    success = profile_manager.delete_profile(gamepad_id)
    
    # Emit the updated list of profiles
    if success:
        emit_profiles_list(node, profile_manager)


def handle_list_gamepad_profiles(event: Dict, node, profile_manager: GamepadProfileManager):
    """Handle the 'list_gamepad_profiles' Dora input event.

    Retrieves the current list of profiles from the manager and emits it.

    Args:
        event: The Dora input event dictionary (value is usually ignored).
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    emit_profiles_list(node, profile_manager)


def emit_profiles_list(node, profile_manager: GamepadProfileManager):
    """Emit the current list of available gamepad profiles.

    Retrieves the profiles from the manager and sends them as a PyArrow
    array containing a single dictionary (mapping IDs to profiles) via the
    'gamepad_profiles_list' output.

    Args:
        node: The Dora node instance.
        profile_manager: The GamepadProfileManager instance.
    """
    profiles = profile_manager.list_profiles()
    print(f"DEBUG - emit_profiles_list: Got profiles from manager: {profiles}")
    print(f"DEBUG - emit_profiles_list: About to emit full gamepad_profiles_list")
    
    try:
        # Send the full profiles through Dora - no need to simplify
        if hasattr(node, 'send_output'):
            node.send_output('gamepad_profiles_list', pa.array([profiles]))
            print(f"DEBUG - emit_profiles_list: Successfully sent full profiles list using send_output")
        else:
            # Fallback to emit if available
            node.emit('gamepad_profiles_list', pa.array([profiles]))
            print(f"DEBUG - emit_profiles_list: Successfully emitted full profiles list using emit")
    except Exception as e:
        print(f"DEBUG - emit_profiles_list: Error emitting profiles: {e}")
        import traceback
        traceback.print_exc()

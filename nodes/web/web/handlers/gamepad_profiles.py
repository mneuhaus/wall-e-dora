"""
Module for handling gamepad profile management.

Provides storage, retrieval, and management of gamepad control mappings.
"""

import os
import json
import pyarrow as pa
from pathlib import Path
from typing import Dict, Any, Optional, List

class GamepadProfileManager:
    """Manages gamepad profiles with persistence to JSON files."""
    
    def __init__(self, profiles_dir: str = None):
        """
        Initialize the profile manager.
        
        Args:
            profiles_dir: Directory to store profile files. If None, uses ~/.wall-e-dora/gamepad_profiles/
        """
        if profiles_dir is None:
            # Use default location in user's home directory
            home_dir = os.path.expanduser("~")
            profiles_dir = os.path.join(home_dir, ".wall-e-dora", "gamepad_profiles")
            
        self.profiles_dir = Path(profiles_dir)
        # Create directory if it doesn't exist
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Cache of loaded profiles
        self.profiles = {}
        
        # Load all existing profiles
        self.load_all_profiles()
    
    def load_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all existing profiles from disk.
        
        Returns:
            Dict mapping gamepad IDs to profile data
        """
        self.profiles = {}
        
        # Find all JSON files in the profiles directory
        json_files = list(self.profiles_dir.glob("*.json"))
        
        for file_path in json_files:
            try:
                with open(file_path, 'r') as f:
                    profile = json.load(f)
                    
                if 'id' in profile:
                    # Use the gamepad ID as the key
                    self.profiles[profile['id']] = profile
            except Exception as e:
                print(f"Error loading profile from {file_path}: {e}")
        
        print(f"Loaded {len(self.profiles)} gamepad profiles")
        return self.profiles
    
    def save_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Save a gamepad profile.
        
        Args:
            profile: Profile data with 'id', 'name', and 'mapping' keys
            
        Returns:
            Success or failure
        """
        if not profile or 'id' not in profile:
            print("Cannot save profile: missing required 'id' field")
            return False
        
        gamepad_id = profile['id']
        
        # Generate a safe filename from the gamepad ID
        safe_name = "".join(c if c.isalnum() else "_" for c in gamepad_id)
        file_path = self.profiles_dir / f"{safe_name}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(profile, f, indent=2)
            
            # Update the cache
            self.profiles[gamepad_id] = profile
            print(f"Saved gamepad profile for '{gamepad_id}' to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def get_profile(self, gamepad_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a gamepad profile by ID.
        
        Args:
            gamepad_id: The unique identifier for the gamepad
            
        Returns:
            The profile data if found, None otherwise
        """
        return self.profiles.get(gamepad_id)
    
    def delete_profile(self, gamepad_id: str) -> bool:
        """
        Delete a gamepad profile.
        
        Args:
            gamepad_id: The unique identifier for the gamepad
            
        Returns:
            Success or failure
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
        """
        List all available profiles.
        
        Returns:
            Dict mapping gamepad IDs to profile data
        """
        return self.profiles


# Handler functions for web node events

def handle_save_gamepad_profile(event, node, profile_manager):
    """Handle save_gamepad_profile events."""
    profile_data = event.get('value')
    
    if not profile_data:
        print("No profile data provided in event")
        return
    
    # Extract the first element if it's a list
    if isinstance(profile_data, list) and len(profile_data) > 0:
        profile_data = profile_data[0]
    
    # Validate profile data
    if not isinstance(profile_data, dict) or 'id' not in profile_data or 'mapping' not in profile_data:
        print("Invalid profile data format")
        return
    
    # Ensure profile has a name
    if 'name' not in profile_data or not profile_data['name']:
        profile_data['name'] = f"Profile for {profile_data['id']}"
    
    # Save the profile
    success = profile_manager.save_profile(profile_data)
    
    # Emit the updated list of profiles
    if success:
        emit_profiles_list(node, profile_manager)


def handle_get_gamepad_profile(event, node, profile_manager):
    """Handle get_gamepad_profile events."""
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


def handle_check_gamepad_profile(event, node, profile_manager):
    """Handle check_gamepad_profile events to check if a profile exists."""
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
    
    # Check if profile exists
    profile = profile_manager.get_profile(gamepad_id)
    
    # Emit the result
    response = {
        'gamepad_id': gamepad_id,
        'exists': profile is not None,
        'profile_name': profile.get('name', '') if profile else ''
    }
    node.emit('gamepad_profile_status', pa.array([response]))


def handle_delete_gamepad_profile(event, node, profile_manager):
    """Handle delete_gamepad_profile events."""
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


def handle_list_gamepad_profiles(event, node, profile_manager):
    """Handle list_gamepad_profiles events."""
    emit_profiles_list(node, profile_manager)


def emit_profiles_list(node, profile_manager):
    """Emit the list of available profiles."""
    profiles = profile_manager.list_profiles()
    
    # Convert to a simple format for the client
    simplified_profiles = {}
    for gamepad_id, profile in profiles.items():
        simplified_profiles[gamepad_id] = {
            'name': profile.get('name', ''),
            'controls_mapped': len(profile.get('mapping', {}))
        }
    
    node.emit('gamepad_profiles_list', pa.array([simplified_profiles]))
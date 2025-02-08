# Audio System

## Overview
The audio system provides Wall-E's voice and sound effects capabilities through a ROS2 node. It manages playback of pre-recorded sounds including startup sequences, voice clips, and background music.

## Hardware Setup
- **Audio Output**: I2S audio via CM4's built-in audio interface
- **Speaker**: 3W 4Ω speaker with amplifier
- **Sound Files**: Pre-recorded MP3s stored in package resources

## Available Sounds
| Filename            | Description                    | Duration |
|--------------------|--------------------------------|----------|
| startup.mp3        | Boot sequence sound            | 2.1s     |
| wall-e-1.mp3       | Main "Wall-E" voice clip       | 1.2s     |
| wall-e-2.mp3       | Curious "Wall-E" voice         | 1.0s     |
| wall-e-3.mp3       | Happy "Wall-E" voice           | 1.1s     |
| wall-e-4.mp3       | Questioning "Wall-E" voice     | 1.3s     |
| gorgeus.mp3        | "Gorgeous" admiration          | 1.0s     |
| whoa.mp3           | "Whoa" surprise sound          | 0.8s     |
| eva.mp3            | "Eva!" excited call            | 0.9s     |
| directive.mp3      | "Directive?" question          | 1.2s     |
| background-music.mp3| Ambient background music       | 60.0s    |
| destruct.mp3       | Destruction sound effect       | 1.5s     |

## ROS2 Interface

### Node: audio_node
- **Package**: audio
- **Executable**: audio_node

### Parameters
| Parameter      | Type    | Default | Description              |
|---------------|---------|---------|--------------------------|
| startup_sound | bool    | true    | Play sound on node start |
| volume        | float   | 1.0     | Master volume (0.0-1.0)  |

### Web Interface Integration
The audio node is integrated with the web interface, providing:
- Quick access buttons for all sound effects
- Visual feedback on sound playback
- Grouped sounds by type (voices, effects, etc)

### Topics
| Topic         | Type              | Direction | Description        |
|---------------|-------------------|-----------|-------------------|
| /play_sound   | std_msgs/String   | Sub      | Play sound by name |
| /stop_sound   | std_msgs/Empty    | Sub      | Stop playback     |

### Usage Examples
```bash
# Play startup sound
ros2 topic pub /play_sound std_msgs/String "data: 'startup.mp3'"

# Play background music
ros2 topic pub /play_sound std_msgs/String "data: 'background-music.mp3'"

# Play Wall-E voice
ros2 topic pub /play_sound std_msgs/String "data: 'wall-e-1.mp3'"

# Stop current playback
ros2 topic pub /stop_sound std_msgs/Empty
```

## Dependencies
- ROS2 Humble
- pygame (audio playback)
- ALSA audio system

## Configuration
The node requires proper ALSA configuration for the I2S audio interface. Ensure the following in `/etc/asound.conf`:

```
pcm.!default {
    type hw
    card 0
}

ctl.!default {
    type hw
    card 0
}
```
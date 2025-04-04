"""Main orchestration module for the Eyes Node.

Initializes the Dora node and handles incoming events for controlling
the Wall-E eye displays, including periodic file synchronization and
on-demand image display requests.
"""

from dora import Node
import pyarrow as pa

# Use direct imports (not relative or absolute that depend on package structure)
from eyes.inputs.tick import process_tick
from eyes.inputs.list_images import process_list_images
from eyes.inputs.play_gif import process_play_gif
from eyes.outputs.images import broadcast_available_images


def main():
    """Main function for the Eyes Node.

    Initializes the Dora node, sets up the context, broadcasts the initial
    list of available images, and enters the main event loop to process
    tick, list_images, and play_gif events.
    """
    # Create the Node
    node = Node()
    
    # Initialize context with dependencies
    context = {
        "node": node
    }
    
    print("Eyes node started - will sync GIF images to eye displays every 5 minutes")
    
    # Broadcast available images at startup
    broadcast_available_images(context)
    
    # Main event loop
    for event in node:
        if event["type"] == "INPUT":
            # Route events based on ID
            if event["id"] == "TICK":
                process_tick(context, event)
            
            # Handle list_images event
            elif event["id"] == "list_images":
                process_list_images(context, event)
                
            # Handle play_gif event from web node
            elif event["id"] == "play_gif":
                process_play_gif(context, event)


if __name__ == "__main__":
    main()

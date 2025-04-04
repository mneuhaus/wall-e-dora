"""Input handler for the 'list_images' event."""
from eyes.outputs.images import broadcast_available_images


def process_list_images(context: dict, event: dict):
    """Process the 'list_images' input event.

    This handler simply triggers the `broadcast_available_images` function
    to scan the directory and send the current list of images.

    Args:
        context: The node context dictionary.
        event: The Dora input event dictionary.
    """
    print("Received list_images event, broadcasting available images")
    broadcast_available_images(context, event)
    return None

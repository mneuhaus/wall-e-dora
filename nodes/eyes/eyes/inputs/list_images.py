"""Input handler for listing images."""
from eyes.outputs.images import broadcast_available_images


def process_list_images(context, event):
    """
    Process a list_images event to broadcast available images.
    
    Args:
        context (dict): The context dictionary containing dependencies.
        event (dict): The event data.
        
    Returns:
        None
    """
    print("Received list_images event, broadcasting available images")
    broadcast_available_images(context, event)
    return None
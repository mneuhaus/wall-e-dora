"""Output handler for broadcasting available eye images."""

import os
import glob
from pathlib import Path
import pyarrow as pa


def broadcast_available_images(context: dict, event: dict = None):
    """Scan the gif_sync directory and broadcast the list of available images.

    Finds all GIF and JPG/JPEG files in the `nodes/eyes/gif_sync` directory,
    collects metadata (filename, paths, size, type, timestamp), sorts them,
    and sends the list as a PyArrow array via the 'available_images' output.

    Args:
        context: The node context dictionary containing the Dora node instance.
        event: The triggering Dora event (optional, currently unused).
    """
    # Get the path to the gif_sync directory
    current_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    gif_sync_dir = current_dir / "gif_sync"
    
    if not gif_sync_dir.exists():
        print(f"Warning: GIF sync directory not found at {gif_sync_dir}")
        # Send empty list if directory doesn't exist
        context["node"].send_output(
            output_id="available_images", 
            data=pa.array([]), 
            metadata={"count": 0}
        )
        return
    
    # Get all GIF files with their paths
    image_files = []
    for ext in ['*.gif', '*.jpg', '*.jpeg', '*.GIF', '*.JPG', '*.JPEG']:
        for file_path in glob.glob(os.path.join(gif_sync_dir, ext)):
            # Get the paths formatted for frontend and server
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Provide additional helpful info for displaying
            is_gif = filename.lower().endswith('.gif')
            
            image_files.append({
                "filename": filename,
                "path": f"/eyes/gif/{filename}",  # Frontend path format
                "source_path": str(file_path),  # Original location for direct reading
                "size": file_size,
                "is_gif": is_gif,
                "timestamp": os.path.getmtime(file_path)
            })
    
    # Sort by filename
    image_files.sort(key=lambda x: x["filename"])
    
    # Convert to Arrow array
    image_data = pa.array(image_files)
    
    print(f"Broadcasting {len(image_files)} available images")
    
    # Send the list of images
    context["node"].send_output(
        output_id="available_images", 
        data=image_data, 
        metadata={"count": len(image_files)}
    )

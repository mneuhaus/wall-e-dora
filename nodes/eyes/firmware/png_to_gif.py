#!/usr/bin/env python3
import os
import sys
import argparse
import math
from PIL import Image, ImageDraw

def create_circular_mask(size, radius=None):
    """Create a circular mask image with anti-aliasing."""
    width, height = size
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    
    # If radius is None, use the smallest distance from center to edge
    if radius is None:
        radius = min(width, height) // 2
    
    # Draw a filled circle with anti-aliasing
    draw.ellipse((width//2 - radius, height//2 - radius, 
                   width//2 + radius, height//2 + radius), 
                  fill=255)
    
    return mask

def convert_png_to_gif(input_dir, output_dir, circular=False):
    """
    Convert all PNG files in input_dir to 240x240 single-frame GIF files in output_dir.
    If circular=True, apply a circular mask to emulate border-radius.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Get list of PNG files
    png_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png')]
    
    if not png_files:
        print("No PNG files found in the input directory.")
        return
    
    print(f"Found {len(png_files)} PNG files to convert")
    
    for filename in png_files:
        input_path = os.path.join(input_dir, filename)
        
        # Change extension from .png to .gif
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}.gif"
        preview_filename = f"{base_name}_preview.gif"
        output_path = os.path.join(output_dir, output_filename)
        preview_path = os.path.join(output_dir, preview_filename)
        
        try:
            # Open the PNG image
            with Image.open(input_path) as img:
                # Get dimensions
                width, height = img.size
                
                # Center crop to square if not already square
                if width != height:
                    # Calculate the square size and crop coordinates
                    size = min(width, height)
                    left = (width - size) // 2
                    top = (height - size) // 2
                    right = left + size
                    bottom = top + size
                    
                    # Crop the image
                    img = img.crop((left, top, right, bottom))
                
                # Resize to 240x240 using Lanczos resampling (high quality)
                img = img.resize((240, 240), Image.LANCZOS)
                
                # Convert to RGB mode if in RGBA to ensure compatibility
                if img.mode == 'RGBA':
                    # Create a black background
                    background = Image.new('RGB', img.size, (0, 0, 0))
                    # Paste the image on the background using alpha as mask
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save standard GIF
                img.save(output_path, 'GIF')
                print(f"Converted: {input_path} -> {output_path}")
                
                # # Create circular preview version
                # preview_img = img.copy()
                # if circular:
                #     # Create circular mask
                #     mask = create_circular_mask(preview_img.size, radius=120)
                    
                #     # Create a blank black background
                #     background = Image.new('RGB', preview_img.size, (0, 0, 0))
                    
                #     # Apply the mask to the image
                #     background.paste(preview_img, (0, 0), mask)
                #     preview_img = background
                
                # # Save preview version
                # preview_img.save(preview_path, 'GIF')
                # print(f"Created preview: {preview_path}")
                
        except Exception as e:
            print(f"Error processing {input_path}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert PNG files to 240x240 single-frame GIF files"
    )
    parser.add_argument("input_dir", help="Directory containing PNG files")
    parser.add_argument("output_dir", help="Directory where GIF files will be saved")
    parser.add_argument("--circular", action="store_true", 
                       help="Apply circular mask to preview images")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory {args.input_dir} does not exist or is not a directory.")
        sys.exit(1)
    
    convert_png_to_gif(args.input_dir, args.output_dir, circular=args.circular)

if __name__ == "__main__":
    main()
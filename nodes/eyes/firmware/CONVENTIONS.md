# GIF Optimization

Before uploading GIFs to the device, optimize them using the provided script:

```bash
python3 optimize_gif.py input_directory output_directory
```

This will:
1. Process all GIF files in the input directory
2. Scale each GIF to cover 240x240 pixels while maintaining aspect ratio
3. Center-crop the scaled GIF to exactly 240x240 pixels
4. Optimize each GIF using gifsicle
5. Save the results to the output directory:
   - Optimized file with "_o" suffix
   - Preview file with "_preview" suffix (contains only first frame)

Requirements:
- Python 3 with Pillow package installed
- gifsicle in your system PATH

Example:
```bash
python3 optimize_gif.py path/to/input_gifs path/to/output_gifs
```

Optional arguments:
- `--rotate <degrees>`: Generate additional rotated versions of each GIF
  - Creates `_left+<angle>.gif` (positive rotation)
  - Creates `_right-<angle>.gif` (negative rotation)
  Example: `python3 optimize_gif.py input/ output/ --rotate 90`

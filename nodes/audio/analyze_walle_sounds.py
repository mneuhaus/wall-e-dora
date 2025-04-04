"""Script to analyze Wall-E audio files using OpenAI's GPT-4o.

This script processes MP3 files in a specified directory, transcribes them
using Whisper, and then uses GPT-4o to suggest a descriptive filename
based on the emotional content and sound type perceived in the audio.
It can optionally rename the files based on the suggestions.

Requires OpenAI API key (set via --api_key or OPENAI_API_KEY env var)
and the `openai` and `pydub` Python packages.
"""

import os
import argparse
import json
from openai import OpenAI
from pydub import AudioSegment

def analyze_audio_with_gpt4o(file_path, client):
    """
    Analyze audio using GPT-4o through OpenAI API
    """
    try:
        with open(file_path, "rb") as audio_file:
            # Create a transcription with GPT-4o
            transcript_response = client.audio.transcriptions.create(
                model="whisper-1",  # Use Whisper for initial transcription
                file=audio_file,
                response_format="verbose_json",
                language="en"
            )
            
            # Get the transcription text
            transcription = transcript_response.text
            
            # Now use GPT-4o to interpret the audio content, especially for robotic sounds
            if transcription:
                # If we have some transcription, ask GPT-4o to analyze it
                completion = client.chat.completions.create(
                    model="gpt-4o",  # Use GPT-4o for better understanding of robot sounds
                    messages=[
                        {"role": "system", "content": (
                            "Du bist ein Klangemotion-Interpret für Wall-E Robotergeräusche. Für jede Audiodatei "
                            "analysierst du die emotionale Qualität, Stimmung oder das Gefühl, das der Klang vermittelt. "
                            "Erstelle dann einen prägnanten, ausdrucksstarken Dateinamen, der diese emotionale Essenz einfängt. "
                            "Der Dateiname sollte:\n"
                            "- Die emotionale Qualität oder Stimmung des Klangs erfassen (neugierig, fröhlich, traurig, aufgeregt, usw.)\n"
                            "- Ein beschreibendes Element über die Klangart enthalten (piep, surr, zirp, usw.)\n"
                            "- Prägnant sein (maximal 2-3 Wörter, durch Bindestriche verbunden)\n"
                            "- Nur Kleinbuchstaben, Zahlen (falls nötig), Unterstriche oder Bindestriche verwenden\n"
                            "- Beispiele: 'neugieriges-piepen', 'trauriges-surren', 'aufgeregtes-zirpen', 'fragendes-boop', 'erstauntes-trillern'\n"
                            "- Antworte nur mit dem Dateinamen, keine Erklärungen"
                        )},
                        {"role": "user", "content": f"Dies ist eine Transkription eines Wall-E Audioclips: '{transcription}'. "
                                               f"Erstelle einen deutschen Dateinamen, der sowohl die emotionale Qualität/Stimmung "
                                               f"als auch die Art des Geräusches in diesem Wall-E Clip einfängt."}
                    ]
                )
                
                # Extract the suggested name from GPT-4o
                suggested_name = completion.choices[0].message.content.strip()
                
                # Clean the name for file usage
                suggested_name = suggested_name.replace('"', '').replace("'", "")
                if suggested_name.endswith('.mp3'):
                    suggested_name = suggested_name[:-4]  # Remove .mp3 if GPT added it
                
                # Make sure it's lowercase
                suggested_name = suggested_name.lower()
                    
                # Limit length and clean up
                suggested_name = suggested_name[:100]
                suggested_name = suggested_name.replace(" ", "-")
                suggested_name = ''.join(c for c in suggested_name if c.isalnum() or c in '-_')
                
                return {
                    "transcription": transcription,
                    "suggested_name": suggested_name,
                    "original_file": file_path
                }
            else:
                # If no transcription, generate a random German emotional robot sound name
                import random
                robot_sounds = ["neugieriges-piepen", "froehliches-zirpen", "trauriges-surren", "aufgeregtes-blubbern", 
                               "verwirrtes-trillern", "fragendes-klicken", "ueberraschtes-brummen", "nervoses-summen", 
                               "schlafriges-brummen", "entschlossenes-piepsen"]
                return {
                    "transcription": "No speech detected",
                    "suggested_name": random.choice(robot_sounds),
                    "original_file": file_path
                }
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return {
            "transcription": f"Error: {str(e)}",
            "suggested_name": "error-processing",
            "original_file": file_path
        }

def analyze_audio_files(directory, api_key=None, rename_directly=False):
    """
    Process all MP3 files in the given directory and suggest appropriate names
    """
    # Get API key from environment variable if not provided
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
        
    if not api_key:
        print("ERROR: OpenAI API key is required for GPT-4o analysis.")
        print("Please provide your API key with the --api_key parameter or set the OPENAI_API_KEY environment variable.")
        return
        
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Get all MP3 files in directory and subdirectories
    mp3_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.mp3'):
                mp3_files.append(os.path.join(root, file))
    
    print(f"Found {len(mp3_files)} MP3 files")
    
    # Store results for a report
    results = []
    
    # Keep track of created names to avoid duplicates
    created_filenames = set()
    
    # Analyze each file
    for file_path in mp3_files:
        print(f"Analyzing: {file_path}")
        
        # Analyze with GPT-4o
        result = analyze_audio_with_gpt4o(file_path, client)
        results.append(result)
        
        # Print results
        print(f"  Transcription: {result['transcription']}")
        print(f"  Suggested name: {result['suggested_name']}")
        print(f"  Original file: {result['original_file']}")
        
        # Rename directly if requested
        if rename_directly:
            dir_name = os.path.dirname(file_path)
            extension = os.path.splitext(file_path)[1]
            
            # Handle duplicate filenames
            base_filename = f"{result['suggested_name']}{extension}"
            final_filename = base_filename
            counter = 1
            
            while os.path.exists(os.path.join(dir_name, final_filename)) or final_filename in created_filenames:
                final_filename = f"{result['suggested_name']}_{counter}{extension}"
                counter += 1
                
            created_filenames.add(final_filename)
            new_path = os.path.join(dir_name, final_filename)
            
            print(f"  Renaming to: {final_filename}")
            os.rename(file_path, new_path)
            print("  ✓ File renamed")
            
        print("-" * 50)
    
    # Save results to JSON file
    with open("walle_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    if rename_directly:
        print("\nAnalysis complete! All files have been renamed.")
    else:
        print("\nAnalysis complete! Results saved to walle_analysis_results.json")
        print("\nTo rename files based on suggestions, run:")
        print("python analyze_walle_sounds.py --rename")

def rename_files_from_json():
    """
    Rename files based on the previous analysis results
    """
    try:
        with open("walle_analysis_results.json", "r") as f:
            results = json.load(f)
        
        print(f"Found {len(results)} files to rename")
        
        # Create output directory if it doesn't exist
        out_dir = os.path.join(os.getcwd(), "out")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            print(f"Created output directory: {out_dir}")
        
        # Keep track of filenames to handle duplicates
        created_filenames = set()
        
        for item in results:
            original = item["original_file"]
            suggested = item["suggested_name"]
            
            if os.path.exists(original):
                extension = os.path.splitext(original)[1]
                base_filename = f"{suggested}{extension}"
                
                # Handle duplicate filenames
                final_filename = base_filename
                counter = 1
                while final_filename in created_filenames:
                    final_filename = f"{suggested}_{counter}{extension}"
                    counter += 1
                
                created_filenames.add(final_filename)
                new_path = os.path.join(out_dir, final_filename)
                
                print(f"Copying: {original} -> {new_path}")
                
                # Create a copy in the output directory
                import shutil
                shutil.copy2(original, new_path)
                print("  ✓ File copied with new name (original preserved)")
            else:
                print(f"  ✗ Original file not found: {original}")
        
        print(f"\nRenaming complete! {len(created_filenames)} files copied to {out_dir}")
    except FileNotFoundError:
        print("Error: walle_analysis_results.json not found.")
        print("Run the analysis first with: python analyze_walle_sounds.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Wall-E audio files using GPT-4o")
    parser.add_argument("--directory", default=".", help="Directory containing MP3 files")
    parser.add_argument("--api_key", help="Your OpenAI API key for GPT-4o access")
    parser.add_argument("--rename", action="store_true", help="Rename files based on previous analysis")
    parser.add_argument("--rename_directly", action="store_true", help="Rename files directly during analysis")
    parser.add_argument("--append_mp3", action="store_true", help="Append .mp3 to suggested filenames")
    
    args = parser.parse_args()
    
    if args.rename:
        rename_files_from_json()
    else:
        analyze_audio_files(args.directory, args.api_key, rename_directly=args.rename_directly)

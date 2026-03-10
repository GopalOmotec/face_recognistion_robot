#!/usr/bin/env python3
"""
Utility script to add new faces to the recognition database
"""

import argparse
import os
import sys
from src.face_recognizer import FaceRecognizer

def main():
    parser = argparse.ArgumentParser(description='Add a new face to the recognition database')
    parser.add_argument('image_path', help='Path to the PNG image file')
    parser.add_argument('name', help='Name of the person')
    parser.add_argument('--info', help='Additional information about the person', default='')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.image_path):
        print(f"Error: File {args.image_path} not found")
        sys.exit(1)
    
    # Check if it's a PNG file
    if not args.image_path.lower().endswith('.png'):
        print("Warning: It's recommended to use PNG images for best results")
    
    # Initialize recognizer
    recognizer = FaceRecognizer()
    
    # Add the face
    metadata = {'info': args.info} if args.info else None
    success = recognizer.add_new_face(args.image_path, args.name, metadata)
    
    if success:
        print(f"Successfully added {args.name} to the database")
    else:
        print("Failed to add face. Make sure the image contains a clear face.")
        sys.exit(1)

if __name__ == "__main__":
    main()
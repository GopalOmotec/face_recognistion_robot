import cv2
import os
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

def draw_face_boxes(frame, faces):
    """Draw bounding boxes and labels for detected faces"""
    for face in faces:
        top, right, bottom, left = face['location']
        name = face['name']
        
        # Choose color based on recognition
        if name == "Unknown":
            color = (0, 0, 255)  # Red for unknown
        else:
            color = (0, 255, 0)  # Green for known
        
        # Draw rectangle
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        
        # Draw label text
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
    
    return frame

def save_unknown_face(frame, face, folder_path):
    """Save unknown face image for later review"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    top, right, bottom, left = face['location']
    face_image = frame[top:bottom, left:right]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"unknown_{timestamp}.png"
    filepath = os.path.join(folder_path, filename)
    
    cv2.imwrite(filepath, face_image)
    logger.info(f"Saved unknown face: {filepath}")
    return filepath

def load_known_faces_from_folder(recognizer, folder_path):
    """Load all PNG images from a folder as known faces"""
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return
    
    # Use the class method instead of reimplementing
    recognizer.load_faces_from_folder(folder_path)
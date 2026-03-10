import cv2
import numpy as np
import face_recognition
import pickle
import os
from datetime import datetime
import logging
import re
from config import ENCODINGS_FILE, TOLERANCE, MODEL, NUM_JITTERS, CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_metadata = {}
        self.face_locations = []
        self.face_encodings = []
        self.process_this_frame = True
        self.load_encodings()
        
    def load_encodings(self):
        """Load pre-saved face encodings"""
        if os.path.exists(ENCODINGS_FILE):
            try:
                with open(ENCODINGS_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_names = data['names']
                    self.known_face_metadata = data.get('metadata', {})
                logger.info(f"✓ Loaded {len(self.known_face_names)} known faces: {', '.join(self.known_face_names)}")
            except Exception as e:
                logger.error(f"Error loading encodings: {e}")
                self.known_face_encodings = []
                self.known_face_names = []
                self.known_face_metadata = {}
    
    def save_encodings(self):
        """Save face encodings to file"""
        data = {
            'encodings': self.known_face_encodings,
            'names': self.known_face_names,
            'metadata': self.known_face_metadata,
            'updated': datetime.now().isoformat()
        }
        try:
            with open(ENCODINGS_FILE, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"✓ Encodings saved successfully for {len(self.known_face_names)} faces")
        except Exception as e:
            logger.error(f"Error saving encodings: {e}")
    
    def add_new_face(self, image_path, name, metadata=None):
        """Add a new face to the known faces database"""
        try:
            # Check if face already exists
            if name in self.known_face_names:
                logger.warning(f"Face '{name}' already exists in database")
                return False
            
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Get face encodings with multiple jitters for better accuracy
            face_encodings = face_recognition.face_encodings(image, num_jitters=NUM_JITTERS)
            
            if len(face_encodings) == 0:
                logger.warning(f"✗ No face found in {image_path}")
                return False
            elif len(face_encodings) > 1:
                logger.warning(f"Multiple faces found in {image_path}, using the first one")
            
            # Add to known faces
            self.known_face_encodings.append(face_encodings[0])
            self.known_face_names.append(name)
            
            # Store metadata
            self.known_face_metadata[name] = {
                'first_seen': datetime.now().isoformat(),
                'times_recognized': 0,
                'last_seen': None,
                'image_path': image_path,
                'info': metadata if metadata else {}
            }
            
            # Save updated encodings
            self.save_encodings()
            logger.info(f"✓ Successfully added new face: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding new face: {e}")
            return False
    
    def recognize_faces(self, frame):
        """Recognize faces in a frame with confidence scores"""
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(rgb_small_frame, model=MODEL)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        recognized_faces = []
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Scale back face locations
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2
            
            # Default to Unknown
            name = "Unknown"
            confidence = 0
            metadata = {}
            
            # Check against known faces
            if self.known_face_encodings:
                # Calculate face distances (lower means more similar)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                # Get the best match
                best_match_index = np.argmin(face_distances)
                best_match_distance = face_distances[best_match_index]
                
                # Convert distance to confidence score (1 - distance, but distance can be >1)
                confidence = 1 - min(best_match_distance, 1.0)
                
                # Check if confidence meets threshold
                if confidence >= CONFIDENCE_THRESHOLD:
                    name = self.known_face_names[best_match_index]
                    metadata = self.known_face_metadata.get(name, {})
                    
                    # Update metadata
                    if name in self.known_face_metadata:
                        self.known_face_metadata[name]['times_recognized'] = \
                            self.known_face_metadata[name].get('times_recognized', 0) + 1
                        self.known_face_metadata[name]['last_seen'] = datetime.now().isoformat()
            
            recognized_faces.append({
                'name': name,
                'location': (top, right, bottom, left),
                'confidence': confidence,
                'metadata': metadata,
                'encoding': face_encoding if name == "Unknown" else None
            })
        
        return recognized_faces
    
    def load_faces_from_folder(self, folder_path):
        """Load all PNG faces from a folder"""
        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return 0
        
        # Get list of PNG files
        png_files = [f for f in os.listdir(folder_path) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not png_files:
            logger.warning(f"No image files found in {folder_path}")
            return 0
        
        logger.info(f"Found {len(png_files)} image files in {folder_path}")
        
        loaded_count = 0
        for filename in png_files:
            file_path = os.path.join(folder_path, filename)
            
            # Extract name from filename (remove extension)
            name = os.path.splitext(filename)[0]
            
            # Clean up the name
            clean_name = re.sub(r'[^\w\s]', '', name).strip()
            clean_name = re.sub(r'\s+', ' ', clean_name)  # Replace multiple spaces
            
            if not clean_name:
                logger.warning(f"Skipping file with invalid name: {filename}")
                continue
            
            # Check if already exists
            if clean_name in self.known_face_names:
                logger.info(f"Face '{clean_name}' already exists, skipping...")
                continue
            
            if self.add_new_face(file_path, clean_name):
                loaded_count += 1
        
        logger.info(f"✓ Successfully loaded {loaded_count} new faces")
        return loaded_count
    
    def get_face_stats(self):
        """Get statistics about recognized faces"""
        stats = {
            'total_faces': len(self.known_face_names),
            'faces': [],
            'total_recognitions': 0
        }
        
        for name in self.known_face_names:
            metadata = self.known_face_metadata.get(name, {})
            times_recognized = metadata.get('times_recognized', 0)
            last_seen = metadata.get('last_seen', 'Never')
            
            stats['faces'].append({
                'name': name,
                'times_recognized': times_recognized,
                'last_seen': last_seen
            })
            stats['total_recognitions'] += times_recognized
        
        return stats
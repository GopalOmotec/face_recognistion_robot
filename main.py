#!/usr/bin/env python3

import cv2
import time
import argparse
import logging
from datetime import datetime
import os
import sys
import numpy as np

from config import (CAMERA_ID, FRAME_WIDTH, FRAME_HEIGHT, FRAME_SKIP, 
                   KNOWN_FACES_DIR, UNKNOWN_FACES_DIR, ROBOT_NAME,
                   GREETING_COOLDOWN)
from src.face_recognizer import FaceRecognizer
from src.robot_dialog import RobotDialog
from src.utils import draw_face_boxes, save_unknown_face

logger = logging.getLogger(__name__)

class ProfessionalFaceRobot:
    def __init__(self, camera_id=CAMERA_ID):
        self.camera_id = camera_id
        self.camera = None
        self.running = False
        self.frame_count = 0
        self.last_greeting_time = {}
        self.current_faces = []
        
        # Minimal UI - no chat transcript
        self.robot_thinking = False
        self.last_action = ""  # Show only current action
        
        # Ultra-minimal color palette
        self.colors = {
            'green': (0, 255, 0),
            'orange': (0, 165, 255),
            'blue': (255, 0, 0),
            'red': (0, 0, 255),
            'white': (255, 255, 255),
            'gray': (100, 100, 100),
            'black': (0, 0, 0)
        }
        
        # Initialize components
        logger.info("="*50)
        logger.info("Initializing Face Recognition Robot (MINIMAL UI)")
        logger.info("="*50)
        
        self.recognizer = FaceRecognizer()
        self.robot = RobotDialog(robot_name=ROBOT_NAME)
        
        # Load faces from folder
        self.load_known_faces()
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'frames_processed': 0,
            'faces_detected': 0,
            'recognitions': 0,
            'unknown_faces': 0
        }
        
        # No chat messages stored
        self.last_greeting = ""
        
        # Update robot with initial known faces
        self.robot.update_known_faces(self.recognizer.known_face_names)
    
    def set_indian_female_voice(self):
        """Set Indian Female voice for the robot"""
        voices = self.robot.tts_engine.getProperty('voices')
        
        logger.info("Available voices for Indian Female selection:")
        indian_voice_found = False
        
        # First, try to find an Indian voice
        indian_keywords = ['indian', 'hin', 'hindi', 'rakesh', 'heera', 'lekha', 'vardan', 'dhwani']
        
        for i, voice in enumerate(voices):
            logger.info(f"Voice {i}: ID={voice.id}, Name={voice.name}")
            voice_lower = voice.name.lower() + " " + voice.id.lower()
            
            # Check for Indian voice
            if any(keyword in voice_lower for keyword in indian_keywords):
                self.robot.tts_engine.setProperty('voice', voice.id)
                logger.info(f"✅ Selected Indian voice: {voice.name}")
                indian_voice_found = True
                break
        
        # If no Indian voice, try to find a female voice
        if not indian_voice_found:
            for voice in voices:
                voice_lower = voice.name.lower()
                if 'female' in voice_lower:
                    self.robot.tts_engine.setProperty('voice', voice.id)
                    logger.info(f"✅ Selected female voice as fallback: {voice.name}")
                    indian_voice_found = True
                    break
        
        # If still no voice, use default
        if not indian_voice_found and len(voices) > 0:
            self.robot.tts_engine.setProperty('voice', voices[0].id)
            logger.info(f"✅ Using default voice: {voices[0].name}")
        
        # Set voice parameters
        self.robot.tts_engine.setProperty('rate', 150)
        self.robot.tts_engine.setProperty('volume', 0.9)
        
        # Try to set pitch if available
        try:
            self.robot.tts_engine.setProperty('pitch', 120)
        except:
            pass
    
    def load_known_faces(self):
        """Load known faces from folder"""
        logger.info("\nLoading known faces...")
        count = self.recognizer.load_faces_from_folder(KNOWN_FACES_DIR)
        
        if count > 0:
            logger.info(f"Successfully loaded {count} new faces")
            self.robot.update_known_faces(self.recognizer.known_face_names)
        else:
            logger.info("No new faces to load")
        
        # Show current database stats
        stats = self.recognizer.get_face_stats()
        if stats['total_faces'] > 0:
            logger.info(f"\nCurrent Face Database:")
            logger.info(f"  Total known faces: {stats['total_faces']}")
    
    def start_camera(self):
        """Start the camera with optimal settings"""
        self.camera = cv2.VideoCapture(self.camera_id)
        
        if not self.camera.isOpened():
            logger.error("Could not open camera")
            return False
        
        # Optimize camera settings
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for less lag
        
        logger.info(f"Camera started successfully (ID: {self.camera_id})")
        return True
    
    def stop_camera(self):
        """Stop the camera"""
        if self.camera:
            self.camera.release()
            logger.info("Camera stopped")
    
    def process_frame(self, frame):
        """Process a single frame for face recognition"""
        # Resize for faster processing if frame is large
        if frame.shape[1] > 640:
            scale = 640 / frame.shape[1]
            new_width = int(frame.shape[1] * scale)
            new_height = int(frame.shape[0] * scale)
            process_frame = cv2.resize(frame, (new_width, new_height))
        else:
            process_frame = frame
        
        # Recognize faces
        faces = self.recognizer.recognize_faces(process_frame)
        
        # Scale face coordinates back if we resized
        if frame.shape[1] > 640 and faces:
            scale_factor = frame.shape[1] / new_width
            for face in faces:
                top, right, bottom, left = face['location']
                face['location'] = (
                    int(top * scale_factor),
                    int(right * scale_factor),
                    int(bottom * scale_factor),
                    int(left * scale_factor)
                )
        
        # Update statistics
        self.stats['frames_processed'] += 1
        self.stats['faces_detected'] += len(faces)
        
        for face in faces:
            if face['name'] != "Unknown":
                self.stats['recognitions'] += 1
            else:
                self.stats['unknown_faces'] += 1
        
        return faces
    
    def handle_recognized_faces(self, faces):
        """Handle interactions with recognized faces"""
        current_time = time.time()
        
        for face in faces:
            name = face['name']
            confidence = face['confidence']
            
            # Skip unknown faces
            if name == "Unknown":
                continue
            
            # Check if we should greet this person
            last_greeting = self.last_greeting_time.get(name, 0)
            
            if current_time - last_greeting > GREETING_COOLDOWN:
                logger.info(f"Recognized: {name} ({confidence:.2%})")
                
                # Greet the person
                self.robot.greet_person(name)
                self.last_greeting = f"Hello {name}"
                
                # Update last greeting time
                self.last_greeting_time[name] = current_time
                
                # Ask a follow-up question for high confidence
                if confidence > 0.7:
                    time.sleep(1)
                    self.robot.ask_question()
    
    def add_to_known_faces(self, frame, face, name):
        """Add an unknown face to known faces database"""
        top, right, bottom, left = face['location']
        face_image = frame[top:bottom, left:right]
        
        temp_path = os.path.join(KNOWN_FACES_DIR, f"{name}.png")
        cv2.imwrite(temp_path, face_image)
        
        success = self.recognizer.add_new_face(temp_path, name)
        
        if success:
            self.robot.speak(f"I will remember you as {name}.")
            self.last_greeting = f"Added {name}"
            logger.info(f"Added {name} to known faces")
            self.robot.update_known_faces(self.recognizer.known_face_names)
        else:
            self.robot.speak("Could not add face.")
            self.last_greeting = "Failed to add"
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return success
    
    def draw_minimal_ui(self, frame, faces):
        """Ultra-minimal UI with no chat transcript"""
        h, w = frame.shape[:2]
        
        # Create a copy
        ui_frame = frame.copy()
        
        # Draw face boxes only
        for face in faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face.get('confidence', 0)
            
            # Simple color coding
            if name == "Unknown":
                color = self.colors['orange']
                label = "?"
            else:
                color = self.colors['green']
                label = name
            
            # Draw bounding box (thin for performance)
            cv2.rectangle(ui_frame, (left, top), (right, bottom), color, 1)
            
            # Simple label
            cv2.putText(ui_frame, label, (left, top - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw minimal stats at top
        stats_text = f"Known: {len(self.recognizer.known_face_names)} | Now: {len(faces)}"
        cv2.putText(ui_frame, stats_text, (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['white'], 1)
        
        # Draw last greeting/action at bottom (single line, no chat history)
        if self.last_greeting:
            cv2.putText(ui_frame, self.last_greeting, (10, h - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['green'], 1)
        
        # Draw minimal controls
        controls = "Q:Quit S:Save A:Add T:Talk L:Listen"
        cv2.putText(ui_frame, controls, (10, h - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['gray'], 1)
        
        # Draw thinking indicator (very minimal)
        if self.robot_thinking:
            cv2.putText(ui_frame, "...", (w - 30, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['blue'], 1)
        
        return ui_frame
    
    def run(self):
        """Main application loop - optimized for performance"""
        if not self.start_camera():
            return
        
        self.running = True
        
        logger.info("\n" + "="*50)
        logger.info("Robot is now running (MINIMAL UI - NO CHAT TRANSCRIPT)")
        logger.info("Press 'q' to quit")
        logger.info("="*50 + "\n")
        
        self.robot.speak(f"{self.robot.robot_name} is online.")
        
        # Performance optimization variables
        frame_count = 0
        process_every_n_frames = FRAME_SKIP
        
        try:
            while self.running:
                # Read frame
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to grab frame")
                    break
                
                frame_count += 1
                
                # Process faces less frequently
                if frame_count % process_every_n_frames == 0:
                    faces = self.process_frame(frame)
                    self.current_faces = faces
                    self.handle_recognized_faces(faces)
                
                # Draw minimal UI
                display_frame = self.draw_minimal_ui(frame, self.current_faces if frame_count % process_every_n_frames == 0 else [])
                
                # Display
                cv2.imshow('Robot Assistant', display_frame)
                
                # Handle key presses (non-blocking)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    logger.info("Quit command received")
                    self.robot.speak("Goodbye.")
                    break
                
                elif key == ord('s') and self.current_faces:
                    self.robot_thinking = True
                    self.last_greeting = "Saving face..."
                    for face in self.current_faces:
                        if face['name'] == "Unknown":
                            save_unknown_face(frame, face, UNKNOWN_FACES_DIR)
                            self.robot.speak("Face saved.")
                            self.last_greeting = "Face saved"
                    self.robot_thinking = False
                
                elif key == ord('a') and self.current_faces:
                    unknown_faces = [f for f in self.current_faces if f['name'] == "Unknown"]
                    if unknown_faces:
                        self.robot_thinking = True
                        self.last_greeting = "Listening for name..."
                        self.robot.speak("Your name?")
                        name = self.robot.listen(timeout=5)
                        if name:
                            clean_name = name.strip().title()
                            self.add_to_known_faces(frame, unknown_faces[0], clean_name)
                        self.robot_thinking = False
                
                elif key == ord('t'):
                    self.robot_thinking = True
                    self.last_greeting = "Conversation mode..."
                    if self.current_faces and self.current_faces[0]['name'] != "Unknown":
                        name = self.current_faces[0]['name']
                        self.robot.have_conversation(name=name, turns=1)
                    else:
                        self.robot.have_conversation(turns=1)
                    self.last_greeting = "Conversation ended"
                    self.robot_thinking = False
                
                elif key == ord('l'):
                    self.robot_thinking = True
                    self.last_greeting = "Listening..."
                    self.robot.speak("Listening?")
                    user_input = self.robot.listen(timeout=5)
                    if user_input:
                        self.last_greeting = f"Heard: {user_input[:20]}"
                        self.robot.respond_to_input(user_input)
                    self.robot_thinking = False
                
                elif key == ord('i'):
                    # Show info briefly
                    runtime = datetime.now() - self.stats['start_time']
                    self.last_greeting = f"Runtime: {str(runtime).split('.')[0]}"
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.stop_camera()
        cv2.destroyAllWindows()
        
        # Final stats
        runtime = datetime.now() - self.stats['start_time']
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Faces detected: {self.stats['faces_detected']}")
        logger.info(f"Recognitions: {self.stats['recognitions']}")
        logger.info("Robot shutdown complete")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Face Recognition Robot')
    parser.add_argument('--camera', type=int, default=CAMERA_ID,
                       help='Camera ID to use')
    parser.add_argument('--reset', action='store_true',
                       help='Reset face database')
    
    args = parser.parse_args()
    
    # Reset if requested
    if args.reset and os.path.exists('data/face_encodings.pkl'):
        os.remove('data/face_encodings.pkl')
        logger.info("Face database reset")
    
    # Create and run robot
    robot = ProfessionalFaceRobot(camera_id=args.camera)
    
    try:
        robot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
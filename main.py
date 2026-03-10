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
        
        # Chat interface variables
        self.chat_messages = []
        self.chat_scroll = 0
        self.last_user_input = ""
        self.robot_thinking = False
        self.typing_animation = 0
        
        # Dark theme color palette (professional, no emojis)
        self.colors = {
            'bg_dark': (10, 10, 10),        # Almost black
            'bg_medium': (20, 20, 20),       # Very dark gray
            'bg_light': (30, 30, 30),         # Dark gray
            'accent_blue': (0, 120, 255),     # Professional blue
            'accent_green': (0, 200, 0),      # Success green
            'accent_orange': (255, 140, 0),   # Warning orange
            'accent_red': (255, 50, 50),      # Error red
            'text_primary': (240, 240, 240),  # Off-white
            'text_secondary': (180, 180, 180), # Light gray
            'text_muted': (120, 120, 120),    # Medium gray
            'border': (60, 60, 60),           # Gray border
            'robot_bubble': (0, 80, 160),     # Dark blue
            'user_bubble': (60, 60, 80)       # Dark gray-blue
        }
        
        # Initialize components
        logger.info("="*50)
        logger.info("Initializing Professional Face Recognition Robot")
        logger.info("="*50)
        
        self.recognizer = FaceRecognizer()
        self.robot = RobotDialog(robot_name=ROBOT_NAME)
        
        # Make robot voice softer
        self.make_robot_softer()
        
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
        
        # Add welcome message to chat (no emojis)
        self.add_chat_message("robot", f"Hello, I am {ROBOT_NAME}, your AI assistant. I can recognize faces and chat with you.")
        self.add_chat_message("robot", "Press 't' for conversation or let me recognize your face.")
    
    def make_robot_softer(self):
        """Make robot voice softer and more pleasant"""
        # Get current voice properties
        voices = self.robot.tts_engine.getProperty('voices')
        
        # Set softer voice parameters
        self.robot.tts_engine.setProperty('rate', 150)  # Slower speed
        self.robot.tts_engine.setProperty('volume', 0.8)  # Lower volume
        
        # Try to find a pleasant voice
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                self.robot.tts_engine.setProperty('voice', voice.id)
                logger.info("Set soft female voice")
                break
        
        # Override speak method to remove emojis
        original_speak = self.robot.speak
        
        def soft_speak(text):
            # Remove any emojis that might be in the text
            clean_text = self.remove_emojis(text)
            original_speak(clean_text)
        
        self.robot.speak = soft_speak
    
    def remove_emojis(self, text):
        """Remove emojis from text"""
        # Simple emoji removal - keep only ASCII characters
        return text.encode('ascii', 'ignore').decode('ascii')
    
    def add_chat_message(self, sender, message):
        """Add a message to the chat history"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_messages.append({
            'sender': sender,
            'message': message,
            'timestamp': timestamp,
            'time': time.time()
        })
        
        # Keep only last 20 messages
        if len(self.chat_messages) > 20:
            self.chat_messages = self.chat_messages[-20:]
    
    def load_known_faces(self):
        """Load known faces from folder"""
        logger.info("\nLoading known faces...")
        count = self.recognizer.load_faces_from_folder(KNOWN_FACES_DIR)
        
        if count > 0:
            logger.info(f"Successfully loaded {count} new faces")
            self.add_chat_message("robot", f"I have learned {count} new face{'s' if count > 1 else ''}.")
        else:
            logger.info("No new faces to load")
        
        # Show current database stats
        stats = self.recognizer.get_face_stats()
        if stats['total_faces'] > 0:
            logger.info(f"\nCurrent Face Database:")
            logger.info(f"  Total known faces: {stats['total_faces']}")
            for face in stats['faces']:
                logger.info(f"  • {face['name']}: recognized {face['times_recognized']} times")
    
    def start_camera(self):
        """Start the camera with optimal settings"""
        self.camera = cv2.VideoCapture(self.camera_id)
        
        if not self.camera.isOpened():
            logger.error("Could not open camera")
            return False
        
        # Set camera properties for better performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info(f"Camera started successfully (ID: {self.camera_id})")
        self.add_chat_message("robot", "Camera is online. Monitoring for faces...")
        return True
    
    def stop_camera(self):
        """Stop the camera"""
        if self.camera:
            self.camera.release()
            logger.info("Camera stopped")
    
    def process_frame(self, frame):
        """Process a single frame for face recognition"""
        # Recognize faces
        faces = self.recognizer.recognize_faces(frame)
        
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
                logger.info(f"Recognized: {name} (confidence: {confidence:.2%})")
                
                # Professional greeting (no emojis)
                greeting = f"Welcome back, {name}. It is good to see you again."
                self.robot.speak(greeting)
                self.add_chat_message("robot", f"Welcome back, {name} (confidence: {confidence:.1%})")
                
                # Update last greeting time
                self.last_greeting_time[name] = current_time
                
                # Ask a follow-up question for high confidence
                if confidence > 0.7:  # High confidence
                    time.sleep(1)
                    question = self.robot.ask_question()
                    self.add_chat_message("robot", question)
    
    def add_to_known_faces(self, frame, face, name):
        """Add an unknown face to known faces database"""
        # Extract face region
        top, right, bottom, left = face['location']
        face_image = frame[top:bottom, left:right]
        
        # Save temporarily
        temp_path = os.path.join(KNOWN_FACES_DIR, f"{name}.png")
        cv2.imwrite(temp_path, face_image)
        
        # Add to recognizer
        success = self.recognizer.add_new_face(temp_path, name)
        
        if success:
            self.robot.speak(f"Thank you. I will remember you as {name}.")
            self.add_chat_message("robot", f"Nice to meet you, {name}. I have added your face to my database.")
            logger.info(f"Added {name} to known faces")
        else:
            self.robot.speak("I apologize, I could not add your face. Please try again.")
            self.add_chat_message("robot", "I could not add your face. Please try again.")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return success
    
    def draw_dark_ui(self, frame, faces):
        """Draw dark theme UI with chat interface (no emojis)"""
        h, w = frame.shape[:2]
        
        # Create a copy for the UI
        ui_frame = frame.copy()
        
        # Create right panel for chat (30% of width)
        panel_width = int(w * 0.3)
        chat_x = w - panel_width
        
        # Draw dark chat panel
        overlay = ui_frame.copy()
        cv2.rectangle(overlay, (chat_x, 0), (w, h), self.colors['bg_dark'], -1)
        cv2.addWeighted(overlay, 0.95, ui_frame, 0.05, 0, ui_frame)
        
        # Draw panel border
        cv2.line(ui_frame, (chat_x, 0), (chat_x, h), self.colors['border'], 1)
        
        # Draw chat header
        header_y = 40
        cv2.putText(ui_frame, "CHAT", (chat_x + 20, header_y), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.7, self.colors['accent_blue'], 1)
        
        # Draw separator line
        cv2.line(ui_frame, (chat_x + 10, header_y + 10), (w - 10, header_y + 10), 
                self.colors['border'], 1)
        
        # Draw chat messages
        message_y = header_y + 40
        visible_messages = 10  # Number of messages visible at once
        
        start_idx = max(0, len(self.chat_messages) - visible_messages - self.chat_scroll)
        end_idx = len(self.chat_messages) - self.chat_scroll
        
        for i, msg in enumerate(self.chat_messages[start_idx:end_idx]):
            sender = msg['sender']
            message = msg['message']
            timestamp = msg['timestamp']
            
            # Calculate bubble dimensions
            bubble_x = chat_x + 15
            max_width = panel_width - 40
            font_scale = 0.45
            
            # Split message into lines
            words = message.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                (text_width, _) = cv2.getTextSize(test_line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
                
                if text_width <= max_width - 20:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Calculate bubble height
            line_height = 20
            bubble_height = len(lines) * line_height + 20
            
            # Draw bubble background
            bubble_color = self.colors['robot_bubble'] if sender == 'robot' else self.colors['user_bubble']
            
            # Draw message bubble (simple rectangle, no rounded corners)
            cv2.rectangle(ui_frame, 
                         (bubble_x, message_y - 5), 
                         (bubble_x + max_width, message_y + bubble_height - 5), 
                         bubble_color, -1)
            
            # Draw bubble border
            cv2.rectangle(ui_frame, 
                         (bubble_x, message_y - 5), 
                         (bubble_x + max_width, message_y + bubble_height - 5), 
                         self.colors['border'], 1)
            
            # Draw timestamp
            cv2.putText(ui_frame, timestamp, 
                       (bubble_x + max_width - 70, message_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['text_muted'], 1)
            
            # Draw sender label
            sender_label = "ROBOT" if sender == 'robot' else "USER"
            cv2.putText(ui_frame, sender_label, (bubble_x + 5, message_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['text_secondary'], 1)
            
            # Draw message lines
            line_y = message_y + 15
            for line in lines:
                cv2.putText(ui_frame, line, (bubble_x + 10, line_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.colors['text_primary'], 1)
                line_y += line_height
            
            message_y += bubble_height + 10
        
        # Draw typing indicator if robot is thinking
        if self.robot_thinking:
            self.typing_animation = (self.typing_animation + 1) % 60
            dots = "." * (self.typing_animation // 20 + 1)
            typing_text = f"Robot is typing{dots}"
            
            cv2.putText(ui_frame, typing_text, (chat_x + 20, h - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text_secondary'], 1)
        
        # Draw camera feed label
        cv2.putText(ui_frame, "CAMERA FEED", (20, 30), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.6, self.colors['accent_blue'], 1)
        
        # Draw face boxes with clean styling
        for face in faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face.get('confidence', 0)
            
            # Choose color based on recognition
            if name == "Unknown":
                color = self.colors['accent_orange']
                label = f"Unknown ({confidence:.1%})" if confidence > 0 else "Unknown"
            else:
                color = self.colors['accent_green']
                label = f"{name} ({confidence:.1%})"
            
            # Draw bounding box
            cv2.rectangle(ui_frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            label_bg = ui_frame.copy()
            cv2.rectangle(label_bg, (left, top - 25), (right, top), color, -1)
            cv2.addWeighted(label_bg, 0.8, ui_frame, 0.2, 0, ui_frame)
            
            # Draw label text
            cv2.putText(ui_frame, label, (left + 5, top - 7), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text_primary'], 1)
        
        # Draw statistics in top left (clean, no emojis)
        stats_y = 70
        stat_items = [
            f"Known: {len(self.recognizer.known_face_names)}",
            f"Detected: {len(faces)}",
            f"Frames: {self.stats['frames_processed']}"
        ]
        
        for stat in stat_items:
            cv2.putText(ui_frame, stat, (20, stats_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text_secondary'], 1)
            stats_y += 25
        
        # Draw instructions at bottom
        inst_y = h - 30
        instructions = [
            ("Q", "Quit", self.colors['accent_red']),
            ("S", "Save", self.colors['accent_orange']),
            ("A", "Add", self.colors['accent_green']),
            ("T", "Talk", self.colors['accent_blue']),
            ("L", "Listen", self.colors['text_secondary'])
        ]
        
        x_offset = 20
        for key, action, color in instructions:
            # Draw key button
            cv2.rectangle(ui_frame, (x_offset - 5, inst_y - 15), 
                         (x_offset + 20, inst_y + 5), color, 1)
            cv2.putText(ui_frame, key, (x_offset, inst_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Draw action text
            cv2.putText(ui_frame, action, (x_offset + 30, inst_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['text_secondary'], 1)
            
            x_offset += 100
        
        return ui_frame
    
    def run(self):
        """Main application loop"""
        if not self.start_camera():
            return
        
        self.running = True
        
        # Initial greeting
        logger.info("\n" + "="*50)
        logger.info("Robot is now running with dark theme")
        logger.info("Press 'q' to quit, 's' to save unknown face, 'a' to add new face")
        logger.info("="*50 + "\n")
        
        self.robot.speak(f"{self.robot.robot_name} is now online and ready to assist.")
        
        try:
            while self.running:
                # Read frame
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to grab frame")
                    break
                
                # Process every FRAME_SKIP frames
                self.frame_count += 1
                if self.frame_count % FRAME_SKIP == 0:
                    # Recognize faces
                    faces = self.process_frame(frame)
                    self.current_faces = faces
                    
                    # Handle recognized faces
                    self.handle_recognized_faces(faces)
                
                # Draw dark UI
                display_frame = self.draw_dark_ui(frame, self.current_faces if self.frame_count % FRAME_SKIP == 0 else [])
                
                # Display frame
                cv2.imshow('AI Robot Assistant - Dark Theme', display_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    logger.info("Quit command received")
                    self.add_chat_message("robot", "Goodbye. It was nice chatting with you.")
                    self.robot.speak("Goodbye. It was nice chatting with you.")
                    time.sleep(2)
                    break
                
                elif key == ord('s') and self.current_faces:
                    # Save unknown faces
                    self.robot_thinking = True
                    for face in self.current_faces:
                        if face['name'] == "Unknown":
                            path = save_unknown_face(frame, face, UNKNOWN_FACES_DIR)
                            self.robot.speak("Unknown face saved for review.")
                            self.add_chat_message("robot", "Unknown face saved for review.")
                            logger.info(f"Saved unknown face to {path}")
                    self.robot_thinking = False
                
                elif key == ord('a') and self.current_faces:
                    # Add new face to known faces
                    unknown_faces = [f for f in self.current_faces if f['name'] == "Unknown"]
                    
                    if unknown_faces:
                        self.robot_thinking = True
                        self.robot.speak("Please say the name of this person.")
                        self.add_chat_message("robot", "Please say your name. I am listening.")
                        time.sleep(1)
                        
                        # Listen for name
                        name = self.robot.listen(timeout=5)
                        
                        if name:
                            # Clean up the name
                            clean_name = name.strip().title()
                            self.add_to_known_faces(frame, unknown_faces[0], clean_name)
                        else:
                            self.robot.speak("I did not catch the name. Please try again.")
                            self.add_chat_message("robot", "I did not hear the name. Please try again later.")
                        self.robot_thinking = False
                    else:
                        self.add_chat_message("robot", "No unknown faces detected.")
                
                elif key == ord('t'):
                    # Conversation mode
                    self.robot_thinking = True
                    self.add_chat_message("robot", "Starting conversation...")
                    
                    if self.current_faces and self.current_faces[0]['name'] != "Unknown":
                        name = self.current_faces[0]['name']
                        conversation = self.robot.have_professional_conversation(name=name, turns=2)
                    else:
                        conversation = self.robot.have_professional_conversation(turns=2)
                    
                    # Add conversation to chat
                    for speaker, text in conversation:
                        if speaker == "robot":
                            self.add_chat_message("robot", text)
                    
                    self.robot_thinking = False
                
                elif key == ord('l'):
                    # Listen mode
                    self.robot_thinking = True
                    self.robot.speak("I am listening. What would you like to say?")
                    self.add_chat_message("robot", "Listening...")
                    
                    user_input = self.robot.listen(timeout=5)
                    
                    if user_input:
                        self.add_chat_message("user", user_input)
                        response = self.robot.respond_to_input(user_input)
                        self.add_chat_message("robot", response)
                    else:
                        self.add_chat_message("robot", "No input detected.")
                    
                    self.robot_thinking = False
                
                elif key == ord('i'):
                    # Show info
                    self.display_info()
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()
    
    def display_info(self):
        """Display system information in chat"""
        info_messages = []
        
        # Runtime
        runtime = datetime.now() - self.stats['start_time']
        info_messages.append(f"Runtime: {str(runtime).split('.')[0]}")
        
        # Face database stats
        stats = self.recognizer.get_face_stats()
        info_messages.append(f"Known faces: {stats['total_faces']}")
        info_messages.append(f"Total recognitions: {stats['total_recognitions']}")
        
        # Session stats
        info_messages.append(f"Session: {self.stats['recognitions']} recognitions, {self.stats['unknown_faces']} unknown")
        
        # Add to chat
        for msg in info_messages:
            self.add_chat_message("robot", msg)
            time.sleep(0.5)
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.stop_camera()
        cv2.destroyAllWindows()
        
        # Final statistics
        self.display_info()
        self.add_chat_message("robot", "Robot shutting down.")
        
        logger.info("\n" + "="*50)
        logger.info("Robot shutdown complete")
        logger.info("="*50)

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
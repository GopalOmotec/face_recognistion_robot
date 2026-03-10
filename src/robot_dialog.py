import pyttsx3
import speech_recognition as sr
import threading
import queue
import time
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RobotDialog:
    def __init__(self, robot_name="ROBOT"):
        self.robot_name = robot_name
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.listening = False
        self.conversation_history = []
        self.known_faces_list = []  # Will be updated from main app
        self.last_greeting_time = {}  # Track last greeting time per person
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.set_female_voice()  # Force female voice
        
        # Initialize speech recognition
        self.setup_speech_recognition()
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()
        
        # Dialog templates
        self.init_dialog_templates()
    
    def set_female_voice(self):
        """Force female voice selection"""
        voices = self.tts_engine.getProperty('voices')
        
        logger.info("="*50)
        logger.info("SELECTING FEMALE VOICE")
        logger.info("="*50)
        
        female_voice_found = False
        
        # List all available voices
        for i, voice in enumerate(voices):
            logger.info(f"Voice {i}: {voice.name} - ID: {voice.id}")
        
        # PRIORITY 1: Look for explicit female voices (Zira is Microsoft's female voice)
        for voice in voices:
            voice_lower = voice.name.lower()
            if 'zira' in voice_lower or 'female' in voice_lower:
                self.tts_engine.setProperty('voice', voice.id)
                logger.info(f"✅ SELECTED FEMALE VOICE: {voice.name}")
                female_voice_found = True
                break
        
        # PRIORITY 2: Look for any voice that might be female (contains 'female' in description)
        if not female_voice_found:
            for voice in voices:
                voice_lower = voice.name.lower()
                if 'female' in voice_lower:
                    self.tts_engine.setProperty('voice', voice.id)
                    logger.info(f"✅ SELECTED FEMALE VOICE: {voice.name}")
                    female_voice_found = True
                    break
        
        # PRIORITY 3: If on Windows, try to specifically get Microsoft Zira
        if not female_voice_found:
            for voice in voices:
                if 'microsoft' in voice.name.lower() and 'english' in voice.name.lower():
                    # Usually the second voice is female (David is male, Zira is female)
                    if 'david' not in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        logger.info(f"✅ SELECTED VOICE: {voice.name}")
                        female_voice_found = True
                        break
        
        # Last resort: use the second voice if available (often female on Windows)
        if not female_voice_found and len(voices) > 1:
            self.tts_engine.setProperty('voice', voices[1].id)
            logger.info(f"✅ USING SECOND AVAILABLE VOICE: {voices[1].name}")
        
        # Set voice parameters for clear, pleasant tone
        self.tts_engine.setProperty('rate', 160)  # Moderate speed
        self.tts_engine.setProperty('volume', 0.9)  # Clear volume
        
        logger.info("="*50)
    
    def update_known_faces(self, face_list):
        """Update the list of known faces from main app"""
        self.known_faces_list = face_list
        logger.info(f"Updated known faces list: {face_list}")
    
    def setup_speech_recognition(self):
        """Setup speech recognition with better parameters"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        with self.microphone as source:
            logger.info("Calibrating microphone for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            self.recognizer.energy_threshold = 3000
            self.recognizer.dynamic_energy_threshold = True
    
    def init_dialog_templates(self):
        """Initialize professional dialog templates"""
        
        # Time-based greetings
        self.time_greetings = {
            'morning': "Good morning",
            'afternoon': "Good afternoon",
            'evening': "Good evening",
            'night': "Good evening"
        }
        
        # Professional questions
        self.professional_questions = [
            "How is your day going?",
            "What work are you doing currently?",
            "Is there anything I can help you with?",
            "Would you like to check any updates?",
            "How can I make your work easier?",
            "What would you like to discuss?",
            "Do you need any information?",
            "Would you like me to show you any features?",
            "What tasks are you focusing on today?",
            "How can I assist you with your work?",
            "Whom can you recognize?"  # New question added
        ]
        
        # Responses
        self.responses = {
            'greeting': [
                "Hello! How may I help you?",
                "Hello! Nice to meet you.",
                "Greetings! How can I assist you?"
            ],
            'status': [
                "I am doing well, thank you for asking.",
                "All systems are working properly.",
                "I am functioning well, thank you."
            ],
            'capabilities': [
                f"I can recognize faces and have conversations. My name is {self.robot_name}.",
                "I can identify people and help you with information.",
                "I am designed for face recognition and professional interaction."
            ],
            'thanks': [
                "You are welcome!",
                "Happy to help you!",
                "My pleasure!"
            ],
            'farewell': [
                "Goodbye! Have a nice day.",
                "See you later! Take care.",
                "Bye bye! Come back soon."
            ],
            'unknown': [
                "I see. Please tell me more.",
                "Okay. What else would you like to discuss?",
                "I understand. Please continue.",
                "Thank you for sharing that."
            ],
            'name_response': [
                "Nice to meet you, Mr. {name}. How can I assist you today?",
                "Pleasure to meet you, {name}. How may I help you?",
                "Welcome Mr. {name}. What can I do for you today?"
            ],
            'recognize_response': [
                "I can recognize {count} people: {names}",
                "The people I know are: {names}",
                "I can recognize {names}"
            ]
        }
    
    def get_time_greeting(self):
        """Get greeting based on current time"""
        current_hour = datetime.now().hour
        
        if current_hour < 12:
            return self.time_greetings['morning']
        elif current_hour < 17:
            return self.time_greetings['afternoon']
        elif current_hour < 21:
            return self.time_greetings['evening']
        else:
            return self.time_greetings['night']
    
    def _process_speech_queue(self):
        """Process speech queue in background"""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                self.speaking = True
                logger.info(f"🤖 Robot says: {text}")
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.speaking = False
                self.conversation_history.append(("robot", text, datetime.now().isoformat()))
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech error: {e}")
                self.speaking = False
    
    def speak(self, text):
        """Add text to speech queue"""
        self.speech_queue.put(text)
    
    def greet_person(self, name):
        """
        Greet a person with time-based greeting
        Only says the greeting once per session
        """
        current_time = time.time()
        
        # Check if we've greeted this person recently (within last 30 seconds)
        last_greeting = self.last_greeting_time.get(name, 0)
        if current_time - last_greeting < 30:
            return None  # Skip greeting if said recently
        
        time_greeting = self.get_time_greeting()
        
        # Create the greeting
        full_greeting = f"{time_greeting} {name}, Nice to meet you Mr. {name}, How can I assist you today?"
        
        self.speak(full_greeting)
        
        # Update last greeting time
        self.last_greeting_time[name] = current_time
        
        # Log and store in history
        logger.info(f"Greeted {name} with: {full_greeting}")
        self.conversation_history.append(("robot", full_greeting, datetime.now().isoformat()))
        
        return full_greeting
    
    def ask_question(self):
        """Ask a professional question"""
        question = random.choice(self.professional_questions)
        
        # Special handling for the recognize question
        if "whom can you recognize" in question.lower():
            return self.ask_recognize_question()
        
        self.speak(question)
        return question
    
    def ask_recognize_question(self):
        """Ask about recognizable faces and list them"""
        if self.known_faces_list:
            # Format the list of names
            if len(self.known_faces_list) == 1:
                names_str = self.known_faces_list[0]
                response = f"I can recognize one person: {names_str}"
            else:
                # Join names with commas and 'and' for the last one
                if len(self.known_faces_list) > 1:
                    names_str = ", ".join(self.known_faces_list[:-1]) + " and " + self.known_faces_list[-1]
                else:
                    names_str = self.known_faces_list[0]
                
                response = f"I can recognize {len(self.known_faces_list)} people: {names_str}"
        else:
            response = "I don't know anyone yet. You can add faces by pressing 'A' and telling me your name."
        
        self.speak(response)
        self.conversation_history.append(("robot", response, datetime.now().isoformat()))
        return response
    
    def respond_to_input(self, user_input, person_name=None):
        """Generate intelligent response based on user input"""
        if not user_input:
            return None
        
        user_input_lower = user_input.lower()
        
        # Check for keywords and generate appropriate responses
        if any(word in user_input_lower for word in ['hello', 'hi', 'hey']):
            response = random.choice(self.responses['greeting'])
        
        elif any(word in user_input_lower for word in ['how are you', 'how do you do']):
            response = random.choice(self.responses['status'])
        
        elif any(word in user_input_lower for word in ['what can you do', 'capabilities', 'features', 'help']):
            response = random.choice(self.responses['capabilities'])
        
        elif any(word in user_input_lower for word in ['thank', 'thanks']):
            response = random.choice(self.responses['thanks'])
        
        elif any(word in user_input_lower for word in ['bye', 'goodbye', 'see you']):
            response = random.choice(self.responses['farewell'])
        
        elif any(word in user_input_lower for word in ['your name', 'who are you']):
            response = f"My name is {self.robot_name}. I am your friendly assistant robot."
        
        elif any(word in user_input_lower for word in ['weather']):
            response = "I don't have access to weather information. You can check a weather app for that."
        
        elif any(word in user_input_lower for word in ['time']):
            current_time = datetime.now().strftime("%I:%M %p")
            response = f"The current time is {current_time}."
        
        elif any(word in user_input_lower for word in ['recognize', 'who do you know', 'whom can you recognize', 'what names']):
            # Handle recognize question
            if self.known_faces_list:
                if len(self.known_faces_list) == 1:
                    response = f"I can recognize {self.known_faces_list[0]}"
                else:
                    names_str = ", ".join(self.known_faces_list[:-1]) + " and " + self.known_faces_list[-1]
                    response = f"I can recognize {len(self.known_faces_list)} people: {names_str}"
            else:
                response = "I don't know anyone yet. You can add faces by pressing 'A' and telling me your name."
        
        elif any(word in user_input_lower for word in ['name', 'my name is', 'i am']):
            # Extract name from user input
            import re
            name_match = re.search(r'(?:name is|i am|call me|i\'m)\s+([a-zA-Z\s]+)', user_input_lower)
            if name_match:
                extracted_name = name_match.group(1).strip().title()
                response = f"Nice to meet you, Mr. {extracted_name}. How can I assist you today?"
            elif person_name:
                response = f"Nice to meet you, Mr. {person_name}. How can I assist you today?"
            else:
                response = "Please tell me your name so I can remember you."
        
        else:
            response = random.choice(self.responses['unknown'])
        
        self.speak(response)
        return response
    
    def listen(self, timeout=5):
        """Listen for user input with better error handling"""
        self.listening = True
        try:
            with self.microphone as source:
                logger.info("🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            logger.info(f"👤 User said: {text}")
            self.conversation_history.append(("user", text, datetime.now().isoformat()))
            self.listening = False
            return text
            
        except sr.WaitTimeoutError:
            logger.debug("Listening timeout")
            self.listening = False
            return None
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            self.listening = False
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            self.listening = False
            return None
        except Exception as e:
            logger.error(f"Listening error: {e}")
            self.listening = False
            return None
    
    def have_conversation(self, name=None, turns=2):
        """Have a natural conversation"""
        conversation = []
        
        # Start with greeting if name provided (but check cooldown)
        if name:
            greeting = self.greet_person(name)
            if greeting:  # Only add if greeting was actually said
                conversation.append(("robot", greeting))
                time.sleep(1)
        
        for i in range(turns):
            # Ask a question
            question = self.ask_question()
            conversation.append(("robot", question))
            
            # Wait for response
            time.sleep(1.5)
            response = self.listen(timeout=4)
            
            if response:
                conversation.append(("user", response))
                # Generate response
                robot_response = self.respond_to_input(response, name)
                conversation.append(("robot", robot_response))
                time.sleep(1)
            else:
                self.speak("I didn't catch that. Shall we continue?")
                break
        
        return conversation
    
    def get_conversation_summary(self):
        """Get summary of conversation history"""
        summary = {
            'total_exchanges': len(self.conversation_history),
            'robot_messages': sum(1 for msg in self.conversation_history if msg[0] == 'robot'),
            'user_messages': sum(1 for msg in self.conversation_history if msg[0] == 'user'),
            'recent': self.conversation_history[-5:] if self.conversation_history else []
        }
        return summary
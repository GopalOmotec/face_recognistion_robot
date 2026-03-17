# src/robot_dialog.py

import pyttsx3
import speech_recognition as sr
import threading
import queue
import time
import random
import logging
from datetime import datetime
import re
import os
import sys
from gtts import gTTS
import playsound
import tempfile

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logger = logging.getLogger(__name__)

class RobotDialog:
    def __init__(self, robot_name="ROBOT"):
        self.robot_name = robot_name
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.listening = False
        self.conversation_history = []
        self.known_faces_list = []
        self.last_greeting_time = {}
        
        # Language settings
        self.current_language = 'en'
        self.hindi_mode_active = False
        self.hindi_intro_given = False
        
        # Use gTTS for better Hindi voice
        self.use_gtts = True
        
        # Initialize pyttsx3 for English fallback
        self.tts_engine = None
        try:
            self.tts_engine = pyttsx3.init()
            self.set_english_voice()
        except:
            logger.warning("pyttsx3 initialization failed, using gTTS only")
        
        # Initialize speech recognition
        self.setup_speech_recognition()
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()
        
        # Dialog templates
        self.init_dialog_templates()
    
    def set_english_voice(self):
        """Set English voice for pyttsx3"""
        try:
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            self.tts_engine.setProperty('rate', 160)
            self.tts_engine.setProperty('volume', 0.9)
        except:
            pass
    
    def speak_with_gtts(self, text, lang='hi'):
        """Use Google TTS for better Hindi pronunciation"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_filename = fp.name
            
            # Generate speech
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(temp_filename)
            
            # Play the audio
            playsound.playsound(temp_filename)
            
            # Clean up
            try:
                os.unlink(temp_filename)
            except:
                pass
            return True
        except Exception as e:
            logger.error(f"gTTS error: {e}")
            return False
    
    def safe_log(self, message):
        """Safely log messages without Unicode errors"""
        try:
            # Convert to string if needed
            if not isinstance(message, str):
                message = str(message)
            # Remove non-ASCII characters for logging
            ascii_message = message.encode('ascii', errors='ignore').decode('ascii')
            logger.info(ascii_message)
        except:
            logger.info("[Message logged]")
    
    def detect_language(self, text):
        """Detect if text is Hindi or English"""
        if not text:
            return 'en'
        
        # Hindi Unicode range
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        
        # Count Hindi characters
        hindi_chars = len(hindi_pattern.findall(text))
        total_chars = len(text.strip())
        
        if total_chars > 0 and (hindi_chars / total_chars) > 0.1:
            return 'hi'
        
        # Check for common Hindi words in Roman script
        hindi_words = ['namaste', 'kaise', 'ho', 'kya', 'hai', 'main', 'tum', 'aap', 
                      'hum', 'nahi', 'mere', 'tera', 'mera', 'acha', 'theek', 'thik',
                      'kaisa', 'kahan', 'kyon', 'kab', 'kaun', 'hindi', 'bolo']
        
        words = text.lower().split()
        for word in words:
            if word in hindi_words:
                return 'hi'
        
        return 'en'
    
    def update_known_faces(self, face_list):
        """Update the list of known faces from main app"""
        self.known_faces_list = face_list
        self.safe_log(f"Updated known faces list: {face_list}")
    
    def setup_speech_recognition(self):
        """Setup speech recognition"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        with self.microphone as source:
            self.safe_log("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self.recognizer.energy_threshold = 3000
            self.recognizer.dynamic_energy_threshold = True
    
    def init_dialog_templates(self):
        """Initialize dialog templates with proper Hindi strings"""
        
        # Hindi time greetings
        self.time_greetings_hi = {
            'morning': "सुप्रभात",
            'afternoon': "नमस्ते",
            'evening': "शुभ संध्या",
            'night': "शुभ रात्रि"
        }
        
        # English time greetings
        self.time_greetings = {
            'morning': "Good morning",
            'afternoon': "Good afternoon",
            'evening': "Good evening",
            'night': "Good evening"
        }
        
        # Hindi questions
        self.professional_questions_hi = [
            "आपका दिन कैसा चल रहा है?",
            "आप अभी क्या काम कर रहे हैं?",
            "क्या मैं आपकी कोई मदद कर सकता हूँ?",
            "क्या आप कोई अपडेट देखना चाहेंगे?",
            "मैं आपका काम कैसे आसान बना सकता हूँ?",
            "आप क्या चर्चा करना चाहेंगे?",
            "क्या आपको कोई जानकारी चाहिए?",
            "आज आप किन कार्यों पर ध्यान दे रहे हैं?",
            "मैं किन लोगों को पहचान सकता हूँ?"
        ]
        
        # English questions
        self.professional_questions = [
            "How is your day going?",
            "What work are you doing currently?",
            "Is there anything I can help you with?",
            "Would you like to check any updates?",
            "How can I make your work easier?",
            "What would you like to discuss?",
            "Do you need any information?",
            "What tasks are you focusing on today?",
            "Whom can I recognize?"
        ]
        
        # Hindi responses
        self.responses_hi = {
            'greeting': [
                "नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?",
                "नमस्ते! आपसे मिलकर अच्छा लगा।"
            ],
            'status': [
                "मैं ठीक हूँ, पूछने के लिए धन्यवाद।",
                "सभी प्रणालियाँ सही से काम कर रही हैं।"
            ],
            'capabilities': [
                f"मैं चेहरे पहचान सकता हूँ और बातचीत कर सकता हूँ। मेरा नाम {self.robot_name} है।",
                "मैं लोगों को पहचान सकता हूँ और जानकारी में मदद कर सकता हूँ।"
            ],
            'thanks': [
                "आपका स्वागत है!",
                "आपकी मदद करके खुशी हुई!"
            ],
            'farewell': [
                "नमस्ते! आपका दिन शुभ हो।",
                "फिर मिलेंगे! अपना ख्याल रखें।"
            ],
            'unknown': [
                "समझ गया। कृपया और बताएं।",
                "ठीक है। आप और क्या चर्चा करना चाहेंगे?"
            ],
            'name_response': [
                "आपसे मिलकर अच्छा लगा, {name}। मैं आपकी कैसे सहायता कर सकता हूँ?"
            ],
            'hindi_intro': [
                "मैं हिंदी में भी बात कर सकता हूँ। कृपया हिंदी में बोलें।",
                "जी हां, मैं हिंदी में भी बात कर सकता हूँ। कृपया बोलिए।"
            ]
        }
        
        # English responses
        self.responses_en = {
            'greeting': [
                "Hello! How may I help you?",
                "Hello! Nice to meet you."
            ],
            'status': [
                "I am doing well, thank you for asking.",
                "All systems are working properly."
            ],
            'capabilities': [
                f"I can recognize faces and have conversations. My name is {self.robot_name}.",
                "I can identify people and help you with information."
            ],
            'thanks': [
                "You are welcome!",
                "Happy to help you!"
            ],
            'farewell': [
                "Goodbye! Have a nice day.",
                "See you later! Take care."
            ],
            'unknown': [
                "I see. Please tell me more.",
                "Okay. What else would you like to discuss?"
            ],
            'name_response': [
                "Nice to meet you, {name}. How can I assist you today?"
            ]
        }
    
    def get_time_greeting(self):
        """Get greeting based on current time"""
        current_hour = datetime.now().hour
        
        if current_hour < 12:
            time_period = 'morning'
        elif current_hour < 17:
            time_period = 'afternoon'
        elif current_hour < 21:
            time_period = 'evening'
        else:
            time_period = 'night'
        
        if self.current_language == 'hi':
            return self.time_greetings_hi[time_period]
        return self.time_greetings[time_period]
    
    def _process_speech_queue(self):
        """Process speech queue"""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                self.speaking = True
                
                # Log safely
                self.safe_log(f"Robot says: {text}")
                
                # Speak based on language
                if self.current_language == 'hi' and self.use_gtts:
                    # Use gTTS for Hindi
                    self.speak_with_gtts(text, 'hi')
                else:
                    # Try pyttsx3 first for English
                    if self.tts_engine:
                        try:
                            self.tts_engine.say(text)
                            self.tts_engine.runAndWait()
                        except:
                            # Fallback to gTTS
                            self.speak_with_gtts(text, 'en')
                    else:
                        # Fallback to gTTS
                        self.speak_with_gtts(text, 'en' if self.current_language == 'en' else 'hi')
                
                self.speaking = False
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.safe_log(f"Speech error: {str(e)}")
                self.speaking = False
    
    def speak(self, text):
        """Add text to speech queue"""
        if text and len(text.strip()) > 0:
            self.speech_queue.put(text)
    
    def greet_person(self, name):
        """Greet a person"""
        current_time = time.time()
        
        last_greeting = self.last_greeting_time.get(name, 0)
        if current_time - last_greeting < 30:
            return None
        
        time_greeting = self.get_time_greeting()
        
        if self.current_language == 'hi':
            full_greeting = f"{time_greeting} {name}, आपसे मिलकर अच्छा लगा। मैं आपकी कैसे सहायता कर सकता हूँ?"
        else:
            full_greeting = f"{time_greeting} {name}, nice to meet you. How can I assist you today?"
        
        self.speak(full_greeting)
        self.last_greeting_time[name] = current_time
        return full_greeting
    
    def ask_question(self):
        """Ask a question"""
        if self.current_language == 'hi':
            question = random.choice(self.professional_questions_hi)
        else:
            question = random.choice(self.professional_questions)
        
        self.speak(question)
        return question
    
    def ask_recognize_question(self):
        """Ask about recognizable faces"""
        if self.known_faces_list:
            if self.current_language == 'hi':
                if len(self.known_faces_list) == 1:
                    response = f"मैं एक व्यक्ति को पहचान सकता हूँ: {self.known_faces_list[0]}"
                else:
                    names_str = ", ".join(self.known_faces_list[:-1]) + " और " + self.known_faces_list[-1]
                    response = f"मैं {len(self.known_faces_list)} लोगों को पहचान सकता हूँ: {names_str}"
            else:
                if len(self.known_faces_list) == 1:
                    response = f"I can recognize one person: {self.known_faces_list[0]}"
                else:
                    names_str = ", ".join(self.known_faces_list[:-1]) + " and " + self.known_faces_list[-1]
                    response = f"I can recognize {len(self.known_faces_list)} people: {names_str}"
        else:
            if self.current_language == 'hi':
                response = "मैं अभी किसी को नहीं जानता। आप 'A' दबाकर और अपना नाम बताकर चेहरे जोड़ सकते हैं।"
            else:
                response = "I don't know anyone yet. You can add faces by pressing 'A' and telling me your name."
        
        self.speak(response)
        return response
    
    def respond_to_input(self, user_input, person_name=None):
        """Generate response based on user input"""
        if not user_input:
            return None
        
        user_input_lower = user_input.lower()
        
        if self.current_language == 'hi':
            # Hindi responses
            if any(word in user_input_lower for word in ['नमस्ते', 'hello', 'hi']):
                response = random.choice(self.responses_hi['greeting'])
            elif any(word in user_input_lower for word in ['कैसे', 'how are']):
                response = random.choice(self.responses_hi['status'])
            elif any(word in user_input_lower for word in ['क्या कर', 'what can', 'मदद']):
                response = random.choice(self.responses_hi['capabilities'])
            elif any(word in user_input_lower for word in ['धन्यवाद', 'शुक्रिया', 'thank']):
                response = random.choice(self.responses_hi['thanks'])
            elif any(word in user_input_lower for word in ['अलविदा', 'bye', 'goodbye']):
                response = random.choice(self.responses_hi['farewell'])
            elif any(word in user_input_lower for word in ['नाम', 'name']):
                if person_name:
                    response = self.responses_hi['name_response'][0].format(name=person_name)
                else:
                    response = "कृपया मुझे अपना नाम बताएं।"
            elif any(word in user_input_lower for word in ['पहचान', 'recognize']):
                return self.ask_recognize_question()
            else:
                response = random.choice(self.responses_hi['unknown'])
        else:
            # English responses
            if any(word in user_input_lower for word in ['hello', 'hi', 'hey']):
                response = random.choice(self.responses_en['greeting'])
            elif any(word in user_input_lower for word in ['how are', 'how do']):
                response = random.choice(self.responses_en['status'])
            elif any(word in user_input_lower for word in ['what can', 'capabilities', 'help']):
                response = random.choice(self.responses_en['capabilities'])
            elif any(word in user_input_lower for word in ['thank', 'thanks']):
                response = random.choice(self.responses_en['thanks'])
            elif any(word in user_input_lower for word in ['bye', 'goodbye']):
                response = random.choice(self.responses_en['farewell'])
            elif any(word in user_input_lower for word in ['name']):
                if person_name:
                    response = self.responses_en['name_response'][0].format(name=person_name)
                else:
                    response = "Please tell me your name."
            elif any(word in user_input_lower for word in ['recognize']):
                return self.ask_recognize_question()
            else:
                response = random.choice(self.responses_en['unknown'])
        
        self.speak(response)
        return response
    
    def listen(self, timeout=5):
        """Listen for user input"""
        self.listening = True
        try:
            with self.microphone as source:
                self.safe_log("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
            
            # Try Hindi first
            text = None
            try:
                text = self.recognizer.recognize_google(audio, language='hi-IN')
                self.safe_log(f"User said (Hindi): {text}")
                self.current_language = 'hi'
            except:
                try:
                    text = self.recognizer.recognize_google(audio, language='en-IN')
                    self.safe_log(f"User said (English): {text}")
                    self.current_language = 'en'
                except:
                    pass
            
            self.listening = False
            return text
            
        except sr.WaitTimeoutError:
            self.listening = False
            return None
        except Exception as e:
            self.safe_log(f"Listening error: {str(e)}")
            self.listening = False
            return None
    
    def have_conversation(self, name=None, turns=2):
        """Have a natural conversation"""
        conversation = []
        
        if name:
            greeting = self.greet_person(name)
            if greeting:
                conversation.append(("robot", greeting))
                time.sleep(1)
        
        for i in range(turns):
            question = self.ask_question()
            conversation.append(("robot", question))
            
            time.sleep(1)
            response = self.listen(timeout=4)
            
            if response:
                conversation.append(("user", response))
                
                # Check for Hindi and switch if needed
                detected_lang = self.detect_language(response)
                if detected_lang == 'hi' and self.current_language == 'en' and not self.hindi_intro_given:
                    self.current_language = 'hi'
                    self.hindi_intro_given = True
                    intro = random.choice(self.responses_hi['hindi_intro'])
                    self.speak(intro)
                    conversation.append(("robot", intro))
                    time.sleep(1)
                
                robot_response = self.respond_to_input(response, name)
                conversation.append(("robot", robot_response))
                time.sleep(1)
            else:
                break
        
        return conversation
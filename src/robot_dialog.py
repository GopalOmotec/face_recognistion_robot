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
    def __init__(self, robot_name="ProfRobot"):
        self.robot_name = robot_name
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.listening = False
        self.conversation_history = []
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.set_voice_properties()
        
        # Initialize speech recognition
        self.setup_speech_recognition()
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()
        
        # Professional dialog templates
        self.init_dialog_templates()
    
    def set_voice_properties(self):
        """Set voice properties for professional tone"""
        self.tts_engine.setProperty('rate', 160)  # Slightly faster for professional
        self.tts_engine.setProperty('volume', 0.95)
        
        # Try to set a professional voice
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
    
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
        self.greetings = {
            'morning': [
                f"Good morning! I'm {self.robot_name}. How can I assist you today?",
                f"Good morning! {self.robot_name} at your service.",
            ],
            'afternoon': [
                f"Good afternoon! {self.robot_name} ready to help.",
                f"Good afternoon! How may I be of assistance?",
            ],
            'evening': [
                f"Good evening! I'm {self.robot_name}. What can I do for you?",
                f"Good evening! Ready to assist with your needs.",
            ],
            'default': [
                f"Hello! I'm {self.robot_name}. Nice to see you!",
                f"Greetings! {self.robot_name} online and ready.",
            ]
        }
        
        self.professional_questions = [
            "How is your day progressing?",
            "What project are you working on currently?",
            "Is there anything I can help you with today?",
            "Would you like to check the latest updates?",
            "How can I make your work more efficient?",
            "What would you like to discuss?",
            "Do you need any information or assistance?",
            "Would you like me to demonstrate any features?",
            "What tasks are you focusing on today?",
            "How can I contribute to your productivity?"
        ]
        
        self.responses = {
            'greeting': [
                "Hello! It's a pleasure to interact with you.",
                "Greetings! How may I help?",
                "Nice to hear from you!"
            ],
            'status': [
                "All systems are functioning optimally.",
                "I'm operating at peak efficiency.",
                "Everything is running smoothly, thank you."
            ],
            'capabilities': [
                f"I can recognize faces, engage in conversation, and assist with various tasks. My name is {self.robot_name}.",
                "I'm designed for face recognition and professional interaction.",
                "I can identify individuals and maintain conversation."
            ],
            'thanks': [
                "You're most welcome!",
                "Happy to be of service!",
                "My pleasure to assist!"
            ],
            'farewell': [
                "Goodbye! It was nice interacting with you.",
                "Until next time! Have a productive day.",
                "Farewell! I'm always here when you need me."
            ],
            'unknown': [
                "I understand. Please continue.",
                "Interesting. Tell me more.",
                "I see. What else would you like to discuss?",
                "Thank you for sharing that."
            ]
        }
    
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
    
    def greet(self, name=None):
        """Greet a person professionally"""
        current_hour = datetime.now().hour
        
        if current_hour < 12:
            greeting_type = 'morning'
        elif current_hour < 17:
            greeting_type = 'afternoon'
        elif current_hour < 21:
            greeting_type = 'evening'
        else:
            greeting_type = 'default'
        
        if name and name != "Unknown":
            greeting = f"Welcome {name}! {random.choice(self.greetings[greeting_type])}"
        else:
            greeting = random.choice(self.greetings[greeting_type])
        
        self.speak(greeting)
        return greeting
    
    def ask_question(self):
        """Ask a professional question"""
        question = random.choice(self.professional_questions)
        self.speak(question)
        return question
    
    def respond_to_input(self, user_input):
        """Generate intelligent response based on user input"""
        if not user_input:
            return None
        
        user_input_lower = user_input.lower()
        
        # Check for keywords and generate appropriate responses
        if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            response = random.choice(self.responses['greeting'])
        elif any(word in user_input_lower for word in ['how are you', 'how do you do', 'status']):
            response = random.choice(self.responses['status'])
        elif any(word in user_input_lower for word in ['what can you do', 'capabilities', 'features', 'help']):
            response = random.choice(self.responses['capabilities'])
        elif any(word in user_input_lower for word in ['thank', 'thanks', 'appreciate']):
            response = random.choice(self.responses['thanks'])
        elif any(word in user_input_lower for word in ['bye', 'goodbye', 'see you', 'farewell']):
            response = random.choice(self.responses['farewell'])
        elif any(word in user_input_lower for word in ['your name', 'who are you']):
            response = f"My name is {self.robot_name}. I'm your professional assistant robot."
        elif any(word in user_input_lower for word in ['weather', 'temperature']):
            response = "I don't have access to real-time weather data. You might want to check a weather service."
        elif any(word in user_input_lower for word in ['time', 'clock']):
            current_time = datetime.now().strftime("%I:%M %p")
            response = f"The current time is {current_time}."
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
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
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
    
    def have_professional_conversation(self, name=None, turns=3):
        """Have a professional conversation"""
        conversation = []
        
        # Start with greeting
        if name:
            greeting = self.greet(name)
            conversation.append(("robot", greeting))
            time.sleep(1)
        
        for i in range(turns):
            # Ask a question
            question = self.ask_question()
            conversation.append(("robot", question))
            
            # Wait for response
            time.sleep(2)
            response = self.listen(timeout=5)
            
            if response:
                conversation.append(("user", response))
                # Generate response
                robot_response = self.respond_to_input(response)
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
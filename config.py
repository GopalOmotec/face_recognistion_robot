import os
import logging

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWN_FACES_DIR = os.path.join(BASE_DIR, 'known_faces')
UNKNOWN_FACES_DIR = os.path.join(BASE_DIR, 'unknown_faces')
DATA_DIR = os.path.join(BASE_DIR, 'data')
ENCODINGS_FILE = os.path.join(DATA_DIR, 'face_encodings.pkl')
LOG_FILE = os.path.join(BASE_DIR, 'robot.log')

# Create directories if they don't exist
for dir_path in [KNOWN_FACES_DIR, UNKNOWN_FACES_DIR, DATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Camera settings
CAMERA_ID = 0  # Default camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_SKIP = 15  # Process every 15th frame for performance

# Recognition settings
TOLERANCE = 0.5  # Lower is stricter (0.4-0.5 is good for accuracy)
MODEL = 'hog'  # 'hog' is faster, 'cnn' is more accurate but slower
NUM_JITTERS = 10  # Number of times to re-sample faces for encoding

# Robot settings
ROBOT_NAME = "Robot"
WAKE_WORD = "robot"
GREETING_COOLDOWN = 10  # Seconds between greetings for same person
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for recognition

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
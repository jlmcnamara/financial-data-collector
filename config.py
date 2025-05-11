import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
COMPANIES_DIR = os.path.join(DATA_DIR, 'companies')

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, COMPANIES_DIR]:
    os.makedirs(directory, exist_ok=True)

# API keys and credentials - never include default values
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set. Document summarization will not work.")

# SEC API settings
SEC_USER_AGENT = os.getenv('SEC_USER_AGENT')
if not SEC_USER_AGENT:
    print("WARNING: SEC_USER_AGENT not set. SEC API requests may fail.")
    
SEC_API_RATE_LIMIT = 0.1  # 10 requests per second

# File paths
FORTUNE_100_CSV = os.path.join(COMPANIES_DIR, 'fortune100.csv')

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))

# Scheduler settings
SCHEDULER_DAILY_TIME = os.getenv('SCHEDULER_DAILY_TIME', '02:00')  # 2 AM daily run

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Email Configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Network Device Configuration
DEVICE_CONFIG = {
    'R1': {
        'device_type': 'cisco_ios',
        'host': os.getenv('R1_HOST'),
        'username': os.getenv('R1_USERNAME'),
        'password': os.getenv('R1_PASSWORD'),
    },
    'R2': {
        'device_type': 'cisco_ios',
        'host': os.getenv('R2_HOST'),
        'username': os.getenv('R2_USERNAME'),
        'password': os.getenv('R2_PASSWORD'),
    }
    # Add other devices as needed
} 
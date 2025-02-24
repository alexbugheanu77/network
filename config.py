import os
from dotenv import load_dotenv
import sys

load_dotenv(override=True)

# Debug prints
print("Environment variables loaded:")
print(f"R1_HOST: {os.getenv('R1_HOST')}")
print(f"R1_USERNAME: {os.getenv('R1_USERNAME')}")
print(f"R1_PASSWORD: {os.getenv('R1_PASSWORD')}")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Email Configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Get environment variables with default values
R1_HOST = os.getenv('R1_HOST')
R1_USERNAME = os.getenv('R1_USERNAME')
R1_PASSWORD = os.getenv('R1_PASSWORD')
R1_DEVICE_TYPE = os.getenv('R1_DEVICE_TYPE', 'cisco_ios')

#R2_HOST = os.getenv('R2_HOST')
#R2_USERNAME = os.getenv('R2_USERNAME')
#R2_PASSWORD = os.getenv('R2_PASSWORD')
#R2_DEVICE_TYPE = os.getenv('R2_DEVICE_TYPE', 'cisco_ios')

# Network Device Configuration
DEVICE_CONFIG = {
    'R1': {
        'device_type': R1_DEVICE_TYPE,
        'host': R1_HOST,
        'username': R1_USERNAME,
        'password': R1_PASSWORD,
        'secret': R1_PASSWORD,  # Enable password (if needed)
    },
#    'R2': {
#        'device_type': R2_DEVICE_TYPE,
#        'host': R2_HOST,
#        'username': R2_USERNAME,
#        'password': R2_PASSWORD,
#        'secret': R2_PASSWORD,  # Enable password (if needed)
#   }
    # Add other devices as needed
}

# Add after DEVICE_CONFIG definition
print("\nDevice Configuration loaded:")
print(f"R1 config: {DEVICE_CONFIG['R1']}")
#print(f"R2 config: {DEVICE_CONFIG['R2']}") 

# Validate required configuration

def validate_device_config():
    for device_name, config in DEVICE_CONFIG.items():
        if not config['host']:
            raise ValueError(f"Host not configured for {device_name}")
        if not config['username']:
            raise ValueError(f"Username not configured for {device_name}")
        if not config['password']:
            raise ValueError(f"Password not configured for {device_name}")

import openai
from config import OPENAI_API_KEY, DEVICE_CONFIG
from netmiko import ConnectHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

class NetworkAgent:
    def __init__(self):
        self.devices = DEVICE_CONFIG

    def get_device_info(self, device_name):
        """Connect to device and get information"""
        try:
            device = ConnectHandler(**self.devices[device_name])
            output = device.send_command("show running-config")
            device.disconnect()
            return output
        except Exception as e:
            logger.error(f"Error connecting to {device_name}: {str(e)}")
            return None

    def analyze_config(self, config, question):
        """Analyze configuration using OpenAI"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # or gpt-3.5-turbo
                messages=[
                    {"role": "system", "content": "You are a network configuration expert. Analyze the following configuration and answer questions about it."},
                    {"role": "user", "content": f"Configuration:\n{config}\n\nQuestion: {question}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error with OpenAI API: {str(e)}")
            return None

    def run_command(self, device_name, command):
        """Run a command on a device"""
        try:
            device = ConnectHandler(**self.devices[device_name])
            output = device.send_command(command)
            device.disconnect()
            return output
        except Exception as e:
            logger.error(f"Error running command on {device_name}: {str(e)}")
            return None

def main():
    agent = NetworkAgent()
    
    # Example usage
    device_name = 'R1'
    config = agent.get_device_info(device_name)
    
    if config:
        analysis = agent.analyze_config(
            config,
            "What security configurations are present in this device?"
        )
        print(f"Analysis for {device_name}:")
        print(analysis)
    
    # Example command
    output = agent.run_command(device_name, "show ip interface brief")
    if output:
        print(f"\nInterface Status for {device_name}:")
        print(output)

if __name__ == "__main__":
    main()
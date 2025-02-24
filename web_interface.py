from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from config import OPENAI_API_KEY, DEVICE_CONFIG
from netmiko import ConnectHandler
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

class NetworkAgent:
    def __init__(self):
        self.devices = DEVICE_CONFIG

    def get_device_info(self, device_name):
        """Connect to device and get information"""
        if device_name not in self.devices:
            logger.error(f"Device {device_name} not found in configuration")
            return None

        try:
            device = ConnectHandler(**self.devices[device_name])
            device.enable()  # Enter privileged exec mode
            output = device.send_command("show running-config")
            device.disconnect()
            return output
        except Exception as e:
            logger.error(f"Error connecting to {device_name}: {str(e)}")
            return None

    def run_command(self, device_name, command):
        """Run a command on a device"""
        try:
            device = ConnectHandler(**self.devices[device_name])
            
            # List of show/verification commands (privileged exec mode)
            show_commands = [
                'show ip',
                'show interface',
                'show run',
                'show start',
                'show version',
                'show protocols',
                'show arp',
                'show vlan',
                'show mac',
                'show',  # Generic show command
                'ping',
                'traceroute',
                'debug'
            ]
            
            # List of configuration commands (config mode)
            config_commands = [
                'ip route',
                'interface',
                'router',
                'access-list',
                'hostname',
                'ip domain',
                'crypto',
                'username',
                'password',
                'enable',
                'line',
                'logging',
                'service',
                'banner'
            ]
            
            # First, determine the command type
            is_show_command = any(cmd in command.lower() for cmd in show_commands)
            is_config_command = any(cmd in command.lower() for cmd in config_commands)
            
            # Always enter privileged exec mode first
            device.enable()
            
            # Handle command based on its type
            if is_show_command:
                # For show commands, we're already in privileged exec mode
                output = device.send_command(command)
            elif is_config_command:
                # For config commands, enter config mode
                output = device.send_config_set([command])
                device.exit_config_mode()
            else:
                # For other commands, try in current mode
                output = device.send_command(command)
            
            device.disconnect()
            return output
            
        except Exception as e:
            logger.error(f"Error running command on {device_name}: {str(e)}")
            return None

    def process_natural_language(self, device_name, user_input):
        try:
            # First, ask GPT to convert natural language to network command
            command_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a network engineer. Convert natural language requests into Cisco IOS commands.
                    Remember:
                    - Use 'show' commands for viewing information (they run in privileged exec mode)
                    - Use configuration commands for making changes (they run in config mode)
                    - For interface status, use 'show ip interface brief' or 'show interfaces'
                    - For routing information, use 'show ip route'
                    Only respond with the command, no explanation."""},
                    {"role": "user", "content": user_input}
                ]
            )
            command = command_response.choices[0].message.content.strip()
            
            # Execute the command
            output = self.run_command(device_name, command)
            
            # Analyze the output
            analysis_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a network expert. Analyze this command output and explain it in simple terms."},
                    {"role": "user", "content": f"Command: {command}\nOutput:\n{output}"}
                ]
            )
            
            return {
                "command": command,
                "raw_output": output,
                "analysis": analysis_response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {"error": str(e)}

agent = NetworkAgent()

@app.route('/')
def home():
    return render_template('index.html', devices=list(DEVICE_CONFIG.keys()))

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    device = data.get('device')
    query = data.get('query')
    
    result = agent.process_natural_language(device, query)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

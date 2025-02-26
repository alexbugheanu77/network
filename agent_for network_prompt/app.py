from flask import Flask, render_template, request, jsonify
import json
import re
import time
import random
from datetime import datetime
import os
import openai
from dotenv import load_dotenv
import threading
import ipaddress

# Network automation libraries
try:
    import netmiko
    from netmiko import ConnectHandler
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    print("Netmiko not available. SSH connections will be simulated.")

try:
    import napalm
    from napalm import get_network_driver
    NAPALM_AVAILABLE = True
except ImportError:
    NAPALM_AVAILABLE = False
    print("NAPALM not available. Device configuration will be simulated.")

try:
    from nornir import InitNornir
    from nornir.plugins.tasks.networking import netmiko_send_command
    from nornir.plugins.functions.text import print_result
    NORNIR_AVAILABLE = True
except ImportError:
    NORNIR_AVAILABLE = False
    print("Nornir not available. Parallel execution will be simulated.")

try:
    from pyats.topology import loader
    from genie.conf import Genie
    PYATS_AVAILABLE = True
except ImportError:
    PYATS_AVAILABLE = False
    print("pyATS/Genie not available. Device testing will be simulated.")

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# Simulated network devices for demo purposes
NETWORK_DEVICES = {
    "router1": {
        "type": "router", 
        "vendor": "Cisco", 
        "model": "ISR 4431", 
        "os": "IOS-XE 17.3.3", 
        "ip": "192.168.1.1",
        "username": os.getenv("ROUTER1_USERNAME", "admin"),
        "password": os.getenv("ROUTER1_PASSWORD", "admin"),
        "device_type": "cisco_ios",
        "secret": os.getenv("ROUTER1_SECRET", "")
    },
    "switch1": {
        "type": "switch", 
        "vendor": "Arista", 
        "model": "7050X3", 
        "os": "EOS 4.24.0F", 
        "ip": "192.168.1.2",
        "username": os.getenv("SWITCH1_USERNAME", "admin"),
        "password": os.getenv("SWITCH1_PASSWORD", "admin"),
        "device_type": "arista_eos",
        "secret": os.getenv("SWITCH1_SECRET", "")
    },
    "firewall1": {
        "type": "firewall", 
        "vendor": "Palo Alto", 
        "model": "PA-5220", 
        "os": "PAN-OS 10.1.0", 
        "ip": "192.168.1.3",
        "username": os.getenv("FIREWALL1_USERNAME", "admin"),
        "password": os.getenv("FIREWALL1_PASSWORD", "admin"),
        "device_type": "paloalto_panos",
        "secret": os.getenv("FIREWALL1_SECRET", "")
    },
    "loadbalancer1": {
        "type": "load balancer", 
        "vendor": "F5", 
        "model": "BIG-IP i15800", 
        "os": "TMOS 15.1.0", 
        "ip": "192.168.1.4",
        "username": os.getenv("LOADBALANCER1_USERNAME", "admin"),
        "password": os.getenv("LOADBALANCER1_PASSWORD", "admin"),
        "device_type": "f5_tmsh",
        "secret": os.getenv("LOADBALANCER1_SECRET", "")
    }
}

# Device connection cache
DEVICE_CONNECTIONS = {}

# Load the agent prompt
with open('agent_for_network_prompt.py', 'r') as file:
    AGENT_PROMPT = file.read()

def get_device_connection(device_id):
    """Get or create a connection to a network device"""
    device = NETWORK_DEVICES[device_id]
    
    # Check if we have a cached connection
    if device_id in DEVICE_CONNECTIONS and DEVICE_CONNECTIONS[device_id].get('connected', False):
        return DEVICE_CONNECTIONS[device_id]['connection']
    
    # If we're in simulation mode or libraries aren't available, return None
    if os.getenv("SIMULATION_MODE", "true").lower() == "true" or not NETMIKO_AVAILABLE:
        return None
    
    try:
        # Create device connection parameters
        device_params = {
            'device_type': device['device_type'],
            'ip': device['ip'],
            'username': device['username'],
            'password': device['password'],
            'secret': device['secret'] if device['secret'] else None,
            'timeout': 20,
        }
        
        # Connect to the device
        connection = ConnectHandler(**device_params)
        
        # Cache the connection
        DEVICE_CONNECTIONS[device_id] = {
            'connection': connection,
            'connected': True,
            'last_used': datetime.now()
        }
        
        return connection
    except Exception as e:
        print(f"Error connecting to {device_id}: {e}")
        return None

def execute_device_command(device_id, command, use_napalm=False):
    """Execute a command on a real network device"""
    device = NETWORK_DEVICES[device_id]
    
    # If we're in simulation mode, use OpenAI to simulate the response
    if os.getenv("SIMULATION_MODE", "true").lower() == "true":
        return simulate_command_execution(device_id, command)
    
    try:
        if use_napalm and NAPALM_AVAILABLE:
            # Use NAPALM for configuration management
            driver = get_network_driver(device['device_type'].replace('_', ''))
            with driver(
                hostname=device['ip'],
                username=device['username'],
                password=device['password'],
                optional_args={'secret': device['secret'] if device['secret'] else ''}
            ) as device_conn:
                
                if command.lower().startswith('get '):
                    # NAPALM getter methods
                    method = command.lower().replace('get ', '').replace(' ', '_')
                    if hasattr(device_conn, method):
                        result = getattr(device_conn, method)()
                        return json.dumps(result, indent=2)
                    else:
                        return f"Method {method} not available in NAPALM for this device type"
                
                elif command.lower().startswith('config '):
                    # NAPALM configuration
                    config_lines = command.replace('config ', '').split('\n')
                    device_conn.load_merge_candidate(config='\n'.join(config_lines))
                    diff = device_conn.compare_config()
                    if diff:
                        device_conn.commit_config()
                        return f"Configuration applied successfully:\n{diff}"
                    else:
                        device_conn.discard_config()
                        return "No configuration changes were needed"
                
                else:
                    # Fall back to CLI command
                    return device_conn.cli([command])[command]
        
        elif NETMIKO_AVAILABLE:
            # Use Netmiko for SSH connections
            connection = get_device_connection(device_id)
            if connection:
                if command.lower().startswith('configure '):
                    # Configuration mode
                    config_commands = command.replace('configure ', '').split('\n')
                    output = connection.send_config_set(config_commands)
                    return output
                else:
                    # Regular command
                    output = connection.send_command(command)
                    return output
            else:
                return simulate_command_execution(device_id, command)
        
        else:
            # Fall back to simulation
            return simulate_command_execution(device_id, command)
            
    except Exception as e:
        print(f"Error executing command on {device_id}: {e}")
        return f"Error executing command: {str(e)}"

def detect_device_from_query(query):
    """Detect which device the query is referring to using OpenAI"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a network device identifier. Extract the device name or IP address from the query. Return ONLY the device ID from this list: router1, switch1, firewall1, loadbalancer1. If no specific device is mentioned, return 'router1'."},
                {"role": "user", "content": query}
            ],
            max_tokens=10,
            temperature=0
        )
        device_id = response.choices[0].message.content.strip().lower()
        
        # Validate the response
        if device_id in NETWORK_DEVICES:
            return device_id
        return list(NETWORK_DEVICES.keys())[0]  # Default to first device
    except Exception as e:
        print(f"Error in device detection: {e}")
        # Fallback to simple detection
        for device_id, device in NETWORK_DEVICES.items():
            if device_id in query.lower() or device["ip"] in query:
                return device_id
        return list(NETWORK_DEVICES.keys())[0]

def translate_to_device_commands(query, device):
    """Use OpenAI to translate natural language to device-specific commands"""
    try:
        system_prompt = f"""
        You are a network command translator for {device['vendor']} {device['type']} devices running {device['os']}.
        Translate the following natural language request into specific CLI commands.
        Only return the exact commands that should be executed, nothing else.
        
        For configuration commands, prefix with 'configure '.
        For NAPALM getters, prefix with 'get ' (e.g., 'get interfaces').
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=500,
            temperature=0.2
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in command translation: {e}")
        # Fallback to simple translation
        if "show" in query.lower() and "interface" in query.lower():
            return "show interfaces"
        elif "show" in query.lower() and ("config" in query.lower() or "run" in query.lower()):
            return "show running-config"
        elif "configure" in query.lower() and "vlan" in query.lower():
            vlan_match = re.search(r'vlan\s+(\d+)', query, re.IGNORECASE)
            vlan_id = vlan_match.group(1) if vlan_match else "100"
            return f"configure vlan {vlan_id}\nname AUTO_VLAN_{vlan_id}"
        else:
            return query

def simulate_device_metrics(device_id, device):
    """Simulate device metrics for anomaly detection"""
    metrics = {
        "cpu": random.randint(10, 95),
        "memory": random.randint(20, 90),
        "uptime": f"{random.randint(1, 365)} days, {random.randint(0, 23)} hours",
        "temperature": random.randint(30, 75)
    }
    
    if device['type'] == 'router':
        metrics.update({
            "interfaces": {
                "up": random.randint(2, 8),
                "down": random.randint(0, 2),
                "errors": random.randint(0, 100)
            },
            "routes": random.randint(100, 10000),
            "bgp_peers": {
                "established": random.randint(1, 5),
                "down": random.randint(0, 2)
            }
        })
    
    elif device['type'] == 'switch':
        metrics.update({
            "ports": {
                "active": random.randint(10, 48),
                "inactive": random.randint(0, 10),
                "errors": random.randint(0, 50)
            },
            "vlans": random.randint(1, 100),
            "mac_addresses": random.randint(10, 10000)
        })
    
    elif device['type'] == 'firewall':
        metrics.update({
            "connections": random.randint(1000, 100000),
            "blocked_threats": random.randint(0, 1000),
            "rules": random.randint(10, 1000),
            "vpn_tunnels": {
                "up": random.randint(1, 10),
                "down": random.randint(0, 3)
            }
        })
    
    elif device['type'] == 'load balancer':
        metrics.update({
            "active_connections": random.randint(100, 10000),
            "requests_per_second": random.randint(10, 5000),
            "health_checks": {
                "passed": random.randint(5, 20),
                "failed": random.randint(0, 5)
            },
            "ssl_tps": random.randint(10, 5000)
        })
    
    return metrics

def analyze_network_anomalies(device_data):
    """Use OpenAI to analyze potential network anomalies based on device data"""
    try:
        # Generate metrics for all devices
        metrics = {}
        for device_id, device in device_data.items():
            metrics[device_id] = simulate_device_metrics(device_id, device)
        
        system_prompt = """
        You are a network anomaly detection system. Analyze the provided device metrics and identify any potential issues.
        If you detect anomalies, return them in this JSON format:
        [{"device": "device_id", "severity": "critical|warning|info", "message": "Description of the anomaly"}]
        If no anomalies are detected, return an empty array: []
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(metrics)}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        anomalies = json.loads(response.choices[0].message.content.strip())
        return anomalies
    except Exception as e:
        print(f"Error in anomaly detection: {e}")
        # Fallback to simple anomaly detection
        return detect_anomalies()

def simulate_command_execution(device_id, command):
    """Simulate executing a command on a device with OpenAI generating realistic output"""
    device = NETWORK_DEVICES[device_id]
    
    # Simulate response delay
    time.sleep(0.5)
    
    try:
        system_prompt = f"""
        You are a {device['vendor']} {device['model']} {device['type']} running {device['os']}.
        Generate a realistic CLI output for the following command.
        Only return the command output as it would appear on the device, nothing else.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in command execution simulation: {e}")
        # Fallback to simple simulation
        if "show" in command.lower() and "run" in command.lower():
            return f"Current configuration for {device['vendor']} {device['model']}:\n... configuration details would appear here ..."
        elif "show" in command.lower() and "interface" in command.lower():
            return f"Interface statistics for {device['vendor']} {device['model']}:\nGigabitEthernet0/0: up, line protocol is up\n... more interface details ..."
        elif "configure" in command.lower():
            return f"Entering configuration mode on {device['vendor']} {device['model']}...\nConfiguration applied successfully."
        else:
            return f"Command executed on {device['vendor']} {device['model']}."

def detect_anomalies():
    """Fallback anomaly detection"""
    anomalies = []
    if random.random() < 0.3:  # 30% chance of detecting an anomaly
        possible_anomalies = [
            {"device": "router1", "severity": "warning", "message": "High CPU utilization (78%)"},
            {"device": "switch1", "severity": "critical", "message": "Port GigabitEthernet1/0/24 flapping"},
            {"device": "firewall1", "severity": "info", "message": "Unusual traffic pattern detected from 203.0.113.15"},
            {"device": "loadbalancer1", "severity": "warning", "message": "Backend server pool member down (192.168.5.23)"}
        ]
        anomalies = [random.choice(possible_anomalies)]
    return anomalies

def process_natural_language(query):
    """Process natural language query using OpenAI and convert to network commands"""
    # Detect which device the query is referring to
    device_id = detect_device_from_query(query)
    device = NETWORK_DEVICES[device_id]
    
    # Translate natural language to device commands
    command = translate_to_device_commands(query, device)
    
    # Determine if we should use NAPALM for this command
    use_napalm = command.lower().startswith('get ') or command.lower().startswith('config ')
    
    # Execute the command on the device (or simulate)
    result = execute_device_command(device_id, command, use_napalm)
    
    return {
        "device": device,
        "device_id": device_id,
        "interpreted_command": command,
        "result": result,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def discover_network_devices(subnet):
    """Discover network devices in a subnet using NAPALM or Nornir"""
    discovered_devices = []
    
    # If we're in simulation mode, return simulated devices
    if os.getenv("SIMULATION_MODE", "true").lower() == "true":
        return list(NETWORK_DEVICES.values())
    
    try:
        # Parse the subnet
        network = ipaddress.IPv4Network(subnet)
        
        # Use Nornir for parallel execution if available
        if NORNIR_AVAILABLE:
            # Create a temporary inventory
            hosts = {}
            for ip in network.hosts():
                ip_str = str(ip)
                hosts[ip_str] = {
                    "hostname": ip_str,
                    "username": os.getenv("DISCOVERY_USERNAME", "admin"),
                    "password": os.getenv("DISCOVERY_PASSWORD", "admin"),
                    "platform": "ios"  # Default to IOS, will try others if this fails
                }
            
            # Initialize Nornir
            nr = InitNornir(
                inventory={
                    "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                    "options": {
                        "hosts": hosts,
                        "groups": {}
                    }
                }
            )
            
            # Try to connect to each host
            results = nr.run(task=netmiko_send_command, command_string="show version")
            
            # Process results
            for host, result in results.items():
                if not result.failed:
                    # Parse the output to determine device type
                    output = result.result
                    device_info = {
                        "ip": host,
                        "reachable": True
                    }
                    
                    # Simple parsing to determine vendor/type
                    if "Cisco IOS" in output:
                        device_info["vendor"] = "Cisco"
                        device_info["os"] = "IOS"
                        device_info["type"] = "router" if "Router" in output else "switch"
                    elif "Arista" in output:
                        device_info["vendor"] = "Arista"
                        device_info["os"] = "EOS"
                        device_info["type"] = "switch"
                    elif "Juniper" in output:
                        device_info["vendor"] = "Juniper"
                        device_info["os"] = "JUNOS"
                        device_info["type"] = "router"
                    else:
                        device_info["vendor"] = "Unknown"
                        device_info["os"] = "Unknown"
                        device_info["type"] = "Unknown"
                    
                    discovered_devices.append(device_info)
        
        # If Nornir isn't available or didn't find anything, try NAPALM
        elif NAPALM_AVAILABLE and not discovered_devices:
            # Try common device types with NAPALM
            device_types = ["ios", "eos", "junos", "nxos"]
            
            for ip in network.hosts():
                ip_str = str(ip)
                
                for device_type in device_types:
                    try:
                        driver = get_network_driver(device_type)
                        with driver(
                            hostname=ip_str,
                            username=os.getenv("DISCOVERY_USERNAME", "admin"),
                            password=os.getenv("DISCOVERY_PASSWORD", "admin"),
                            timeout=5
                        ) as device:
                            facts = device.get_facts()
                            discovered_devices.append({
                                "ip": ip_str,
                                "hostname": facts.get("hostname", "Unknown"),
                                "vendor": facts.get("vendor", "Unknown"),
                                "model": facts.get("model", "Unknown"),
                                "os_version": facts.get("os_version", "Unknown"),
                                "type": "router" if "router" in facts.get("model", "").lower() else "switch",
                                "reachable": True
                            })
                            break  # Found a working driver, move to next IP
                    except Exception:
                        continue  # Try next driver
        
        return discovered_devices
    
    except Exception as e:
        print(f"Error discovering devices: {e}")
        return list(NETWORK_DEVICES.values())

@app.route('/')
def index():
    return render_template('index.html', devices=NETWORK_DEVICES)

@app.route('/api/devices')
def get_devices():
    return jsonify(NETWORK_DEVICES)

@app.route('/api/execute', methods=['POST'])
def execute_command():
    data = request.json
    query = data.get('query', '')
    
    # Process the natural language query
    response = process_natural_language(query)
    
    # Check for anomalies using AI
    anomalies = analyze_network_anomalies(NETWORK_DEVICES)
    if anomalies:
        response["anomalies"] = anomalies
    
    return jsonify(response)

@app.route('/api/explain', methods=['POST'])
def explain_command():
    """Endpoint to explain what a command does in plain English"""
    data = request.json
    command = data.get('command', '')
    device_id = data.get('device_id', list(NETWORK_DEVICES.keys())[0])
    device = NETWORK_DEVICES[device_id]
    
    try:
        system_prompt = f"""
        You are a network command explainer for {device['vendor']} {device['type']} devices.
        Explain what the following command does in simple terms that a junior network engineer would understand.
        Be concise but thorough.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command}
            ],
            max_tokens=300,
            temperature=0.5
        )
        
        explanation = response.choices[0].message.content.strip()
        return jsonify({"explanation": explanation})
    except Exception as e:
        print(f"Error in command explanation: {e}")
        return jsonify({"explanation": f"This command appears to be for {device['type']} configuration or monitoring."})

@app.route('/api/suggest', methods=['GET'])
def suggest_commands():
    """Endpoint to suggest common commands for a device"""
    device_id = request.args.get('device_id', list(NETWORK_DEVICES.keys())[0])
    device = NETWORK_DEVICES[device_id]
    
    try:
        system_prompt = f"""
        You are a network command assistant for {device['vendor']} {device['type']} devices running {device['os']}.
        Suggest 5 common and useful commands that network engineers might want to run on this device.
        Return the suggestions as a JSON array of objects with 'command' and 'description' fields.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Suggest commands for {device['vendor']} {device['model']}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        suggestions = json.loads(response.choices[0].message.content.strip())
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        print(f"Error in command suggestions: {e}")
        # Fallback suggestions
        fallback_suggestions = [
            {"command": "show interfaces", "description": "Display interface status and statistics"},
            {"command": "show running-config", "description": "Display the current configuration"},
            {"command": "show ip route", "description": "Display the routing table"},
            {"command": "show version", "description": "Display device hardware and software information"},
            {"command": "show log", "description": "Display system logs"}
        ]
        return jsonify({"suggestions": fallback_suggestions})

@app.route('/api/discover', methods=['POST'])
def discover_devices():
    """Endpoint to discover network devices in a subnet"""
    data = request.json
    subnet = data.get('subnet', '192.168.1.0/24')
    
    # Start discovery in a background thread to avoid blocking
    def run_discovery():
        global NETWORK_DEVICES
        discovered = discover_network_devices(subnet)
        
        # Update the global device list with new discoveries
        for device in discovered:
            if 'ip' in device and device['ip'] not in [d['ip'] for d in NETWORK_DEVICES.values()]:
                device_id = f"device_{len(NETWORK_DEVICES) + 1}"
                NETWORK_DEVICES[device_id] = device
    
    threading.Thread(target=run_discovery).start()
    
    return jsonify({"message": f"Discovery started for subnet {subnet}. Check back soon for results."})

@app.route('/api/backup', methods=['POST'])
def backup_config():
    """Endpoint to backup device configurations"""
    data = request.json
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({"error": "Device ID is required"}), 400
    
    if device_id not in NETWORK_DEVICES:
        return jsonify({"error": f"Device {device_id} not found"}), 404
    
    device = NETWORK_DEVICES[device_id]
    
    # If we're in simulation mode, return a simulated backup
    if os.getenv("SIMULATION_MODE", "true").lower() == "true" or not NAPALM_AVAILABLE:
        backup_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return jsonify({
            "message": f"Configuration backup completed for {device_id}",
            "filename": f"{device_id}_{backup_time}.cfg",
            "config": simulate_command_execution(device_id, "show running-config")
        })
    
    try:
        # Use NAPALM to get the device configuration
        driver = get_network_driver(device['device_type'].replace('_', ''))
        with driver(
            hostname=device['ip'],
            username=device['username'],
            password=device['password'],
            optional_args={'secret': device['secret'] if device['secret'] else ''}
        ) as device_conn:
            # Get the configuration
            config = device_conn.get_config()
            running_config = config.get('running', '')
            
            # Save to file
            backup_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"backups/{device_id}_{backup_time}.cfg"
            
            # Ensure backups directory exists
            os.makedirs("backups", exist_ok=True)
            
            with open(filename, 'w') as f:
                f.write(running_config)
            
            return jsonify({
                "message": f"Configuration backup completed for {device_id}",
                "filename": filename,
                "config": running_config
            })
    
    except Exception as e:
        print(f"Error backing up configuration: {e}")
        return jsonify({"error": f"Failed to backup configuration: {str(e)}"}), 500

@app.route('/api/restore', methods=['POST'])
def restore_config():
    """Endpoint to restore device configurations"""
    data = request.json
    device_id = data.get('device_id')
    config = data.get('config')
    
    if not device_id or not config:
        return jsonify({"error": "Device ID and configuration are required"}), 400
    
    if device_id not in NETWORK_DEVICES:
        return jsonify({"error": f"Device {device_id} not found"}), 404
    
    device = NETWORK_DEVICES[device_id]
    
    # If we're in simulation mode, return a simulated response
    if os.getenv("SIMULATION_MODE", "true").lower() == "true" or not NAPALM_AVAILABLE:
        return jsonify({
            "message": f"Configuration restored successfully for {device_id}",
            "device": device_id
        })
    
    try:
        # Use NAPALM to restore the configuration
        driver = get_network_driver(device['device_type'].replace('_', ''))
        with driver(
            hostname=device['ip'],
            username=device['username'],
            password=device['password'],
            optional_args={'secret': device['secret'] if device['secret'] else ''}
        ) as device_conn:
            # Load the configuration
            device_conn.load_merge_candidate(config=config)
            
            # Check for differences
            diff = device_conn.compare_config()
            
            if not diff:
                device_conn.discard_config()
                return jsonify({
                    "message": "No configuration changes needed",
                    "device": device_id
                })
            
            # Commit the changes
            device_conn.commit_config()
            
            return jsonify({
                "message": f"Configuration restored successfully for {device_id}",
                "device": device_id,
                "diff": diff
            })
    
    except Exception as e:
        print(f"Error restoring configuration: {e}")
        return jsonify({"error": f"Failed to restore configuration: {str(e)}"}), 500

@app.route('/api/test', methods=['POST'])
def test_device():
    """Endpoint to run tests on a device using pyATS/Genie"""
    data = request.json
    device_id = data.get('device_id')
    test_type = data.get('test_type', 'connectivity')
    
    if not device_id:
        return jsonify({"error": "Device ID is required"}), 400
    
    if device_id not in NETWORK_DEVICES:
        return jsonify({"error": f"Device {device_id} not found"}), 404
    
    device = NETWORK_DEVICES[device_id]
    
    # If we're in simulation mode or pyATS is not available, return simulated results
    if os.getenv("SIMULATION_MODE", "true").lower() == "true" or not PYATS_AVAILABLE:
        test_results = {
            "device": device_id,
            "test_type": test_type,
            "status": "passed" if random.random() > 0.2 else "failed",
            "details": f"Simulated test results for {device['vendor']} {device['model']}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify(test_results)
    
    try:
        # Create a simple pyATS testbed
        testbed = {
            "devices": {
                device_id: {
                    "connections": {
                        "cli": {
                            "ip": device['ip'],
                            "protocol": "ssh"
                        }
                    },
                    "credentials": {
                        "default": {
                            "username": device['username'],
                            "password": device['password']
                        }
                    },
                    "os": device['device_type'].split('_')[1] if '_' in device['device_type'] else device['device_type'],
                    "type": device['type']
                }
            }
        }
        
        # Write testbed to file
        with open('testbed.yaml', 'w') as f:
            json.dump(testbed, f)
        
        # Load the testbed
        tb = loader.load('testbed.yaml')
        dev = tb.devices[device_id]
        
        # Connect to the device
        dev.connect()
        
        # Run tests based on test_type
        results = {}
        if test_type == 'connectivity':
            # Test basic connectivity
            results['ping'] = dev.ping('8.8.8.8')
            results['traceroute'] = dev.traceroute('8.8.8.8')
        elif test_type == 'interfaces':
            # Test interfaces
            parser = dev.parse('show interfaces')
            results['interfaces'] = parser
        elif test_type == 'routing':
            # Test routing
            parser = dev.parse('show ip route')
            results['routes'] = parser
        else:
            # Default to basic device info
            parser = dev.parse('show version')
            results['version'] = parser
        
        # Disconnect from the device
        dev.disconnect()
        
        return jsonify({
            "device": device_id,
            "test_type": test_type,
            "status": "passed",
            "details": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        print(f"Error testing device: {e}")
        return jsonify({
            "device": device_id,
            "test_type": test_type,
            "status": "failed",
            "details": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

@app.route('/api/analyze_network_anomalies', methods=['GET'])
def api_analyze_network_anomalies():
    """Endpoint to analyze network anomalies"""
    anomalies = analyze_network_anomalies(NETWORK_DEVICES)
    return jsonify({"anomalies": anomalies})

@app.route('/api/device_metrics', methods=['GET'])
def get_device_metrics():
    """Endpoint to get device metrics for monitoring"""
    device_id = request.args.get('device_id')
    
    if not device_id:
        # Return metrics for all devices
        metrics = {}
        for dev_id, device in NETWORK_DEVICES.items():
            metrics[dev_id] = simulate_device_metrics(dev_id, device)
        return jsonify(metrics)
    
    if device_id not in NETWORK_DEVICES:
        return jsonify({"error": f"Device {device_id} not found"}), 404
    
    device = NETWORK_DEVICES[device_id]
    metrics = simulate_device_metrics(device_id, device)
    
    return jsonify(metrics)

@app.route('/api/close_connections', methods=['POST'])
def close_connections():
    """Close all device connections"""
    global DEVICE_CONNECTIONS
    
    for device_id, conn_info in DEVICE_CONNECTIONS.items():
        if conn_info.get('connected', False) and conn_info.get('connection'):
            try:
                conn_info['connection'].disconnect()
            except Exception as e:
                print(f"Error disconnecting from {device_id}: {e}")
    
    DEVICE_CONNECTIONS = {}
    
    return jsonify({"message": "All connections closed"})

# Cleanup connections when the application exits
import atexit

@atexit.register
def cleanup_connections():
    """Clean up device connections when the application exits"""
    for device_id, conn_info in DEVICE_CONNECTIONS.items():
        if conn_info.get('connected', False) and conn_info.get('connection'):
            try:
                conn_info['connection'].disconnect()
            except Exception:
                pass

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs("backups", exist_ok=True)
    
    # Start the application
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
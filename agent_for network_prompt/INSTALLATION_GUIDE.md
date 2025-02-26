# Network Management Assistant: Installation and Setup Guide

This guide will walk you through the process of installing and running the Network Management Assistant application on your system.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

## Step 1: Set Up Your Environment

1. **Create a project directory**:
   ```bash
   mkdir network-management-assistant
   cd network-management-assistant
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

## Step 2: Create the Required Files

1. **Create the agent prompt file**:
   Create a file named `agent_for_network_prompt.py` with the content from your existing file.

2. **Create the application file**:
   Create a file named `app.py` with the content from your existing file.

3. **Create the requirements file**:
   Create a file named `requirements.txt` with the content from your existing file.

4. **Create the .env file**:
   ```bash
   touch .env
   ```
   
   Edit the `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SIMULATION_MODE=true
   
   # Optional: Device credentials (if connecting to real devices)
   ROUTER1_USERNAME=admin
   ROUTER1_PASSWORD=your_password
   SWITCH1_USERNAME=admin
   SWITCH1_PASSWORD=your_password
   FIREWALL1_USERNAME=admin
   FIREWALL1_PASSWORD=your_password
   LOADBALANCER1_USERNAME=admin
   LOADBALANCER1_PASSWORD=your_password
   ```

5. **Create the templates directory and HTML file**:
   ```bash
   mkdir -p templates
   mkdir -p static/css
   ```
   
   Create `templates/index.html` with the content from your existing file.
   Create `static/css/style.css` with the content from your existing file.

## Step 3: Install Dependencies

1. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

   Note: Some packages like pyATS/Genie might have additional dependencies or installation requirements. If you encounter issues, you can run the application in simulation mode (default) which doesn't require these packages to be fully functional.

2. **Create the backups directory**:
   ```bash
   mkdir backups
   ```

## Step 4: Run the Application

1. **Start the Flask application**:
   ```bash
   # On Windows
   python app.py

   # On macOS/Linux
   python3 app.py
   ```

2. **Access the application**:
   Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Step 5: Using the Application

1. **Explore the interface**:
   - The main terminal allows you to enter natural language commands
   - The right sidebar shows connected devices and command history
   - The network map displays your network topology

2. **Try some example commands**:
   - "Show interfaces on router1"
   - "Configure VLAN 100 on switch1"
   - "Check firewall rules on firewall1"
   - "Show CPU utilization on all devices"

3. **Use the command suggestions**:
   - Click the "Show Command Suggestions" button to see recommended commands for the selected device

4. **Backup device configurations**:
   - Use the backup feature to save device configurations

## Connecting to Real Network Devices (Optional)

If you want to connect to real network devices instead of using simulation mode:

1. **Update the .env file**:
   ```
   SIMULATION_MODE=false
   ```

2. **Update device information**:
   Edit the `NETWORK_DEVICES` dictionary in `app.py` to match your actual network devices' IP addresses and credentials.

3. **Ensure network connectivity**:
   Make sure your system can reach the network devices via SSH or the appropriate protocol.

## Troubleshooting

1. **Package installation issues**:
   - If you have trouble installing some of the network automation packages, you can still run the application in simulation mode.
   - For specific package issues, consult the documentation for that package.

2. **Connection errors**:
   - Check that your device credentials are correct
   - Verify network connectivity to the devices
   - Ensure the devices have SSH enabled and properly configured

3. **API key issues**:
   - Verify your OpenAI API key is correct and has sufficient quota
   - Check the OpenAI API status if you experience service disruptions

## Advanced Configuration

1. **Customizing device discovery**:
   - Use the `/api/discover` endpoint with a POST request containing the subnet to scan
   - Example: `{"subnet": "192.168.1.0/24"}`

2. **Running automated tests**:
   - Use the `/api/test` endpoint with a POST request specifying the device and test type
   - Example: `{"device_id": "router1", "test_type": "connectivity"}`

3. **Analyzing network anomalies**:
   - Access the `/api/analyze_network_anomalies` endpoint to get AI-powered analysis of your network

## Security Considerations

1. **API Key Protection**:
   - Never commit your `.env` file to version control
   - Consider using a secrets manager for production deployments

2. **Device Credentials**:
   - Use environment variables or a secure credential store
   - Implement proper access controls to the application

3. **Network Access**:
   - Run the application on a secure management network
   - Consider using a VPN if accessing remotely

## Features Overview

### 1. Natural Language Interface
The application allows network engineers to use plain English to:
- Query device status and configurations
- Make configuration changes
- Troubleshoot network issues
- Perform complex network tasks

### 2. Device Recognition and Management
- Automatically identifies network devices (routers, switches, firewalls, etc.)
- Detects vendor-specific characteristics
- Maintains connections securely

### 3. Configuration Management
- Translates natural language to device-specific commands
- Performs configuration backups before changes
- Supports configuration rollback
- Validates changes before applying

### 4. Anomaly Detection
- Monitors network traffic patterns
- Identifies unusual behavior
- Alerts on configuration drift
- Detects performance bottlenecks

### 5. Reporting
- Generates detailed logs of actions
- Provides visual network topology
- Creates executive summaries
- Documents configuration changes

By following this guide, you should have a fully functional Network Management Assistant that can help you manage your network devices using natural language commands and AI-powered analysis. 
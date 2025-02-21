FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports if needed (adjust according to your SMTP server settings)
EXPOSE 587 25

# Set environment variables (these should be overridden at runtime)
ENV SMTP_HOST=smtp.gmail.com
ENV SMTP_PORT=587
ENV EMAIL_ADDRESS=your@email.com
ENV EMAIL_PASSWORD=your_password

# Run the main agent
CMD ["python", "main_agent.py"] 
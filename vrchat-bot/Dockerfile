# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy your code and requirements
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]

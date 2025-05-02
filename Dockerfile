# Use the official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install -U pip && pip3 install -U -r requirements.txt
# Copy the rest of the code
COPY . .

# Command to run the bot
CMD ["python", "bot.py"]

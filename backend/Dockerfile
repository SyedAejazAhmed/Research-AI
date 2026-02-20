FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create outputs directory with proper permissions
RUN mkdir -p /app/outputs && chmod 777 /app/outputs

# Expose the port the app will run on
EXPOSE 8000

# Start the application with correct module path
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"] 
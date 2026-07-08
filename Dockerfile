# Use a lightweight, standardized production Python runtime environment
FROM python:3.11-slim

# Set internal operational directory inside the running container
WORKDIR /app

# Install dependencies clean without saving unnecessary local setup caches
RUN pip install --no-cache-dir requests markdownify google-genai python-dotenv

# Copy all remaining script files into the workspace environment container
COPY . .

# Explicit execution endpoint when 'docker run' triggers
CMD ["python", "main.py"]
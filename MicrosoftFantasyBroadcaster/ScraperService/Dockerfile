# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# 1. Copy the requirements file first (for better caching)
COPY requirements.txt .

# 2. Install dependencies (This installs openai, pika, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the Python code (scraper.py, storyline_generator.py, .env)
COPY . .

# 4. Run the scraper when the container starts
CMD ["python", "scraper.py"]
# Use Python 3.12 slim image for lightweight container
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media directory
RUN mkdir -p media/chat_files media/post_media media/product_images media/profile_images media/story_media

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

# Run migrations
RUN python manage.py migrate --noinput 2>/dev/null || true

# Expose port
EXPOSE 8000

# Run daphne server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "GlobalCreoleSociety.asgi:application"]

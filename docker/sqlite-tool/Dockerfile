# SQLite Tool Docker container
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1

WORKDIR /app

# Install required packages
RUN pip install --no-cache-dir flask flask-cors

# Copy SQLite tool files from the build context
COPY sqlite_tool.py /app/
COPY sqlite_api_server.py /app/

# Create directories for data persistence
RUN mkdir -p /app/data

# Expose the API port
EXPOSE 5555

# Simple health check using python instead of curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5555/health')" || exit 1

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Start the Flask API server
CMD ["python", "sqlite_api_server.py"]
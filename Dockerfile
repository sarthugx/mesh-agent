FROM python:3.11-slim

WORKDIR /app

# Copy package structures for dependency installation layer caching
COPY linerun/ /app/linerun/
COPY pyproject.toml README.md /app/

# Install the sub-package and application dependencies
RUN pip install --no-cache-dir ./linerun && \
    pip install --no-cache-dir .

# Copy FastAPI application directories
COPY app/ /app/app/

# Prepare sandboxed workspace and config storage
RUN mkdir -p /app/workspace /app/config && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Run under the non-privileged user account
USER appuser

ENV PORT=8000
EXPOSE 8000

# Start server bound to all interfaces
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

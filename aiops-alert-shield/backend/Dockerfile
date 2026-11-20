FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/models/contracts.py /app/backend/models/
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    strawberry-graphql \
    pydantic \
    litellm \
    httpx

# Copy repository files
COPY backend /app/backend
COPY scripts /app/scripts
COPY agents /app/agents
COPY data /app/data

ENV PYTHONPATH=/app
ENV MOCK_LLM=true

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

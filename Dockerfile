FROM python:3.12-slim

ARG PORT=8051

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy the MCP server files
COPY . .

# Install Python packages and setup TypeScript parser
# Combining commands to reduce Docker layers
RUN uv pip install --system -e . && \
    crawl4ai-setup && \
    cd knowledge_graphs && \
    npm install && \
    cd ..

# Set environment variable to indicate Docker
ENV DOCKER_CONTAINER=true

EXPOSE ${PORT}

# Command to run the MCP server
CMD ["python", "src/crawl4ai_mcp.py"]

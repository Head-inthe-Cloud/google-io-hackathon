# --- Stage 1: Build React Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy dependencies first for caching
COPY frontend/package*.json ./
RUN npm install

# Copy source and build
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Serve with FastAPI Backend ---
FROM python:3.13-slim
WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy backend dependencies and install
COPY backend/pyproject.toml backend/uv.lock ./backend/
WORKDIR /app/backend
RUN uv pip install --system -r pyproject.toml

# Copy backend source
COPY backend/ /app/backend/

# Copy data directory for catalog seeding
COPY data/ /app/data/

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose port and configure environment
EXPOSE 8080
ENV PORT=8080
ENV DATASET=dataset2
ENV CATALOG_DATASET=dataset2
ENV GEMINI_MODEL=gemini-3.5-flash

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

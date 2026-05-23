# Justfile for ClosetAI

# Sync backend dependencies
sync:
    cd backend && uv sync

# Run the FastAPI backend
run:
    cd backend && uv run uvicorn main:app --reload --port 8000

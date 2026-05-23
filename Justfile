# Justfile for ClosetAI
# Uses conda env: ai2

# Install minimal packages for agent testing in ai2
sync:
    conda run -n ai2 pip install google-genai python-dotenv

# Run the FastAPI backend (requires: conda activate ai2 + full deps)
run:
    cd backend && conda run -n ai2 uvicorn main:app --reload --port 8000

# Run try-on + guardrail agent test script
test-agents scenario="rec_m_gym_001":
    cd backend && conda run -n ai2 python scripts/test_tryon_guardrail.py --scenario {{scenario}}

test-agents-dry:
    cd backend && conda run -n ai2 python scripts/test_tryon_guardrail.py --dry-run --all

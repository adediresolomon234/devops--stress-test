# ──────────────────────────────────────────────────────────────────────────────
# DevOps Assessment — Python / FastAPI
#
# This Dockerfile is intentionally NOT optimised.
# Candidates are encouraged to improve it as part of the assessment.
# Known issues to find:
#   - No multi-stage build (image is bloated)
#   - Running as root
#   - No .dockerignore awareness baked in
#   - Single uvicorn worker (won't saturate CPU)
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Single worker — intentional bottleneck for candidates to discover and fix.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

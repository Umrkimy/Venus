# Venus Core for server mode. Build from the repository root, because Core
# installs the shared protocol package from packages/:
#   docker compose --profile server build core
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /venus/apps/core

# Dependencies first: Docker reuses this layer until requirements change.
COPY packages/venus-protocol /venus/packages/venus-protocol
COPY apps/core/requirements.txt ./
RUN pip install -r requirements.txt

COPY apps/core ./

# Run as a normal user, not root.
RUN useradd --create-home venus
USER venus

EXPOSE 9000

# Bring the database up to date, then serve.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 9000"]

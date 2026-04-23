FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY agent_local /app/agent_local
RUN rm -f /app/agent_local/data/checkpoints.json

CMD ["python", "-m", "agent_local.main"]

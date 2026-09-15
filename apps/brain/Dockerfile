FROM python:3.12-slim

WORKDIR /app

COPY apps/brain/requirements.txt apps/brain/requirements.txt
RUN pip install --no-cache-dir -r apps/brain/requirements.txt

COPY apps/brain apps/brain
COPY packages packages

ENV PYTHONPATH=/app
WORKDIR /app/apps/brain

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]

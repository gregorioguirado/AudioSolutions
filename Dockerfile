FROM python:3.12-slim
WORKDIR /app
COPY engine/ .
RUN pip install --no-cache-dir -r requirements.txt
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

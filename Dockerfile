FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-deploy.txt ./
RUN pip install --upgrade pip && pip install -r requirements-deploy.txt

COPY app ./app
COPY frontend ./frontend
COPY data ./data
COPY uploads ./uploads

RUN mkdir -p /app/uploads /app/data

EXPOSE 8000 8501

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

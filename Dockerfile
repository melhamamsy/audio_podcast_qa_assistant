FROM python:3.11.5-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-app.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-app.txt

COPY exceptions/ exceptions/
COPY prompts/ prompts/
COPY config/ config/
COPY utils/ utils/
COPY app.py .

CMD ["streamlit", "run", "app.py"]
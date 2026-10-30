FROM python:3.14.10-slim
WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium
COPY app ./app
CMD ["python", "-m", "app.workers.main"]

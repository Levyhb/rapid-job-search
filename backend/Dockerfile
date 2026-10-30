FROM python:3.14.10-slim
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium
RUN useradd --create-home --uid 10001 --user-group worker
COPY app ./app
USER 10001:10001
CMD ["python", "-m", "app.workers.main"]

FROM python:3.12-slim

WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app/src
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["bash", "run_all.sh"]

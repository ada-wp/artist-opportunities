FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY schemas ./schemas

RUN pip install --no-cache-dir -e .[api]

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "artist_resource_project.api:app", "--host", "0.0.0.0", "--port", "8000"]

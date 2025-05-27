ARG SOFTWARE_VERSION_TAG=3.10
FROM python:${SOFTWARE_VERSION_TAG}

WORKDIR /app
COPY python_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY python_app/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"] 
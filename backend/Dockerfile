FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
WORKDIR /app
COPY backend/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home app
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY tests ./tests
COPY contracts ./contracts
COPY skills ./skills
USER app
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]

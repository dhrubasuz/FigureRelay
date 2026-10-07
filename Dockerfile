# Copyright 2026 Dhruba Poudel
# SPDX-License-Identifier: Apache-2.0
FROM node:24-bookworm-slim AS interface
WORKDIR /app/frontend
RUN npm install --global pnpm@11.19.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm AS application
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FIGURERELAY_HOST=0.0.0.0 FIGURERELAY_PORT=8080 \
    FIGURERELAY_DATA_DIR=/data FIGURERELAY_FRONTEND_DIR=/app/frontend/dist
WORKDIR /app
COPY backend/ ./backend/
RUN pip install --no-cache-dir --constraint ./backend/requirements-lock.txt ./backend \
    && useradd --uid 10001 --create-home relay \
    && mkdir /data && chown relay:relay /data
COPY --from=interface /app/frontend/dist ./frontend/dist
USER relay
EXPOSE 8080
VOLUME ["/data"]
CMD ["python", "-m", "figurerelay"]

# Dockerfile
# Python 3.11 + Chromium for headless Grafana screenshots
FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg curl ca-certificates \
    chromium chromium-driver \
    libgbm1 libgtk-3-0 libnss3 libxss1 libatk-bridge2.0-0 \
    libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxrandr2 \
    fonts-liberation libappindicator3-1 libasound2 \
  && rm -rf /var/lib/apt/lists/*

# Tell Selenium where to find Chromium
ENV CHROMIUM_PATH=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# ── Python dependencies ───────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────
COPY . .

# Create output directories
RUN mkdir -p outputs/reports

# ── Default: run all tenant reports once ─────────────────────────────────
CMD ["python", "main.py"]

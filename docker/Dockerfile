FROM python:3.12-slim

# System deps for Chrome + Node.js (needed by Browser/Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg curl unzip fonts-liberation libnss3 libatk-bridge2.0-0 \
    libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libcups2 libxss1 libgtk-3-0 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Chrome (for SeleniumLibrary)
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*

# Node.js 20 LTS (required by robotframework-browser)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python packages
RUN pip install --no-cache-dir \
    robotframework==7.4.2 \
    robotframework-seleniumlibrary==6.8.0 \
    robotframework-browser==19.14.2 \
    opentelemetry-api>=1.20.0 \
    opentelemetry-sdk>=1.20.0 \
    opentelemetry-exporter-otlp-proto-http>=1.20.0 \
    jsonschema>=4.0.0

# Initialize Browser library (downloads Playwright browsers)
RUN rfbrowser init

WORKDIR /work

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python packages and the browser used by Playwright during image build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY tcgplayer_cards.py .

ENTRYPOINT ["python", "tcgplayer_cards.py"]

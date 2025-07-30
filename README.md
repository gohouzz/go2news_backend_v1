# Go2News Backend API

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set your API key:
   ```bash
   cp .env.example .env
   # Edit .env and set NEWSDATA_API_KEY
   ```

3. Run locally:
   ```bash
   python app.py
   ```

4. Deploy with Gunicorn (recommended for production):
   ```bash
   gunicorn app:app
   ```

## Endpoints

- `/news` - Get latest news (query params: language, country, size, etc.)
- `/first-run/v1` - Get news based on user location (query param: location)
- `/health` - Health check

## Environment Variables
- `NEWSDATA_API_KEY` - Your NewsData.io API key

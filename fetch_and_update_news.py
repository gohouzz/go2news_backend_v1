import os
import sys
import requests
import logging
from db import store_articles
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Load environment variables
load_dotenv()

API_KEY = 'pub_e76dcc8b6ab4489e820d4809debdce21'
API_URL = 'https://newsdata.io/api/1/latest'

# Define the parameter combinations you want to fetch
LANGUAGES = ['en', 'te', 'hi']  # Add more as needed
COUNTRIES = ['in']  # Add more as needed
CATEGORIES = []  # Example: ['politics', 'sports']
SIZE = 50


def fetch_news(params):
    params['apikey'] = API_KEY
    try:
        response = requests.get(API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if 'results' in data and isinstance(data['results'], list):
            logging.info(f"Fetched {len(data['results'])} articles for params: {params}")
            return data['results']
        else:
            logging.warning(f"No results for params: {params}")
            return []
    except Exception as e:
        logging.error(f"Failed to fetch news for params {params}: {e}")
        return []

def main():
    total_articles = 0
    for lang in LANGUAGES:
        for country in COUNTRIES:
            # If you want to fetch by category, add another loop here
            params = {
                'language': lang,
                'country': country,
                'size': SIZE
            }
            articles = fetch_news(params)
            if articles:
                try:
                    store_articles(articles)
                    total_articles += len(articles)
                except Exception as e:
                    logging.error(f"Failed to store articles for params {params}: {e}")
    logging.info(f"Done. Total articles processed: {total_articles}")

if __name__ == "__main__":
    main() 
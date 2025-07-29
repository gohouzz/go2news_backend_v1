from flask import Flask, jsonify, redirect, url_for, request
import os
import requests
import json
from flask_cors import CORS
# from dotenv import load_dotenv
import re
from db import create_tables, get_cached_articles, store_articles, get_database_stats, cleanup_old_articles, get_cached_articles_by_type2
# from apscheduler.schedulers.background import BackgroundScheduler
from fetch_and_update_news import main as fetch_and_update_news_main

list = ['id', 'qInTitle', 'qInMeta', 'timeframe', 'sentiment', ]

parameters = {
    'id': '',
    'qInTitle': '',
    'qInMeta': '',
    'timeframe': '15m',
    'country': 'in',
    'category': '',
    'excludecategory': '',
    'language': 'te',
    'tag': '',
    'sentiment': '',
    'region': '',
    'domain': '',
    'domainurl': '',
    'excludedomain': '',
    'excludefield': '',
    'prioritydomain': '',
    'timezone': '',
    'full_content': '',
    'image': '',
    'video': '',
    'removeduplicate': '',
    'size': '',
    'page': ''
}

# load_dotenv()
app = Flask(__name__)
CORS(app)

# Start APScheduler background job to fetch news every 5 minutes
# scheduler = BackgroundScheduler()
# scheduler.add_job(fetch_and_update_news_main, 'interval', minutes=5)
# scheduler.start()

# Create database tables at startup
try:
    create_tables()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def home():
    return redirect(url_for('news'))

@app.route('/news')
def news():
    # api_key = 'pub_e76dcc8b6ab4489e820d4809debdce21'
    # if not api_key:
        # return jsonify({'error': 'API key not set. Please set NEWSDATA_API_KEY environment variable.'}), 401

    # Get user parameters
    user_params = request.args.to_dict()
    if 'language' not in user_params:
        user_params['language'] = 'telugu'
    if 'country' not in user_params:
        user_params['country'] = ['india']

    # Try to get cached articles first
    cached_articles = get_cached_articles_by_type2(user_params)
    
    if cached_articles:
        # Return cached data
        return jsonify({
            "status": "success",
            "news": cached_articles,
            "source": "cache",
        })
    
    # If no cached articles found, return empty result
    return jsonify({
        "status": "success",
        "news": [],
        "source": "cache",
        "message": "No articles found"
    })

# def summarize_text(text, max_words=60):
#     """
#     Simple text summarization by taking the first 60 words
#     and ensuring it ends with a complete sentence.
#     """
#     if not text:
#         return ""
    
#     # Remove HTML tags if any
#     text = re.sub(r'<[^>]+>', '', text)
    
#     # Split into words
#     words = text.split()
    
#     if len(words) <= max_words:
#         return text
    
#     # Take first max_words words
#     truncated = ' '.join(words[:max_words])
    
#     # Try to end with a complete sentence
#     sentences = truncated.split('.')
#     if len(sentences) > 1:
#         # Remove the last incomplete sentence and add period
#         complete_text = '.'.join(sentences[:-1]) + '.'
#         if len(complete_text.split()) <= max_words:
#             return complete_text
    
#     # If we can't make a complete sentence, just truncate and add ellipsis
#     return truncated + '...'

# '''
# This function is useful for running personalised news or advertisements
@app.route('/advertisements')
def advertisements():
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    # Get SQS queue URL and AWS credentials from environment variables
    sqs_queue_url = os.environ.get('AWS_SQS_QUEUE_URL')
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')

    if not sqs_queue_url or not aws_access_key or not aws_secret_key:
        return jsonify({'error': 'Missing AWS SQS configuration. Please set AWS_SQS_QUEUE_URL, AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY environment variables.'}), 401

    try:
        sqs = boto3.client(
            'sqs',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        # Receive messages from the SQS queue
        response = sqs.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=2
        )
        messages = response.get('Messages', [])
        # Optionally, delete messages after reading (uncomment if needed)
        # for msg in messages:
        #     sqs.delete_message(QueueUrl=sqs_queue_url, ReceiptHandle=msg['ReceiptHandle'])
        return jsonify(messages)
    except (BotoCoreError, ClientError) as e:
        return jsonify({'error': 'Failed to fetch messages from SQS', 'details': str(e)}), 500
@app.route('/first-run/v1')
def first_run():
    parameters = request.args.to_dict()
    languages = {
        "AndamanandNicobarIslands": "bn",
        "AndhraPradesh": "te",
        "ArunachalPradesh": "en",
        "Assam": "as",
        "Bihar": "hi",
        "Chandigarh": "hi",
        "Chhattisgarh": "hi",
        "DadraandNagarHaveliandDamanandDiu": "gu",
        "Delhi": "hi",
        "Goa": "en",
        "Gujarat": "gu",
        "Haryana": "hi",
        "HimachalPradesh": "hi",
        "JammuandKashmir": "en",
        "Jharkhand": "hi",
        "Karnataka": "en",
        "Kerala": "en",
        "Ladakh": "en",
        "Lakshadweep": "en",
        "MadhyaPradesh": "hi",
        "Maharashtra": "mr",
        "Manipur": "en",
        "Meghalaya": "en",
        "Mizoram": "en",
        "Nagaland": "en",
        "Odisha": "en",
        "Puducherry": "ta",
        "Punjab": "pa",
        "Rajasthan": "hi",
        "Sikkim": "en",
        "TamilNadu": "ta",
        "Telangana": "te",
        "Tripura": "bn",
        "UttarPradesh": "hi",
        "Uttarakhand": "hi",
        "WestBengal": "bn"
    }
    location = parameters.get('location', 'Sikkim')
    language = languages.get(location, 'en')
    
    # Try to get cached articles first
    params = {'language': language, 'country': 'in'}
    cached_articles, params_hash = get_cached_articles(params, max_age_hours=1)
    
    if cached_articles:
        return jsonify({
            "status": "success",
            "results": cached_articles,
            "source": "cache"
        })
    
    # If no cache, fetch from API
    api_key = 'pub_e76dcc8b6ab4489e820d4809debdce21'
    if not api_key:
        return jsonify({'error': 'API key not set. Please set NEWSDATA_API_KEY environment variable.'}), 401
    url = 'https://newsdata.io/api/1/latest'
    params = {'apikey': api_key, 'language': language, 'country': 'in'}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Store articles in database
        if 'results' in data and isinstance(data['results'], list):
            try:
                store_articles(data['results'], params_hash)
            except Exception as e:
                print(f"Warning: Could not store articles in database: {e}")
        
        return jsonify(data)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to fetch news', 'details': str(e)}), 500

@app.route('/stats')
def stats():
    """Get database statistics"""
    try:
        stats = get_database_stats()
        if stats:
            return jsonify({
                "status": "success",
                "stats": stats
            })
        else:
            return jsonify({'error': 'Could not retrieve database stats'}), 500
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

@app.route('/cleanup')
def cleanup():
    """Clean up old articles (admin endpoint)"""
    try:
        days_to_keep = request.args.get('days', 7, type=int)
        deleted_count = cleanup_old_articles(days_to_keep)
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        })
    except Exception as e:
        return jsonify({'error': 'Cleanup failed', 'details': str(e)}), 500

@app.route('/testjson')
def testjson():
    return jsonify({"hello": "world", "numbers": [1, 2, 3]})

@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error': 'Not Found', 'message': str(e)}), 404

if __name__ == '__main__': 
    app.run(debug=True)

from flask import Flask, jsonify, redirect, url_for, request
import os
import requests
import json
from flask_cors import CORS
from dotenv import load_dotenv
import re
from database import init_app, db
from scheduler import start_article_scheduler, stop_article_scheduler, get_scheduler_status

load_dotenv()
app = Flask(__name__)
CORS(app)

# Initialize database
init_app(app)

# Start the article collection scheduler
scheduler_started = start_article_scheduler()
if scheduler_started:
    print("✅ Article collection scheduler started successfully")
else:
    print("❌ Failed to start article collection scheduler")

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def home():
    return redirect(url_for('news'))

@app.route('/news')
def news():
    try:
        # Import our database components
        from secure_db import db_manager
        from queries import NewsQueries
        
        # Get parameters from request
        user_params = request.args.to_dict()
        language = user_params.get('language', 'te')
        country = user_params.get('country', 'in')
        size = int(user_params.get('size', 50))
        
        # Parse country parameter (can be comma-separated)
        countries = country.split(',') if country else ['in']
        
        # Use secure database connection
        with db_manager.get_connection() as db:
            # Get news from database using our query system
            articles = NewsQueries.get_articles_with_advanced_filters(
                country=countries,
                language=language,
                limit=size,
                sort_by='pub_date',
                sort_order='desc'
            )
            
            # Convert articles to dictionary format
            news_data = []
            for article in articles:
                article_dict = article.to_dict()
                # Apply content summarization
                if article_dict.get('content'):
                    article_dict['content'] = summarize_text(article_dict['content'])
                news_data.append(article_dict)
            
            # Return response in same format as before
            return jsonify({
                "status": "success",
                "news": news_data,
                "source": "database"
            })
            
    except Exception as e:
        # Fallback to external API if database fails
        print(f"Database error: {e}")
        return fallback_to_external_api(user_params)

def fallback_to_external_api(user_params):
    """Fallback to external API when database is unavailable"""
    try:
        from newsdataapi import NewsDataApiClient
        
        api_key = 'pub_6ba8c95994ed43399a65b9859a83e0ac'
        api_client = NewsDataApiClient(apikey=api_key)
        
        # Set default parameters
        if 'language' not in user_params:
            user_params['language'] = 'te'
        if 'country' not in user_params:
            user_params['country'] = 'in'
        if 'size' not in user_params:
            user_params['size'] = '50'
        
        # Use NewsDataApiClient with scroll=True
        response = api_client.news_api(
            language=user_params['language'],
            country=user_params['country'],
            size=int(user_params['size']),
            scroll=True
        )
        
        # Process articles
        if response and hasattr(response, 'results') and response.results:
            for article in response.results:
                if hasattr(article, 'content') and article.content:
                    article.content = summarize_text(article.content)
        
        # Return response
        return jsonify({
            "status": "success",
            "news": response.results if response and hasattr(response, 'results') else [],
            "source": "external_api"
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch news', 'details': str(e)}), 500

@app.route('/api/news/save', methods=['POST'])
def save_news_to_database():
    """Save news articles from external API to database"""
    try:
        from secure_db import db_manager
        from queries import NewsQueries
        
        # Get parameters from request
        user_params = request.args.to_dict()
        language = user_params.get('language', 'te')
        country = user_params.get('country', 'in')
        size = int(user_params.get('size', 50))
        
        # Fetch from external API using NewsDataApiClient
        from newsdataapi import NewsDataApiClient
        
        api_key = 'pub_6ba8c95994ed43399a65b9859a83e0ac'
        api_client = NewsDataApiClient(apikey=api_key)
        
        response = api_client.news_api(
            language=language,
            country=country,
            size=size,
            scroll=True
        )
        
        if not response or not hasattr(response, 'results') or not response.results:
            return jsonify({'error': 'No articles found from API'}), 404
        
        # Save articles to database
        with db_manager.get_connection() as db:
            saved_articles = NewsQueries.bulk_save_articles(data['results'])
            
            return jsonify({
                "status": "success",
                "message": f"Saved {len(saved_articles)} articles to database",
                "saved_count": len(saved_articles),
                "total_articles": len(data['results'])
            })
            
    except Exception as e:
        return jsonify({'error': f'Failed to save articles: {str(e)}'}), 500

@app.route('/api/news/search')
def search_news():
    """Advanced news search with database queries"""
    try:
        from secure_db import db_manager
        from queries import NewsQueries
        
        # Get all search parameters
        params = request.args.to_dict()
        
        # Parse parameters for advanced filtering
        search_params = {
            'id': params.get('id'),
            'country': params.get('country', '').split(',') if params.get('country') else None,
            'category': params.get('category', '').split(',') if params.get('category') else None,
            'language': params.get('language'),
            'sentiment': params.get('sentiment'),
            'tag': params.get('tag'),
            'q': params.get('q'),
            'qInTitle': params.get('qInTitle'),
            'qInMeta': params.get('qInMeta'),
            'timeframe': params.get('timeframe'),
            'limit': int(params.get('limit', 50)),
            'sort_by': params.get('sort_by', 'pub_date'),
            'sort_order': params.get('sort_order', 'desc')
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        # Use secure database connection
        with db_manager.get_connection() as db:
            articles = NewsQueries.get_articles_with_advanced_filters(**search_params)
            
            # Convert to dictionary format
            news_data = []
            for article in articles:
                article_dict = article.to_dict()
                if article_dict.get('content'):
                    article_dict['content'] = summarize_text(article_dict['content'])
                news_data.append(article_dict)
            
            return jsonify({
                "status": "success",
                "news": news_data,
                "count": len(news_data),
                "filters_applied": search_params,
                "source": "database"
            })
            
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/scheduler/status')
def scheduler_status():
    """Get scheduler status"""
    try:
        status = get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': f'Failed to get scheduler status: {str(e)}'}), 500

@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the article collection scheduler"""
    try:
        success = start_article_scheduler()
        if success:
            return jsonify({'status': 'success', 'message': 'Scheduler started successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to start scheduler'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to start scheduler: {str(e)}'}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the article collection scheduler"""
    try:
        stop_article_scheduler()
        return jsonify({'status': 'success', 'message': 'Scheduler stopped successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to stop scheduler: {str(e)}'}), 500

def summarize_text(text, max_words=60):
    """
    Simple text summarization by taking the first 60 words
    and ensuring it ends with a complete sentence.
    """
    if not text:
        return ""
    
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    
    # Split into words
    words = text.split()
    
    if len(words) <= max_words:
        return text
    
    # Take first max_words words
    truncated = ' '.join(words[:max_words])
    
    # Try to end with a complete sentence
    sentences = truncated.split('.')
    if len(sentences) > 1:
        # Remove the last incomplete sentence and add period
        complete_text = '.'.join(sentences[:-1]) + '.'
        if len(complete_text.split()) <= max_words:
            return complete_text
    
    # If we can't make a complete sentence, just truncate and add ellipsis
    return truncated + '...'

'''
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
'''
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
    api_key = 'pub_e76dcc8b6ab4489e820d4809debdce21'
    if not api_key:
        return jsonify({'error': 'API key not set. Please set NEWSDATA_API_KEY environment variable.'}), 401
    url = 'https://newsdata.io/api/1/latest'
    params = {'apikey': api_key, 'language': language, 'country': 'in'}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to fetch news', 'details': str(e)}), 500

@app.route('/testjson')
def testjson():
    return jsonify({"hello": "world", "numbers": [1, 2, 3]})

@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error': 'Not Found', 'message': str(e)}), 404

if __name__ == '__main__': 
    app.run(debug=True)

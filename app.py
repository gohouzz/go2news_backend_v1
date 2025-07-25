from flask import Flask, jsonify, redirect, url_for, request
import os
import requests
import json
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return redirect(url_for('news'))

@app.route('/news')
def news():
    api_key = 'pub_e76dcc8b6ab4489e820d4809debdce21'
    if not api_key:
        return jsonify({'error': 'API key not set. Please set NEWSDATA_API_KEY environment variable.'}), 401

    url = 'https://newsdata.io/api/1/latest'
    # Extract query parameters from the request URL
    user_params = request.args.to_dict()
    # Set default values if not provided
    if 'language' not in user_params:
        user_params['language'] = 'en'
    if 'country' not in user_params:
        user_params['country'] = 'in'
    if 'size' not in user_params:
        user_params['size'] = '50'
    # Always include the API key
    params = {'apikey': api_key}
    # Add/override with user-provided params (e.g., language, country, etc.)
    params.update(user_params)
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return json.dumps(data, ensure_ascii=False)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to fetch news', 'details': str(e)}), 500
    
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
    # This route can be used to perform any first-run setup tasks
    # params should receive end-user's location as parameter with 'location'=
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
    # Call the /news endpoint logic with the detected language
    # Reuse the news() function by passing language as a query param
    # But since news() uses request.args, we need to call the logic directly
    api_key = 'pub_e76dcc8b6ab4489e820d4809debdce21'
    url = 'https://newsdata.io/api/1/latest'
    params = {'apikey': api_key, 'language': language, 'country': 'in'}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return json.dumps(data, ensure_ascii=False)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to fetch news', 'details': str(e)}), 500

@app.errorhandler(404)
def handle_404(e):
    return jsonify({'error': 'Not Found', 'message': str(e)}), 404
if __name__ == '__main__': 
    app.run(debug=True)

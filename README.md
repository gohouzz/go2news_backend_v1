## Features
- Fetches latest news from [newsdata.io](https://newsdata.io/) API
- Maps user location to language for personalized news
- Fetches advertisements from AWS SQS
- CORS enabled for frontend integration

## Setup
1. Clone or download this repository and unzip on your server.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables as needed (for AWS SQS, etc).
4. Run the app:
   ```
   python app.py
   ```

## Endpoints
- `/` 
  - Redirects to `/news` endpoint.
- `/news`
  - Returns latest news from newsdata.io.
  - Accepts query parameters:
    - `language` (default: `en`)
    - `country` (default: `in`)
    - Any other supported by newsdata.io
- `/first-run/v1`
  - Returns news based on user's location (maps location to language).
  - Accepts query parameter: `location` (e.g., `AndhraPradesh`, `TamilNadu`, etc.)
- `/advertisements` (currently commented out)
  - Fetches messages from AWS SQS queue.
  - Requires AWS credentials and SQS queue URL as environment variables.
- Error handling for 404 (returns JSON error message).

## Environment Variables
- `AWS_SQS_QUEUE_URL` - SQS queue URL for advertisements
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (default: `us-east-1`)

## Notes
- The API key for newsdata.io is currently hardcoded. For production, move it to an environment variable.
- Update the endpoints and logic as needed for your use case.

---
Feel free to modify this README and the endpoints as per your requirements.

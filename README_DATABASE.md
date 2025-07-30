# Database Setup Documentation

## Overview
This project uses PostgreSQL on AWS RDS with secure SSH tunnel connection through EC2.

## Files Structure

### Core Database Files
- `database.py` - SQLAlchemy initialization and configuration
- `models.py` - Database models (NewsArticle)
- `queries.py` - Database query operations
- `secure_db.py` - Secure SSH tunnel connection manager

### Migration Files
- `migrations/` - Database migration files
- `migrate.py` - Migration runner script

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Migrations
```bash
flask db init
```

### 3. Create Migration
```bash
flask db migrate -m "Initial migration"
```

### 4. Run Migrations (Secure)
```bash
python migrate.py
```

## Database Connection

### Secure Connection (Recommended)
The project uses SSH tunnel to connect to RDS through EC2:

```python
from secure_db import db_manager

# Use in your code
with db_manager.get_connection() as db:
    articles = NewsQueries.get_latest_news()
```

### Configuration
- **EC2 Host:** ec2-3-80-189-208.compute-1.amazonaws.com
- **SSH Key:** /Users/saitejareddygutpe/Downloads/dubaiedeals.pem
- **RDS Endpoint:** database-1.cw3egoy2c577.us-east-1.rds.amazonaws.com
- **Database:** go2news

## Query Examples

### Basic Queries
```python
from queries import NewsQueries

# Get latest news
articles = NewsQueries.get_latest_news(limit=50)

# Search by country
articles = NewsQueries.get_news_by_countries(['in', 'us'])

# Advanced filtering
articles = NewsQueries.get_articles_with_advanced_filters(
    country=['in', 'us'],
    q='Palestinian',
    timeframe='1d'
)
```

### Save Articles
```python
from queries import NewsQueries

# Save single article
article = NewsQueries.save_article(api_data)

# Save multiple articles
articles = NewsQueries.bulk_save_articles(articles_data)
```

## Phase 4 Complete ✅
- ✅ Foundation Setup
- ✅ Data Models  
- ✅ Database Operations
- ✅ Migration System

Ready for Phase 5: Integration 
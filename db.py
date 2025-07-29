import psycopg2
from pypika import Query, Table, Order
import json
from datetime import datetime, timedelta
import logging
from psycopg2.extensions import adapt
# from pypika import Or
from psycopg2.extras import execute_values
from sshtunnel import SSHTunnelForwarder  # Add this import

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SSH and DB config (update these as needed)
SSH_KEY_PATH = '/Users/saitejareddygutpe/go2news2/go2news_backend_v1/dubaiedeals.pem'  # Path to your PEM file
SSH_USER = 'ubuntu'                   # Or 'ubuntu', depending on your EC2 OS
SSH_HOST = 'ec2-3-80-189-208.compute-1.amazonaws.com'              # Public IP of your EC2 instance

RDS_HOST = 'database-1.cw3egoy2c577.us-east-1.rds.amazonaws.com'
RDS_PORT = 5432
DB_NAME = 'go2news'
DB_USER = 'postgres'
DB_PASS = 'GoHouzz2025'
LOCAL_BIND_PORT = 6543  # You can pick any free local port

column_types = {
    "id": "serial",
    "article_id": "varchar",
    "title": "varchar",
    "link": "varchar",
    "pub_date_tz": "varchar",
    "image_url": "varchar",
    "video_url": "varchar",
    "source_id": "varchar",
    "source_name": "varchar",
    "source_url": "varchar",
    "source_icon": "varchar",
    "language": "varchar",
    "sentiment": "varchar",
    "description": "text",
    "content": "text",
    "ai_summary": "text",
    "ai_content": "text",
    "keywords": "text_array",
    "creator": "text_array",
    "country": "text_array",
    "category": "text_array",
    "ai_tag": "text_array",
    "ai_region": "text_array",
    "ai_org": "text_array",
    "source_priority": "bigint",
    "pub_date": "timestamp",
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "duplicate": "boolean",
    "sentiment_stats": "jsonb"
}

search_params_mapping = {
    "q": ["title", "link", "keywords", "image_url", "description", "content", "ai_tag", "ai_summary", "ai_content", "category", "ai_tag", "ai_region", "sentiment"],
    "qInTitle": ["title"],
    "qInMeta": ["title", "link", "keywords", "description", "tag"]
}

def is_valid_param(val):
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip() != ''
    if isinstance(val, (list, tuple)):
        return len(val) > 0
    return True

def get_cached_articles_by_type(params):
    """
    Get articles from the database using filters, building where conditions according to the column_types dict.
    Uses '&&' for array columns (TEXT[]), and direct equality for others.
    Only columns present in both params and the type dict are handled, and only if the value is a non-empty string or non-empty list/tuple.
    """
    conn, tunnel = get_connection()
    cur = conn.cursor()
    try:
        news = Table('news_articles')
        q = Query.from_(news).select('*')
        array_where_clauses = []
        array_values = []
        # Loop through params and add where clauses based on type
        for col, val in params.items():
            if col not in column_types or not is_valid_param(val):
                # Check if this param is a search parameter from search_params_mapping
                if col in search_params_mapping:
                    search_columns = search_params_mapping[col]
                    # Create OR conditions for searching across multiple columns
                    search_conditions = []
                    for search_col in search_columns:
                        if search_col in column_types:
                            # Use ILIKE for case-insensitive substring search
                            search_conditions.append(getattr(news, search_col).ilike(f"%{val}%"))
                    
                    if search_conditions:
                        # Combine all search conditions with OR
                        combined_condition = " OR ".join([getattr(news, sc).ilike(f"%{val}%") for sc in search_columns])
                        q = q.where(combined_condition)
                continue
            col_type = column_types[col]
            if col_type == "text_array":
                # Use '&&' for array overlap
                if not isinstance(val, list):
                    val = [val]
                array_where_clauses.append(f"{col} && %s")
                array_values.append(val)
            elif col_type in ("varchar", "text"):
                q = q.where(getattr(news, col) == val)
            elif col_type == "bigint":
                q = q.where(getattr(news, col) == int(val))
            elif col_type == "timestamp":
                if isinstance(val, str):
                    try:
                        val = datetime.fromisoformat(val)
                    except Exception:
                        continue
                q = q.where(getattr(news, col) == val)
            elif col_type == "boolean":
                if isinstance(val, str):
                    val = val.lower() == 'true'
                q = q.where(getattr(news, col) == val)
            # skip serial and jsonb for filtering
        # Limit if size param
        if 'size' in params and is_valid_param(params['size']):
            try:
                q = q.limit(int(params['size']))
            except Exception:
                pass
        q = q.orderby(news.pub_date, order=Order.desc)
        sql = q.get_sql()
        print(sql)
        # If there are array filters, append them to the WHERE clause
        if array_where_clauses:
            if 'WHERE' in sql:
                sql += ' AND ' + ' AND '.join(array_where_clauses)
            else:
                sql += ' WHERE ' + ' AND '.join(array_where_clauses)
        cur.execute(sql, array_values)
        columns = [desc[0] for desc in cur.description]
        articles = []
        for row in cur.fetchall():
            article = dict(zip(columns, row))
            for tcol in [k for k, v in column_types.items() if v == 'timestamp']:
                if article.get(tcol):
                    article[tcol] = article[tcol].isoformat()
            articles.append(article)
        logger.info(f"Retrieved {len(articles)} articles from database with filters by type (&& for arrays, dict-driven)")
        return articles
    except Exception as e:
        logger.error(f"Error getting articles by type: {e}")
        return None
    finally:
        cur.close()
        conn.close()
        tunnel.stop()

def get_connection():
    """
    Establishes an SSH tunnel to the EC2 instance and connects to the RDS database through it.
    Returns (conn, tunnel). You must close both when done.
    """
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY_PATH,
        remote_bind_address=(RDS_HOST, RDS_PORT),
        local_bind_address=('localhost', LOCAL_BIND_PORT)
    )
    tunnel.start()
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host='localhost',
        port=LOCAL_BIND_PORT
    )
    return conn, tunnel  # Caller must close both

def create_tables():
    """Create the necessary tables if they don't exist"""
    conn, tunnel = get_connection()
    cur = conn.cursor()

    # Create news articles table with expanded schema
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            article_id VARCHAR(64),
            title VARCHAR(500),
            link VARCHAR(500) UNIQUE,
            keywords TEXT[],
            creator TEXT[],
            description TEXT,
            content TEXT,
            pub_date TIMESTAMP,
            pub_date_tz VARCHAR(16),
            image_url VARCHAR(500),
            video_url VARCHAR(500),
            source_id VARCHAR(100),
            source_name VARCHAR(200),
            source_priority BIGINT,
            source_url VARCHAR(500),
            source_icon VARCHAR(500),
            language VARCHAR(32),
            country TEXT[],
            category TEXT[],
            sentiment VARCHAR(32),
            sentiment_stats JSONB,
            ai_tag TEXT[],
            ai_region TEXT[],
            ai_org TEXT[],
            ai_summary TEXT,
            ai_content TEXT,
            duplicate BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_language ON news_articles(language)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_country ON news_articles USING GIN(country)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_pub_date ON news_articles(pub_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_category ON news_articles USING GIN(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_keywords ON news_articles USING GIN(keywords)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_creator ON news_articles USING GIN(creator)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment)")

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database tables created/verified successfully")
    tunnel.stop()

def normalize_article(article):
    """
    Normalize a raw article dict to match the DB schema, handling missing fields and type conversions.
    """
    def arr(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]
    def jsonb(val):
        if val is None:
            return None
        return json.dumps(val)
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == 'true'
        return False
    def to_datetime(val):
        if not val:
            return None
        try:
            return datetime.fromisoformat(val)
        except Exception:
            try:
                return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
    return {
        'article_id': article.get('article_id'),
        'title': article.get('title'),
        'link': article.get('link'),
        'keywords': arr(article.get('keywords')),
        'creator': arr(article.get('creator')),
        'description': article.get('description'),
        'content': article.get('content'),
        'pub_date': to_datetime(article.get('pubDate')),
        'pub_date_tz': article.get('pubDateTZ'),
        'image_url': article.get('image_url'),
        'video_url': article.get('video_url'),
        'source_id': article.get('source_id'),
        'source_name': article.get('source_name'),
        'source_priority': article.get('source_priority'),
        'source_url': article.get('source_url'),
        'source_icon': article.get('source_icon'),
        'language': article.get('language'),
        'country': arr(article.get('country')),
        'category': arr(article.get('category')),
        'sentiment': article.get('sentiment'),
        'sentiment_stats': article.get('sentiment_stats'),
        'ai_tag': arr(article.get('ai_tag')),
        'ai_region': arr(article.get('ai_region')),
        'ai_org': arr(article.get('ai_org')),
        'ai_summary': article.get('ai_summary'),
        'ai_content': article.get('ai_content'),
        'duplicate': to_bool(article.get('duplicate')),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

def store_articles(articles, params_hash=None):
    """Store articles in the database"""
    conn, tunnel = get_connection()
    tunnel.stop()
    cur = conn.cursor()
    try:
        # Normalize all articles
        norm_articles = [normalize_article(a) for a in articles]
        # Prepare columns and values
        columns = [
            'article_id', 'title', 'link', 'keywords', 'creator', 'description', 'content',
            'pub_date', 'pub_date_tz', 'image_url', 'video_url', 'source_id', 'source_name',
            'source_priority', 'source_url', 'source_icon', 'language', 'country', 'category',
            'sentiment', 'sentiment_stats', 'ai_tag', 'ai_region', 'ai_org', 'ai_summary',
            'ai_content', 'duplicate', 'created_at', 'updated_at'
        ]
        values = [
            [
                a['article_id'], a['title'], a['link'], a['keywords'], a['creator'], a['description'], a['content'],
                a['pub_date'], a['pub_date_tz'], a['image_url'], a['video_url'], a['source_id'], a['source_name'],
                a['source_priority'], a['source_url'], a['source_icon'], a['language'], a['country'], a['category'],
                a['sentiment'], json.dumps(a['sentiment_stats']) if a['sentiment_stats'] is not None else None,
                a['ai_tag'], a['ai_region'], a['ai_org'], a['ai_summary'], a['ai_content'], a['duplicate'],
                a['created_at'], a['updated_at']
            ] for a in norm_articles
        ]
        insert_sql = f"""
            INSERT INTO news_articles (
                article_id, title, link, keywords, creator, description, content,
                pub_date, pub_date_tz, image_url, video_url, source_id, source_name,
                source_priority, source_url, source_icon, language, country, category,
                sentiment, sentiment_stats, ai_tag, ai_region, ai_org, ai_summary,
                ai_content, duplicate, created_at, updated_at
            ) VALUES %s
            ON CONFLICT (link) DO UPDATE SET
                updated_at = EXCLUDED.updated_at,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                content = EXCLUDED.content,
                keywords = EXCLUDED.keywords,
                creator = EXCLUDED.creator,
                pub_date = EXCLUDED.pub_date,
                pub_date_tz = EXCLUDED.pub_date_tz,
                image_url = EXCLUDED.image_url,
                video_url = EXCLUDED.video_url,
                source_id = EXCLUDED.source_id,
                source_name = EXCLUDED.source_name,
                source_priority = EXCLUDED.source_priority,
                source_url = EXCLUDED.source_url,
                source_icon = EXCLUDED.source_icon,
                language = EXCLUDED.language,
                country = EXCLUDED.country,
                category = EXCLUDED.category,
                sentiment = EXCLUDED.sentiment,
                sentiment_stats = EXCLUDED.sentiment_stats,
                ai_tag = EXCLUDED.ai_tag,
                ai_region = EXCLUDED.ai_region,
                ai_org = EXCLUDED.ai_org,
                ai_summary = EXCLUDED.ai_summary,
                ai_content = EXCLUDED.ai_content,
                duplicate = EXCLUDED.duplicate
        """
        execute_values(cur, insert_sql, values)
        conn.commit()
        logger.info(f"Stored {len(articles)} articles in database")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error storing articles: {e}")
        raise
    finally:
        cur.close()
        conn.close()
        tunnel.stop()

def get_cached_articles(params):
    """Get articles from the database using filters (no cache logic)"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        news = Table('news_articles')
        q = Query.from_(news).select('*')
        # Apply filters based on params
        if 'language' in params:
            q = q.where(news.language == params['language'])
        if 'country' in params:
            q = q.where(news.country == params['country'])
        if 'category' in params:
            q = q.where(news.category == params['category'])
        if 'keywords' in params:
            q = q.where(news.keywords == params['keywords'])
        if 'size' in params:
            q = q.limit(int(params['size']))
        # Order by publication date (newest first)
        q = q.orderby(news.pub_date, order=Order.desc)
        sql = q.get_sql()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        articles = []
        for row in cur.fetchall():
            article = dict(zip(columns, row))
            # Convert datetime to string for JSON serialization
            if article.get('pub_date'):
                article['pub_date'] = article['pub_date'].isoformat()
            if article.get('created_at'):
                article['created_at'] = article['created_at'].isoformat()
            if article.get('updated_at'):
                article['updated_at'] = article['updated_at'].isoformat()
            articles.append(article)
        logger.info(f"Retrieved {len(articles)} articles from database with filters")
        return articles
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return None, None
    finally:
        cur.close()
        conn.close()

def get_cached_articles_enhanced(params):
    """
    Enhanced version of get_cached_articles that uses type-aware filtering and search capabilities.
    This function uses the utility function from db_query_utils for advanced query building.
    """
    try:
        articles = get_cached_articles_by_type(params)
        if articles is None:
            logger.error("Failed to retrieve articles using enhanced method")
            return None
        logger.info(f"Enhanced query retrieved {len(articles)} articles")
        return articles
    except Exception as e:
        logger.error(f"Error in enhanced get_cached_articles: {e}")
        return None

def get_news(params_array):
    """Legacy function - kept for backward compatibility"""
    # Use PyPika to build a query
    news = Table('news_articles')
    q = Query.from_(news).select('*')
    if len(params_array) > 0:
        # params_array should be a list of (column, value) tuples
        for col, val in params_array:
            q = q.where(getattr(news, col) == val)
    sql = q.get_sql()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    news_rows = cur.fetchall()
    cur.close()
    conn.close()
    return news_rows

def cleanup_old_articles(days_to_keep=7):
    """Remove articles older than specified days using PyPika for DELETE query"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        # Use PyPika to build the DELETE query
        news = Table('news_articles')
        q = Query.from_(news).delete().where(news.pub_date < cutoff_date)
        sql = q.get_sql()
        cur.execute(sql)
        deleted_count = cur.rowcount
        conn.commit()
        logger.info(f"Cleaned up {deleted_count} old articles")
        return deleted_count
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning up old articles: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_database_stats():
    """Get database statistics"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM news_articles")
        total_articles = cur.fetchone()[0]
        
        cur.execute("SELECT MIN(pub_date), MAX(pub_date) FROM news_articles")
        date_range = cur.fetchone()
        
        return {
            'total_articles': total_articles,
            'date_range': {
                'oldest': date_range[0].isoformat() if date_range[0] else None,
                'newest': date_range[1].isoformat() if date_range[1] else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return None
    finally:
        cur.close()
        conn.close() 

def get_cached_articles_by_type2(params):
    """
    Get articles from the database using filters, building where conditions according to the column_types dict.
    Uses '&&' for array columns (TEXT[]), and direct equality for others.
    Only columns present in both params and the type dict are handled, and only if the value is a non-empty string or non-empty list/tuple.
    """
    conn, tunnel = get_connection()
    cur = conn.cursor()
    print(params)
    try:
        news = Table('news_articles')
        q = Query.from_(news).select('*')
        array_where_clauses = []
        array_values = []
        # Loop through params and add where clauses based on type
        for col, val in params.items():
            print()
            if col in column_types:
                print(col)
                col_type = column_types[col]
                if col_type == "text_array":
                    # Use '&&' for array overlap
                    print(col_type)
                    if not isinstance(val, list):
                        val = [val]
                    # Use ANY() approach instead of && for better compatibility
                    array_where_clauses.append(f"'{{{','.join(val)}}}' && {col}")
                    # Don't add to array_values since we're embedding the values directly
                elif col_type in ("varchar", "text"):
                    q = q.where(getattr(news, col) == val)
                elif col_type == "bigint":
                    q = q.where(getattr(news, col) == int(val))
                elif col_type == "boolean":
                    if isinstance(val, str):
                        val = val.lower() == 'true'
                    q = q.where(getattr(news, col) == val)
            else:
                print(col, val)
                # Handle timeframe parameter using PostgreSQL timezone functions
                if 'timeframe' in params and is_valid_param(params['timeframe']):
                    try:
                        timeframe_minutes = int(params['timeframe'])
                        # Use PostgreSQL timezone conversion in the WHERE clause
                        timeframe_condition = f"pub_date >= NOW() AT TIME ZONE pub_date_tz - INTERVAL '{timeframe_minutes} minutes'"
                        array_where_clauses.append(timeframe_condition)
                        logger.info(f"Applied timeframe filter: articles from last {timeframe_minutes} minutes using PostgreSQL timezone conversion")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid timeframe value: {params['timeframe']}, ignoring timeframe filter. Error: {e}")
                # Check if this param is a search parameter from search_params_mapping
                if col in search_params_mapping:
                    search_columns = search_params_mapping[col]
                    # Create OR conditions for searching across multiple columns
                    search_conditions = []
                    array_search_conditions = []
                    for search_col in search_columns:
                        if search_col in column_types:
                            # Use ILIKE for case-insensitive substring search
                            col_type = column_types[search_col]
                            if col_type == "text_array":
                                # For text_array columns, use ANY() operator for substring search
                                array_search_conditions.append(f"ANY({search_col}) ILIKE '%{val}%'")
                            else:
                                # For varchar/text columns, use regular PyPika ILIKE
                                search_conditions.append(getattr(news, search_col).ilike(f"%{val}%"))
                        
   
                    if search_conditions:
                        condition = search_conditions[0]
                        for c in search_conditions[1:]:
                            condition |= c  # logical OR chaining
                        q = q.where(condition)

                    if array_search_conditions:
        # Handle array conditions separately
                        array_where_clauses.extend(array_search_conditions)

        # Limit if size param
        # q = q.orderby(news.pub_date, order=Order.desc)
        sql = q.get_sql()
        print(sql)
        # If there are array filters, append them to the WHERE clause
        print(array_where_clauses)
        if array_where_clauses:
            if 'WHERE' in sql:
                sql += ' AND ' + ' AND '.join(array_where_clauses)
            else:
                sql += ' WHERE ' + ' AND '.join(array_where_clauses)
        
        # q = q.orderby(news.pub_date, order=Order.desc)
        # sql = q.get_sql()
        # print(sql)
        print(array_values)
        print("SQL:", sql)
        print("Params:", array_values)
        print("Placeholder count:", sql.count('%s'))
        print("Param count:", len(array_values))

        # Execute query - array_values should be empty now since arrays are embedded
        cur.execute(sql, array_values)
        columns = [desc[0] for desc in cur.description]
        articles = []
        for row in cur.fetchall():
            article = dict(zip(columns, row))
            for tcol in [k for k, v in column_types.items() if v == 'timestamp']:
                if article.get(tcol) and hasattr(article[tcol], 'isoformat'):
                    article[tcol] = article[tcol].isoformat()
            articles.append(article)
        logger.info(f"Retrieved {len(articles)} articles from database with filters by type (&& for arrays, dict-driven)")
        return articles
    except Exception as e:
        logger.error(f"Error getting articles by type: {e}")
        return None
    finally:
        cur.close()
        if tunnel:
            tunnel.close()
        conn.close()
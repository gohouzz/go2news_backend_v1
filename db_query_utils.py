import psycopg2
from pypika import Query, Table
from pypika.terms import OrCriterion
from datetime import datetime
import logging
from go2news_backend_v1.db import get_connection

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

logger = logging.getLogger(__name__)

def is_valid_param(val):
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip() != ''
    if isinstance(val, (list, tuple)):
        return len(val) > 0
    return True

def get_cached_articles_by_type2(params):
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
                elif col_type == "boolean":
                    if isinstance(val, str):
                        val = val.lower() == 'true'
                    q = q.where(getattr(news, col) == val)
            else:

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
                    for search_col in search_columns:
                        if search_col in column_types:
                            # Use ILIKE for case-insensitive substring search
                            search_conditions.append(getattr(news, search_col).ilike(f"%{val}%"))
                    
                    if search_conditions:
                        # Combine all search conditions with OR
                        combined_condition = OrCriterion(*search_conditions)
                        q = q.where(combined_condition)
        # Limit if size param
        q = q.orderby(news.pub_date, order=Query.desc)
        sql = q.get_sql()
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
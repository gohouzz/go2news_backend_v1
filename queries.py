from database import db
from models import NewsArticle
from sqlalchemy import desc, and_, or_, func
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timedelta

class NewsQueries:
    """Database queries for news operations using PostgreSQL arrays"""
    
    @staticmethod
    def get_articles_with_advanced_filters(
        # Direct column filters
        id=None,                    # Maps to article_id
        country=None,               # Direct column filter
        category=None,              # Direct column filter (array)
        language=None,              # Direct column filter
        sentiment=None,             # Direct column filter
        tag=None,                   # Direct column filter
        
        # Search filters
        q=None,                     # Search across multiple columns
        qInTitle=None,              # Search in title only
        qInMeta=None,               # Search in meta fields
        
        # Other parameters
        timeframe=None,             # Time-based filtering
        limit=50,
        sort_by='pub_date',
        sort_order='desc'
    ):
        """Advanced filter method with search parameter mappings"""
        query = NewsArticle.query
        
        # Direct column filters
        if id:
            query = query.filter(NewsArticle.article_id == id)
        
        if country:
            query = query.filter(NewsArticle.country.any(country))
        
        if category:
            query = query.filter(NewsArticle.category.any(category))
        
        if language:
            query = query.filter(NewsArticle.language == language)
        
        if sentiment:
            query = query.filter(NewsArticle.sentiment == sentiment)
        
        if tag:
            query = query.filter(NewsArticle.ai_tag.any(tag))
        
        # Search parameter mappings
        search_mappings = {
            "q": ["title", "link", "keywords", "image_url", "description", "content", "ai_tag", "ai_summary", "ai_content", "category", "ai_region", "sentiment"],
            "qInTitle": ["title"],
            "qInMeta": ["title", "link", "keywords", "description", "tag"]
        }
        
        # Handle each search parameter
        for search_param, columns in search_mappings.items():
            search_value = locals().get(search_param)
            if search_value:
                search_pattern = f'%{search_value}%'
                search_conditions = []
                
                for column in columns:
                    if column == "title":
                        search_conditions.append(NewsArticle.title.ilike(search_pattern))
                    elif column == "link":
                        search_conditions.append(NewsArticle.link.ilike(search_pattern))
                    elif column == "keywords":
                        # Search within array elements
                        search_conditions.append(
                            func.exists(
                                func.select(1).select_from(
                                    func.unnest(NewsArticle.keywords)
                                ).where(func.unnest(NewsArticle.keywords).ilike(search_pattern))
                            )
                        )
                    elif column == "image_url":
                        search_conditions.append(NewsArticle.image_url.ilike(search_pattern))
                    elif column == "description":
                        search_conditions.append(NewsArticle.description.ilike(search_pattern))
                    elif column == "content":
                        search_conditions.append(NewsArticle.content.ilike(search_pattern))
                    elif column == "ai_tag":
                        # Search within array elements
                        search_conditions.append(
                            func.exists(
                                func.select(1).select_from(
                                    func.unnest(NewsArticle.ai_tag)
                                ).where(func.unnest(NewsArticle.ai_tag).ilike(search_pattern))
                            )
                        )
                    elif column == "ai_summary":
                        search_conditions.append(NewsArticle.ai_summary.ilike(search_pattern))
                    elif column == "ai_content":
                        search_conditions.append(NewsArticle.ai_content.ilike(search_pattern))
                    elif column == "category":
                        # Search within array elements
                        search_conditions.append(
                            func.exists(
                                func.select(1).select_from(
                                    func.unnest(NewsArticle.category)
                                ).where(func.unnest(NewsArticle.category).ilike(search_pattern))
                            )
                        )
                    elif column == "ai_region":
                        search_conditions.append(NewsArticle.ai_region.ilike(search_pattern))
                    elif column == "sentiment":
                        search_conditions.append(NewsArticle.sentiment.ilike(search_pattern))
                    elif column == "tag":
                        # Search within ai_tag array elements
                        search_conditions.append(
                            func.exists(
                                func.select(1).select_from(
                                    func.unnest(NewsArticle.ai_tag)
                                ).where(func.unnest(NewsArticle.ai_tag).ilike(search_pattern))
                            )
                        )
                
                # Combine all search conditions with OR
                if search_conditions:
                    query = query.filter(or_(*search_conditions))
        
        # Handle timeframe filter
        if timeframe:
            now = datetime.utcnow()
            if timeframe == '15m':
                start_time = now - timedelta(minutes=15)
            elif timeframe == '1h':
                start_time = now - timedelta(hours=1)
            elif timeframe == '1d':
                start_time = now - timedelta(days=1)
            elif timeframe == '1w':
                start_time = now - timedelta(weeks=1)
            elif timeframe == '1m':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)  # Default to 1 day
            
            query = query.filter(NewsArticle.pub_date >= start_time)
        
        # Apply sorting
        if sort_by == 'pub_date':
            if sort_order == 'desc':
                query = query.order_by(desc(NewsArticle.pub_date))
            else:
                query = query.order_by(NewsArticle.pub_date)
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_latest_news(limit=50, language='en', country_filter=None, category_filter=None):
        """Get latest news articles with array filtering"""
        query = NewsArticle.query.filter(
            NewsArticle.language == language
        )
        
        # Filter by country (array overlap)
        if country_filter:
            query = query.filter(NewsArticle.country.any(country_filter))
        
        # Filter by category (array overlap)
        if category_filter:
            query = query.filter(NewsArticle.category.any(category_filter))
        
        return query.order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_countries(countries, limit=20):
        """Get news from specific countries using array operations"""
        return NewsArticle.query.filter(
            NewsArticle.country.any(lambda x: x in countries)
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_categories(categories, limit=20):
        """Get news by categories using array operations"""
        return NewsArticle.query.filter(
            NewsArticle.category.any(lambda x: x in categories)
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def search_news_by_keywords(keywords, limit=20):
        """Search news by keywords using array operations"""
        return NewsArticle.query.filter(
            NewsArticle.keywords.any(lambda x: x in keywords)
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_ai_tags(ai_tags, limit=20):
        """Get news by AI tags using array operations"""
        return NewsArticle.query.filter(
            NewsArticle.ai_tag.any(lambda x: x in ai_tags)
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_sentiment(sentiment, limit=20):
        """Get news by sentiment (positive, negative, neutral)"""
        return NewsArticle.query.filter(
            NewsArticle.sentiment == sentiment
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_sentiment_range(min_positive=0, max_negative=100, limit=20):
        """Get news by sentiment statistics range"""
        return NewsArticle.query.filter(
            and_(
                NewsArticle.sentiment_stats['positive'].astext.cast(db.Float) >= min_positive,
                NewsArticle.sentiment_stats['negative'].astext.cast(db.Float) <= max_negative
            )
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_news_by_date_range(start_date, end_date, language='en', countries=None):
        """Get news within a date range with country filtering"""
        query = NewsArticle.query.filter(
            and_(
                NewsArticle.pub_date >= start_date,
                NewsArticle.pub_date <= end_date,
                NewsArticle.language == language
            )
        )
        
        if countries:
            query = query.filter(NewsArticle.country.any(lambda x: x in countries))
        
        return query.order_by(desc(NewsArticle.pub_date)).all()
    
    @staticmethod
    def search_news_text(search_term, language='en', limit=20):
        """Search news by title and content with array filtering"""
        search_pattern = f'%{search_term}%'
        return NewsArticle.query.filter(
            and_(
                or_(
                    NewsArticle.title.ilike(search_pattern),
                    NewsArticle.content.ilike(search_pattern),
                    NewsArticle.description.ilike(search_pattern)
                ),
                NewsArticle.language == language
            )
        ).order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_trending_news(days=7, limit=10, countries=None):
        """Get trending news from the last N days with country filtering"""
        start_date = datetime.utcnow() - timedelta(days=days)
        query = NewsArticle.query.filter(
            NewsArticle.pub_date >= start_date
        )
        
        if countries:
            query = query.filter(NewsArticle.country.any(lambda x: x in countries))
        
        return query.order_by(desc(NewsArticle.pub_date)).limit(limit).all()
    
    @staticmethod
    def get_popular_countries(limit=10):
        """Get most popular countries from articles"""
        return db.session.query(
            func.unnest(NewsArticle.country).label('country'),
            func.count().label('count')
        ).group_by('country').order_by(desc('count')).limit(limit).all()
    
    @staticmethod
    def get_popular_categories(limit=10):
        """Get most popular categories from articles"""
        return db.session.query(
            func.unnest(NewsArticle.category).label('category'),
            func.count().label('count')
        ).group_by('category').order_by(desc('count')).limit(limit).all()
    
    @staticmethod
    def get_popular_keywords(limit=20):
        """Get most popular keywords from articles"""
        return db.session.query(
            func.unnest(NewsArticle.keywords).label('keyword'),
            func.count().label('count')
        ).group_by('keyword').order_by(desc('count')).limit(limit).all()
    
    @staticmethod
    def get_popular_ai_tags(limit=20):
        """Get most popular AI tags from articles"""
        return db.session.query(
            func.unnest(NewsArticle.ai_tag).label('ai_tag'),
            func.count().label('count')
        ).group_by('ai_tag').order_by(desc('count')).limit(limit).all()
    
    @staticmethod
    def get_popular_creators(limit=20):
        """Get most popular creators from articles"""
        return db.session.query(
            func.unnest(NewsArticle.creator).label('creator'),
            func.count().label('count')
        ).group_by('creator').order_by(desc('count')).limit(limit).all()
    
    @staticmethod
    def get_sentiment_analysis():
        """Get sentiment analysis statistics"""
        return db.session.query(
            NewsArticle.sentiment,
            func.count().label('count')
        ).group_by(NewsArticle.sentiment).all()
    
    @staticmethod
    def save_article(article_data):
        """Save a new article to database"""
        try:
            # Check if article already exists
            existing = NewsArticle.query.filter_by(article_id=article_data['article_id']).first()
            if existing:
                return existing
            
            # Create new article using the helper method
            article = NewsArticle.from_api_data(article_data)
            db.session.add(article)
            db.session.commit()
            return article
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def bulk_save_articles(articles_data):
        """Save multiple articles at once"""
        try:
            saved_articles = []
            for article_data in articles_data:
                # Check if article already exists
                existing = NewsArticle.query.filter_by(article_id=article_data['article_id']).first()
                if not existing:
                    article = NewsArticle.from_api_data(article_data)
                    db.session.add(article)
                    saved_articles.append(article)
            
            db.session.commit()
            return saved_articles
        except Exception as e:
            db.session.rollback()
            raise e 
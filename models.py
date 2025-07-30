from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy import Text

class NewsArticle(db.Model):
    """Model for storing news articles from NewsData API"""
    __tablename__ = 'news_articles'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Article identification
    article_id = db.Column(db.String(100), unique=True, nullable=False)
    
    # Basic article information
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    link = db.Column(db.String(1000), unique=True)
    
    # Media (can be null)
    image_url = db.Column(db.String(1000), nullable=True)
    video_url = db.Column(db.String(1000), nullable=True)
    
    # Publication details
    pub_date = db.Column(db.DateTime)
    pub_date_tz = db.Column(db.String(50))
    
    # Source information
    source_id = db.Column(db.String(100))
    source_name = db.Column(db.String(200))
    source_priority = db.Column(db.Integer)
    source_url = db.Column(db.String(500))
    source_icon = db.Column(db.String(500))
    
    # Localization - PostgreSQL ARRAYS for better performance
    language = db.Column(db.String(20), default='en')
    country = db.Column(db.ARRAY(db.String))  # PostgreSQL array
    category = db.Column(db.ARRAY(db.String))  # PostgreSQL array
    keywords = db.Column(db.ARRAY(db.String))  # PostgreSQL array
    creator = db.Column(db.ARRAY(db.String))  # PostgreSQL array
    
    # Categorization
    sentiment = db.Column(db.String(20))  # positive, negative, neutral
    sentiment_stats = db.Column(db.JSON)  # JSON object with sentiment percentages
    
    # AI features - PostgreSQL ARRAYS for better performance
    ai_tag = db.Column(db.ARRAY(db.String))  # PostgreSQL array
    ai_region = db.Column(db.Text)
    ai_org = db.Column(db.Text)
    ai_summary = db.Column(db.Text)
    ai_content = db.Column(db.Text)
    
    # Metadata
    duplicate = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def from_api_data(cls, api_data):
        """Create NewsArticle from API response data"""
        # Convert API arrays to PostgreSQL arrays (no JSON conversion needed)
        countries = api_data.get('country', []) if api_data.get('country') else []
        categories = api_data.get('category', []) if api_data.get('category') else []
        keywords = api_data.get('keywords', []) if api_data.get('keywords') else []
        creators = api_data.get('creator', []) if api_data.get('creator') else []
        ai_tags = api_data.get('ai_tag', []) if api_data.get('ai_tag') else []
        
        # Parse pubDate string to datetime
        pub_date = None
        if api_data.get('pubDate'):
            try:
                from datetime import datetime
                pub_date = datetime.fromisoformat(api_data['pubDate'].replace('Z', '+00:00'))
            except:
                pub_date = None
        
        return cls(
            article_id=api_data.get('article_id'),
            title=api_data.get('title'),
            description=api_data.get('description'),
            content=api_data.get('content'),
            link=api_data.get('link'),
            image_url=api_data.get('image_url'),
            video_url=api_data.get('video_url'),
            pub_date=pub_date,
            pub_date_tz=api_data.get('pubDateTZ'),
            source_id=api_data.get('source_id'),
            source_name=api_data.get('source_name'),
            source_priority=api_data.get('source_priority'),
            source_url=api_data.get('source_url'),
            source_icon=api_data.get('source_icon'),
            language=api_data.get('language'),
            country=countries,  # Direct array assignment
            category=categories,  # Direct array assignment
            keywords=keywords,  # Direct array assignment
            creator=creators,  # Direct array assignment
            sentiment=api_data.get('sentiment'),
            sentiment_stats=api_data.get('sentiment_stats'),  # JSON object
            ai_tag=ai_tags,  # Direct array assignment
            ai_region=api_data.get('ai_region'),
            ai_org=api_data.get('ai_org'),
            ai_summary=api_data.get('ai_summary'),
            ai_content=api_data.get('ai_content'),
            duplicate=api_data.get('duplicate', False)
        )
    
    def to_dict(self):
        """Convert model to dictionary matching API response format"""
        # PostgreSQL arrays are already in the correct format
        return {
            'article_id': self.article_id,
            'title': self.title,
            'link': self.link,
            'keywords': self.keywords or [],  # Return as array
            'creator': self.creator or [],  # Return as array
            'description': self.description,
            'content': self.content,
            'pubDate': self.pub_date.isoformat() if self.pub_date else None,
            'pubDateTZ': self.pub_date_tz,
            'image_url': self.image_url,
            'video_url': self.video_url,
            'source_id': self.source_id,
            'source_name': self.source_name,
            'source_priority': self.source_priority,
            'source_url': self.source_url,
            'source_icon': self.source_icon,
            'language': self.language,
            'country': self.country or [],  # Return as array
            'category': self.category or [],  # Return as array
            'sentiment': self.sentiment,
            'sentiment_stats': self.sentiment_stats,  # JSON object
            'ai_tag': self.ai_tag or [],  # Return as array
            'ai_region': self.ai_region,
            'ai_org': self.ai_org,
            'ai_summary': self.ai_summary,
            'ai_content': self.ai_content,
            'duplicate': self.duplicate,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<NewsArticle {self.article_id}: {self.title[:50]}...>' 
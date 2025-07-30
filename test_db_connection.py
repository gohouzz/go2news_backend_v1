#!/usr/bin/env python3
"""
Test SSH tunnel and database connection
"""
from secure_db import db_manager
from queries import NewsQueries

def test_connection():
    """Test SSH tunnel and database connection"""
    print("🔍 Testing SSH tunnel and database connection...")
    
    try:
        with db_manager.get_connection() as db:
            print("✅ SSH tunnel established successfully")
            print("✅ Database connection successful")
            
            # Test a simple query
            articles = NewsQueries.get_latest_news(limit=1)
            print(f"✅ Database query successful - Found {len(articles)} articles")
            
            if articles:
                print(f"📰 Latest article: {articles[0].title[:50]}...")
                print(f"📅 Latest pub_date: {articles[0].pub_date}")
            else:
                print("📝 No articles in database yet")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_connection() 
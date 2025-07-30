#!/usr/bin/env python3
"""
Automated Article Collection Scheduler
Fetches articles from external API and saves to database every 5 minutes
"""
import requests
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from secure_db import db_manager
from queries import NewsQueries
from newsdataapi import NewsDataApiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag to prevent multiple scheduler instances
_scheduler_started = False

class ArticleFetcher:
    """Handles fetching and saving articles from external API"""
    
    def __init__(self):
        self.api_key = 'pub_3afa0cea798346df9bcc900ecfe5fe20'
        self.api_client = NewsDataApiClient(apikey=self.api_key)
        
        # Countries to fetch articles from
        self.countries = ['in']
    
    def get_latest_article_time(self):
        """Get the latest pub_date time from database"""
        try:
            with db_manager.get_connection() as db:
                # Get the most recent article's pub_date time
                latest_article = NewsQueries.get_latest_news(limit=1)
                if latest_article:
                    return latest_article[0].pub_date
                else:
                    # If no articles in database, return None
                    return None
        except Exception as e:
            logger.error(f"Error getting latest article time: {e}")
            return None
    
    def fetch_articles_from_api(self, country, from_date, to_date):
        """Fetch articles from external API using NewsDataApiClient with scroll=True"""
        try:
            # Format dates for API
            from_date_str = from_date.strftime('%Y-%m-%d %H:%M:%S')
            to_date_str = to_date.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Fetching articles for {country} from {from_date_str} to {to_date_str}")
            
            # Use NewsDataApiClient archive API for time-based fetching
            response = self.api_client.archive_api(
                country=country,
                from_date=from_date_str,
                to_date=to_date_str,
                scroll=True
            )
            
            if response and hasattr(response, 'results') and response.results:
                logger.info(f"Fetched {len(response.results)} articles for {country}")
                return response.results
            else:
                logger.warning(f"No articles found for {country}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching articles for {country}: {e}")
            return []
    
    def save_articles_to_database(self, articles):
        """Save articles to database using secure connection"""
        try:
            with db_manager.get_connection() as db:
                saved_articles = NewsQueries.bulk_save_articles(articles)
                logger.info(f"Saved {len(saved_articles)} new articles to database")
                return len(saved_articles)
        except Exception as e:
            logger.error(f"Error saving articles to database: {e}")
            return 0
    
    def fetch_and_save_articles(self):
        """Main task: Fetch articles using time-based parameters and save to database"""
        logger.info("Starting scheduled article fetch and save task")
        total_fetched = 0
        total_saved = 0
        
        # Get current time (use UTC to match API requirements)
        current_time = datetime.now(timezone.utc)
        
        # Get the latest article pub_date from database
        latest_time = self.get_latest_article_time()
        
        if latest_time:
            # Use the latest article pub_date as from_date
            from_date = latest_time
            logger.info(f"Using latest article pub_date as from_date: {from_date}")
        else:
            # If no articles in database, fetch last 20 minutes
            from_date = current_time - timedelta(minutes=20)
            logger.info(f"No articles in database, fetching last 20 minutes from: {from_date}")
        
        # Use a time in the past to avoid future date issues
        to_date = current_time - timedelta(minutes=1)  # 1 minute ago
        logger.info(f"Fetching articles from {from_date} to {to_date}")
        
        for country in self.countries:
            try:
                # Fetch articles from API using time range
                articles = self.fetch_articles_from_api(country, from_date, to_date)
                
                if articles:
                    total_fetched += len(articles)
                    # Save to database
                    saved_count = self.save_articles_to_database(articles)
                    total_saved += saved_count
                    
                    logger.info(f"Country {country}: Fetched {len(articles)}, Saved {saved_count}")
                
            except Exception as e:
                logger.error(f"Error processing country {country}: {e}")
        
        logger.info(f"Task completed: Total fetched={total_fetched}, Total saved={total_saved}")
        return {'fetched': total_fetched, 'saved': total_saved}

class SchedulerManager:
    """Manages the background scheduler"""
    
    def __init__(self):
        self.scheduler = None
        self.article_fetcher = ArticleFetcher()
    
    def start_scheduler(self):
        """Start the background scheduler"""
        try:
            self.scheduler = BackgroundScheduler()
            
            # Add job to fetch articles every 5 minutes
            self.scheduler.add_job(
                func=self.article_fetcher.fetch_and_save_articles,
                trigger=IntervalTrigger(minutes=5),
                id='article_fetcher',
                name='Fetch articles every 5 minutes',
                max_instances=1,  # Prevent overlapping jobs
                coalesce=True      # Combine missed executions
            )
            
            # Add event listeners for monitoring
            self.scheduler.add_listener(self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
            
            # Start the scheduler
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Run initial fetch immediately
            self.scheduler.add_job(
                func=self.article_fetcher.fetch_and_save_articles,
                trigger='date',
                id='initial_fetch',
                name='Initial article fetch'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def job_listener(self, event):
        """Listen to job events for monitoring"""
        if event.exception:
            logger.error(f"Job {event.job_id} raised an exception: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} executed successfully")
    
    def get_scheduler_status(self):
        """Get current scheduler status"""
        if not self.scheduler:
            return {'status': 'not_started'}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else None
            })
        
        return {
            'status': 'running',
            'jobs': jobs
        }

# Global scheduler instance
scheduler_manager = SchedulerManager()

def start_article_scheduler():
    """Start the article collection scheduler"""
    global _scheduler_started
    
    if _scheduler_started:
        logger.warning("Scheduler already started, skipping...")
        return True
    
    success = scheduler_manager.start_scheduler()
    if success:
        _scheduler_started = True
    return success

def stop_article_scheduler():
    """Stop the article collection scheduler"""
    scheduler_manager.stop_scheduler()

def get_scheduler_status():
    """Get scheduler status"""
    return scheduler_manager.get_scheduler_status()

if __name__ == "__main__":
    # Test the scheduler
    print("Starting article scheduler...")
    if start_article_scheduler():
        print("Scheduler started successfully!")
        print("Press Ctrl+C to stop...")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_article_scheduler()
            print("Scheduler stopped.")
    else:
        print("Failed to start scheduler.") 
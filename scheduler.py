import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from fetch_and_update_news import main as fetch_and_update_news_main

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

if __name__ == "__main__":
    logging.info("Starting news fetch scheduler (every 5 minutes)...")
    scheduler = BlockingScheduler()
    scheduler.add_job(fetch_and_update_news_main, 'interval', minutes=5)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
    except Exception as e:
        logging.error(f"Scheduler error: {e}")

# Note: Add 'APScheduler' to your requirements.txt 
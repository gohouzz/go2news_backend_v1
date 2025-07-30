#!/usr/bin/env python3
"""
Test script for the article collection scheduler
"""
import time
from scheduler import get_scheduler_status, start_article_scheduler, stop_article_scheduler

def test_scheduler():
    """Test the scheduler functionality"""
    print("🔄 Testing scheduler...")
    
    # Check initial status
    status = get_scheduler_status()
    print(f"Initial status: {status}")
    
    # Start scheduler
    print("🔄 Starting scheduler...")
    success = start_article_scheduler()
    print(f"Scheduler start: {'✅ Success' if success else '❌ Failed'}")
    
    # Check status after start
    time.sleep(2)
    status = get_scheduler_status()
    print(f"Status after start: {status}")
    
    # Wait a bit to see if jobs run
    print("⏳ Waiting 10 seconds to see scheduler activity...")
    time.sleep(10)
    
    # Stop scheduler
    print("🔄 Stopping scheduler...")
    stop_article_scheduler()
    
    # Final status
    status = get_scheduler_status()
    print(f"Final status: {status}")
    print("✅ Scheduler test completed!")

if __name__ == "__main__":
    test_scheduler() 
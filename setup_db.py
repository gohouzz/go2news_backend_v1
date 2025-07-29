#!/usr/bin/env python3
"""
Simple database setup script for Go2News backend
"""

from db import create_tables, get_connection
import sys

def main():
    print("🚀 Setting up Go2News database...")
    
    try:
        # Test database connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        print(f"✅ Database connection successful!")
        print(f"   PostgreSQL version: {version[0]}")
        
        # Create tables
        create_tables()
        print("✅ Database tables created successfully!")
        
        print("\n🎉 Setup complete! You can now run the application.")
        print("   Run: python app.py")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("\n📝 Troubleshooting:")
        print("   1. Check your database credentials in db.py")
        print("   2. Ensure PostgreSQL is running")
        print("   3. Verify network connectivity to your database")
        sys.exit(1)

if __name__ == "__main__":
    main() 
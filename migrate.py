#!/usr/bin/env python3
"""
Database Migration Runner
Runs migrations through secure SSH tunnel
"""
import os
import subprocess
from sshtunnel import SSHTunnelForwarder

def run_migrations():
    """Run database migrations through secure SSH tunnel"""
    try:
        # Start SSH tunnel
        tunnel = SSHTunnelForwarder(
            ('ec2-3-80-189-208.compute-1.amazonaws.com', 22),
            ssh_username='ubuntu',
            ssh_pkey='/Users/saitejareddygutpe/Downloads/dubaiedeals.pem',
            remote_bind_address=('database-1.cw3egoy2c577.us-east-1.rds.amazonaws.com', 5432),
            local_bind_address=('127.0.0.1', 5432)
        )
        
        print("🔄 Starting SSH tunnel...")
        tunnel.start()
        print(f"✅ SSH tunnel established: {tunnel.local_bind_host}:{tunnel.local_bind_port}")
        
        # Set database URL
        os.environ['DATABASE_URL'] = 'postgresql://postgres:GoHouzz2025@127.0.0.1:5432/go2news'
        
        print("🔄 Running database migrations...")
        result = subprocess.run(['flask', 'db', 'upgrade'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database migrations completed successfully!")
        else:
            print("❌ Database migrations failed!")
            print(result.stderr)
        
        tunnel.stop()
        print("🔌 SSH tunnel stopped")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migrations() 
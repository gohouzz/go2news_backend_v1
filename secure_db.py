#!/usr/bin/env python3
"""
Secure Database Connection Manager
Uses SSH tunnel to connect to RDS through EC2
"""
import os
import time
from contextlib import contextmanager
from sshtunnel import SSHTunnelForwarder
from database import db

class SecureDatabaseManager:
    def __init__(self):
        # SSH Tunnel Configuration
        self.ssh_config = {
            'ssh_host': 'ec2-3-80-189-208.compute-1.amazonaws.com',
            'ssh_username': 'ubuntu',
            'ssh_pkey': '/Users/saitejareddygutpe/Downloads/dubaiedeals.pem',
            'remote_bind_host': 'database-1.cw3egoy2c577.us-east-1.rds.amazonaws.com',
            'remote_bind_port': 5432,
            'local_bind_host': '127.0.0.1',
            'local_bind_port': 5433  # Use different port to avoid conflicts
        }
        
        # Database Configuration
        self.db_config = {
            'host': '127.0.0.1',
            'port': 5433,  # Match the tunnel port
            'database': 'go2news',
            'username': 'postgres',
            'password': 'GoHouzz2025'
        }
        
        self.tunnel = None
        self.is_connected = False
    
    def start_tunnel(self):
        """Start SSH tunnel"""
        try:
            self.tunnel = SSHTunnelForwarder(
                (self.ssh_config['ssh_host'], 22),
                ssh_username=self.ssh_config['ssh_username'],
                ssh_pkey=self.ssh_config['ssh_pkey'],
                remote_bind_address=(self.ssh_config['remote_bind_host'], self.ssh_config['remote_bind_port']),
                local_bind_address=(self.ssh_config['local_bind_host'], self.ssh_config['local_bind_port'])
            )
            
            self.tunnel.start()
            self.is_connected = True
            print(f"✅ SSH tunnel established: {self.tunnel.local_bind_host}:{self.tunnel.local_bind_port}")
            return True
            
        except Exception as e:
            print(f"❌ SSH tunnel failed: {e}")
            return False
    
    def stop_tunnel(self):
        """Stop SSH tunnel"""
        if self.tunnel and self.tunnel.is_active:
            self.tunnel.stop()
            self.is_connected = False
            print("🔌 SSH tunnel stopped")
    
    def get_database_url(self):
        """Get database URL for tunneled connection"""
        if not self.is_connected:
            raise Exception("SSH tunnel not established")
        
        return f"postgresql://{self.db_config['username']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
    
    @contextmanager
    def get_connection(self):
        """Context manager for database operations"""
        try:
            # Start tunnel
            if not self.start_tunnel():
                raise Exception("Failed to start SSH tunnel")
            
            # Update environment
            os.environ['DATABASE_URL'] = self.get_database_url()
            
            # Create app context for database operations
            from flask import Flask
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = self.get_database_url()
            temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            
            # Initialize SQLAlchemy with the temp app
            from database import init_app
            init_app(temp_app)
            
            with temp_app.app_context():
                yield db
                
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
        finally:
            # Always stop tunnel
            self.stop_tunnel()

# Global instance
db_manager = SecureDatabaseManager()

def test_secure_connection():
    """Test the secure database connection"""
    try:
        with db_manager.get_connection() as db_session:
            # Test connection
            from sqlalchemy import text
            result = db_session.execute(text("SELECT 1"))
            print("✅ Secure database connection successful!")
            
            # Test table creation
            db.create_all()
            print("✅ Database tables created successfully!")
            
            return True
            
    except Exception as e:
        print(f"❌ Secure connection failed: {e}")
        return False

if __name__ == "__main__":
    test_secure_connection() 
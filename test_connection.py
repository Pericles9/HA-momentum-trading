"""
Quick test to check database connection
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Test connection parameters
params = {
    'host': '127.0.0.1',
    'port': '5433',
    'database': 'momentum_trading',
    'user': 'postgres',
    'password': 'password123'
}

print("Testing database connection...")
print(f"Connecting to: {params['host']}:{params['port']}/{params['database']}")

try:
    conn = psycopg2.connect(**params)
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ Connection successful!")
    print(f"PostgreSQL version: {version[0]}")
    
    # Test TimescaleDB
    cursor.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb';")
    timescale = cursor.fetchone()
    if timescale:
        print(f"✅ TimescaleDB extension is installed: {timescale[1]}")
    else:
        print("❌ TimescaleDB extension not found")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
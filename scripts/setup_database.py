#!/usr/bin/env python3
"""
Database setup script for Monero Trading Bot.

This script initializes the PostgreSQL database schema required for the bot.
Run this once before starting the bot for the first time.

Usage:
    python setup_database.py

Requirements:
    - PostgreSQL must be running
    - .env file must be configured with correct database credentials
"""

import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_connection(config):
    """Test database connection"""
    try:
        engine = create_engine(config.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return engine
    except OperationalError as e:
        logger.error(f"❌ Cannot connect to database: {e}")
        logger.error("")
        logger.error("Possible issues:")
        logger.error("1. PostgreSQL is not running")
        logger.error("2. Database credentials in .env are incorrect")
        logger.error("3. Database does not exist")
        logger.error("")
        logger.error("If using Docker:")
        logger.error("  docker-compose up -d postgres")
        logger.error("")
        logger.error("If using local PostgreSQL:")
        logger.error("  # Check if running:")
        logger.error("  pg_isready")
        logger.error("")
        logger.error("  # Create database:")
        logger.error("  psql -U postgres")
        logger.error("  CREATE DATABASE monero_trading;")
        logger.error("  CREATE USER trading_bot WITH PASSWORD 'your_password';")
        logger.error("  GRANT ALL PRIVILEGES ON DATABASE monero_trading TO trading_bot;")
        return None

def create_database_schema(engine):
    """Create all database tables"""
    try:
        from src.database.models import Base
        
        logger.info("Creating database schema...")
        Base.metadata.create_all(engine)
        logger.info("✅ Database schema created successfully")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📊 Created tables: {', '.join(tables)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error creating schema: {e}")
        return False

def verify_tables(engine):
    """Verify all required tables exist"""
    from sqlalchemy import inspect
    
    required_tables = [
        'trades',
        'positions',
        'signals',
        'market_data',
        'news_events',
        'news_sentiment'
    ]
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    logger.info("\nVerifying tables...")
    all_present = True
    for table in required_tables:
        if table in existing_tables:
            logger.info(f"  ✅ {table}")
        else:
            logger.warning(f"  ❌ {table} - MISSING!")
            all_present = False
    
    return all_present

def main():
    """Main setup function"""
    logger.info("=" * 60)
    logger.info("Monero Trading Bot - Database Setup")
    logger.info("=" * 60)
    logger.info("")
    
    # Load configuration
    try:
        from config import config
        logger.info(f"📁 Loading configuration...")
        logger.info(f"   Database: {config.db_name}")
        logger.info(f"   Host: {config.db_host}:{config.db_port}")
        logger.info(f"   User: {config.db_user}")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")
        logger.error("")
        logger.error("Make sure:")
        logger.error("1. .env file exists (copy from env.example)")
        logger.error("2. Database credentials are configured in .env")
        logger.error("")
        sys.exit(1)
    
    # Check database connection
    logger.info("🔍 Checking database connection...")
    engine = check_database_connection(config)
    if not engine:
        sys.exit(1)
    
    logger.info("")
    
    # Create schema
    if not create_database_schema(engine):
        sys.exit(1)
    
    logger.info("")
    
    # Verify all tables
    if not verify_tables(engine):
        logger.warning("\n⚠️  Some tables are missing!")
        logger.warning("This may cause issues when running the bot.")
        sys.exit(1)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Database setup complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Review your .env configuration")
    logger.info("2. Start the bot with: python run_bot.py --mode paper")
    logger.info("   or: docker-compose up -d")
    logger.info("")
    logger.info("📖 See GETTING_STARTED.md for more information")
    logger.info("")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nSetup interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ Unexpected error: {e}")
        logger.error("\nPlease report this issue with the full error message.")
        sys.exit(1)


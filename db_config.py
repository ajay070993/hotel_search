from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Database configuration
DB_HOST = 'ls-c58472822a3bb4a898de3fa2ff20dad9426ac9ab.c5g08c00ahp4.ap-south-1.rds.amazonaws.com'
DB_USERNAME = 'dbmasteruser'
DB_PASSWORD = 'sLpLxurfv!G^&Xq3?qctd%8N1EB,nD9U'
DB_NAME = 'anh_ajay_testing'

# Create database URL
DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic import BaseModel, Field

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, Integer, text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Any, List
from sqlalchemy.exc import SQLAlchemyError
import os

# MySQL Database Configuration
DB_USER = os.getenv("DB_USER", "root")  # Your MySQL username
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")  # Your MySQL password
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "startups_db")  # Your database name
DB_PORT = os.getenv("DB_PORT", "3306")

# Create MySQL connection URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine and session
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class CompanyDB(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    website = Column(String(255), nullable=False)
    tech_area = Column(String(100), index=True, nullable=False)

class CompanyInfo(BaseModel):
    name: str = Field(description='Name of the company')
    website: str = Field(description='Official website URL of the company')
    tech_area: str = Field(description='Primary technology area of the company')

def save_to_database(companies: List[CompanyInfo]) -> None:
    """Save company information to the database."""
    session = SessionLocal()
    try:
        for company in companies:
            # Check if company already exists
            existing_company = session.query(CompanyDB).filter_by(name=company.name).first()
            if not existing_company:
                db_company = CompanyDB(
                    name=company.name,
                    website=company.website,
                    tech_area=company.tech_area
                )
                session.add(db_company)
                print(f"Adding new company: {company.name}")
            else:
                print(f"Company already exists: {company.name}")
        
        session.commit()
        print("✅ Successfully saved companies to database")
    
    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
        session.rollback()
    finally:
        session.close()

def query_database():
    """Utility function to query and display all companies in the database."""
    session = SessionLocal()
    try:
        companies = session.query(CompanyDB).all()
        print("\nCompanies in database:")
        print("-" * 50)
        for company in companies:
            print(f"Name: {company.name}")
            print(f"Website: {company.website}")
            print(f"Technology Area: {company.tech_area}")
            print("-" * 50)
    except SQLAlchemyError as e:
        print(f"❌ Error querying database: {str(e)}")
    finally:
        session.close()
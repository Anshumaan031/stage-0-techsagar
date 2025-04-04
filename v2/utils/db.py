from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic import BaseModel, Field

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, Enum, TIMESTAMP, text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Any, List, Dict   
from sqlalchemy.exc import SQLAlchemyError
import os
import random
import string
from datetime import datetime

# MySQL Database Configuration
DB_USER = os.getenv("DB_USER", "root")  # Your MySQL username
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")  # Your MySQL password
DB_HOST = os.getenv("DB_HOST", "localhost")
#DB_NAME = os.getenv("DB_NAME", "startups_db")  # Your database name
DB_NAME = "ts_data_enrichment"  # Your database name
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

class CompanyProfile(Base):
    __tablename__ = "ts_entity_company_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_refid = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    about = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    contact = Column(String(50), nullable=True)
    linkedin = Column(String(255), nullable=True)
    twitter = Column(String(255), nullable=True)
    status = Column(Enum('extracted', 'screened', 'crawled', 'validated', 'capability mapped', 'ready for prod', 'production'), nullable=True)
    stage = Column(Enum('stage0', 'stage1', 'stage2', 'stage3', 'stage4'), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    created_by = Column(Integer, nullable=True)
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    updated_by = Column(Integer, nullable=True)
    deleted = Column(Boolean, default=False)

def generate_ts_refid():
    """Generate a unique reference ID in the format YY-MM-XXXX where XXXX is 4 random alphanumeric characters."""
    yy = datetime.now().strftime("%y")  # Last 2 digits of year
    mm = datetime.now().strftime("%m")  # 2 digits of month
    # Generate 4 random alphanumeric characters (uppercase letters and digits)
    last_four = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{yy}-{mm}-{last_four}"

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

def save_website_data(companies: List[Dict]) -> None:
    """Save verified company website information to the existing companies table."""
    session = SessionLocal()
    try:
        for company in companies:
            # Check if company already exists
            existing_company = session.query(CompanyDB).filter_by(name=company["name"]).first()
            
            if not existing_company:
                db_company = CompanyDB(
                    name=company["name"],
                    website=company["website"],
                    tech_area=company["tech_area"]   
                )
                session.add(db_company)
                print(f"Adding new company: {company['name']}")
            else:
                # Update website if company exists
                existing_company.website = company["website"]
                existing_company.tech_area = company["tech_area"]
                print(f"Updating company: {company['name']}")
        
        session.commit()
        print("Successfully saved company websites to database")
    
    except SQLAlchemyError as e:
        print(f"Database error: {str(e)}")
        session.rollback()
    finally:
        session.close()

def save_company_profiles(companies: List[Dict]) -> None:
    """Save company information to the ts_entity_company_profile table."""
    session = SessionLocal()
    try:
        for company in companies:
            # Check if company already exists by name
            existing_company = session.query(CompanyProfile).filter_by(name=company["name"]).first()
            
            if not existing_company:
                # Generate a unique reference ID
                ts_refid = generate_ts_refid()
                
                # Check if the generated refid already exists
                while session.query(CompanyProfile).filter_by(ts_refid=ts_refid).first():
                    ts_refid = generate_ts_refid()
                
                # Create new company profile entry
                company_profile = CompanyProfile(
                    ts_refid=ts_refid,
                    name=company["name"],
                    url=company["website"],
                    status='extracted',
                    stage='stage0',
                    created_by='1'
                )
                session.add(company_profile)
                print(f"Adding new company profile: {company['name']} with reference ID: {ts_refid}")
            else:
                # Update URL if company exists
                existing_company.url = company["website"]
                print(f"Updating existing company profile: {company['name']}")
        
        session.commit()
        print("Successfully saved company profiles to database")
    
    except SQLAlchemyError as e:
        print(f"Database error: {str(e)}")
        session.rollback()
    finally:
        session.close()


# same vesion of the previous function with mroe debugging 
# def save_company_profiles(companies: List[Dict]) -> None:
#     """
#     Save company profile information to the ts_entity_company_profile table.
    
#     Args:
#         companies: List of dictionaries containing company information with keys:
#                   'name' - Company name
#                   'website' - Company website URL
#     """
#     print(f"DEBUG: save_company_profile called with {len(companies)} companies")
#     print(f"DEBUG: Database URL: {DATABASE_URL}")
    
#     if not companies:
#         print("DEBUG: No companies to save to profile table!")
#         return
    
#     # Print sample data
#     print(f"DEBUG: Sample company data: {companies[0]}")
    
#     session = SessionLocal()
#     try:
#         for company in companies:
#             # Ensure required fields exist
#             if 'name' not in company or 'website' not in company:
#                 print(f"DEBUG: Missing required fields in company data: {company}")
#                 continue
                
#             # Debug query execution
#             print(f"DEBUG: Checking if company exists: {company['name']}")
            
#             # Check if company already exists (by name)
#             query = text("SELECT id FROM ts_entity_company_profile WHERE name = :name AND deleted = FALSE")
#             print(f"DEBUG: Executing query: {query}")
            
#             existing_company = None
#             try:
#                 existing_company = session.execute(
#                     query,
#                     {"name": company["name"]}
#                 ).fetchone()
#                 print(f"DEBUG: Query result: {existing_company}")
#             except Exception as query_error:
#                 print(f"DEBUG: Error executing existence check query: {str(query_error)}")
#                 continue
            
#             try:
#                 if not existing_company:
#                     # Generate a unique ts_refid
#                     ts_refid = generate_ts_refid()
#                     print(f"DEBUG: Generated ts_refid: {ts_refid}")
                    
#                     # Insert new company profile
#                     insert_query = text("""
#                     INSERT INTO ts_entity_company_profile 
#                     (ts_refid, name, url, status, stage, created_at, updated_at, deleted) 
#                     VALUES (:ts_refid, :name, :url, 'extracted', 'stage0', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE)
#                     """)
#                     print(f"DEBUG: Executing insert: {insert_query}")
                    
#                     session.execute(
#                         insert_query,
#                         {
#                             "ts_refid": ts_refid,
#                             "name": company["name"],
#                             "url": company["website"]
#                         }
#                     )
#                     print(f"DEBUG: Added new company profile: {company['name']} with ts_refid: {ts_refid}")
#                 else:
#                     # Update existing company website
#                     update_query = text("""
#                     UPDATE ts_entity_company_profile 
#                     SET url = :url, updated_at = CURRENT_TIMESTAMP 
#                     WHERE name = :name AND deleted = FALSE
#                     """)
#                     print(f"DEBUG: Executing update: {update_query}")
                    
#                     session.execute(
#                         update_query,
#                         {
#                             "name": company["name"],
#                             "url": company["website"]
#                         }
#                     )
#                     print(f"DEBUG: Updated existing company profile: {company['name']}")
#             except Exception as mutation_error:
#                 print(f"DEBUG: Error during {'insert' if not existing_company else 'update'}: {str(mutation_error)}")
#                 continue
        
#         print("DEBUG: Committing transaction")
#         session.commit()
#         print("✅ Successfully saved company profiles to database")
    
#     except SQLAlchemyError as e:
#         print(f"❌ Database error: {str(e)}")
#         session.rollback()
#     except Exception as general_error:
#         print(f"❌ General error: {str(general_error)}")
#         session.rollback()
#     finally:
#         print("DEBUG: Closing session")
#         session.close()
        
#     # Verify data was saved by querying the table
#     try:
#         verify_session = SessionLocal()
#         count_query = text("SELECT COUNT(*) FROM ts_entity_company_profile WHERE deleted = FALSE")
#         count_result = verify_session.execute(count_query).fetchone()
#         print(f"DEBUG: Verification - ts_entity_company_profile table has {count_result[0]} records")
#         verify_session.close()
#     except Exception as verify_error:
#         print(f"DEBUG: Error verifying data: {str(verify_error)}")
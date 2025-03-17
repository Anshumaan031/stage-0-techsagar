from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
from typing import Any, List
from datetime import date
from pathlib import Path

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, Integer, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# Setup API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# Setup Tavily Client
tavily_client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# MySQL Database Configuration
DB_USER = os.getenv("DB_USER", "root")  # Your MySQL username
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")  # Your MySQL password
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "startups_db")  # Your database name
DB_PORT = os.getenv("DB_PORT", "3306")

# Create MySQL connection URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine and session
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# Define the Company model for the database
class CompanyDB(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    website = Column(String(255), nullable=False)
    tech_area = Column(String(100), index=True, nullable=False)

# Define the technology areas
TECHNOLOGY_AREAS = [
    "AI and ML", "Application Infrastructure and Software", "Augmented and Virtual Reality",
    "Blockchain", "Cloud Computing and Virtualization", "Computer Vision", "Cryptology",
    "Cybersecurity", "Data Science", "Digital Forensics", "Enterprise Business Technologies",
    "Hardware, Semiconductors, and Embedded", "Human Computer Interaction", 
    "Identity Management and Authentication", "Internet of Things", "Location and Presence", 
    "Material Science", "Mobility and End Points", "Natural Language Processing", 
    "Next Generation Computing", "Operating Systems", "Quantum Technology",
    "Software Defined Infrastructure", "Unmanned Aerial Vehicles", 
    "Wireless and Networking Technologies", "5G and 6G"
]

@dataclass
class SearchDataclass:
    max_results: int
    tech_area: str
    todays_date: str

@dataclass
class CompanySearchDependencies:
    tech_area: str
    todays_date: str
    max_results: int

#This class definition defines a data model using Pydantic's BaseModel
class CompanyInfo(BaseModel):  
    name: str = Field(description='Name of the company')
    website: str = Field(description='Official website URL of the company')
    tech_area: str = Field(description='Primary technology area of the company')

class CompanySearchResult(BaseModel):
    companies: List[CompanyInfo] = Field(description='List of companies with their details')
    summary: str = Field(description='Brief summary of the search results')
#this class represents a structured data format for company search results, containing a list of company details and a summary of the results.

# Create the agent with specific focus on company extraction
company_search_agent = Agent(
    'openai:gpt-4',
    deps_type=CompanySearchDependencies,
    result_type=CompanySearchResult,
    system_prompt='''You are an expert at researching Indian technology startups.
    Your task is to:
    1. Make ONE comprehensive search query that includes company names AND their websites
    2. Extract only verified Indian startups (not established companies)
    3. Limit extraction to 5-7 most promising startups per technology area
    4. Include official website URLs from the search results
    
    Use this search format:
    "top emerging Indian startups in [tech_area] technology with their official websites"
    
    DO NOT make separate searches for individual companies or websites.
    Focus on emerging and startup companies only, not established enterprises.
    '''
)

@company_search_agent.tool
async def get_search(search_data: RunContext[SearchDataclass], query: str, query_number: int) -> dict[str, Any]:
    """Tool for getting web search results for Indian startups in specific tech areas."""
    print(f"Search query {query_number}: {query}")
    results = await tavily_client.get_search_context(
        query=query,
        max_results=search_data.deps.max_results,
        search_depth="advanced"
    )
    return results

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

async def process_tech_area(tech_area: str) -> CompanySearchResult:
    """Process a single technology area to find relevant startups."""
    deps = CompanySearchDependencies(
        tech_area=tech_area,
        todays_date=date.today().strftime("%Y-%m-%d"),
        max_results=10   #increase or decrease the number accordingly to your needs
    )

    result = await company_search_agent.run(
        f'top emerging Indian startups in {tech_area} technology with their official websites',
        deps=deps
    )

    # Save the results to database
    save_to_database(result.data.companies)

    return result.data

async def main():
    all_results = []
    results_dir = Path("results")
    
    # Test database connection
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        print("✅ Successfully connected to MySQL database")
        session.close()
    except SQLAlchemyError as e:
        print(f"❌ Failed to connect to database: {str(e)}")
        return

    for tech_area in TECHNOLOGY_AREAS:
        print(f"\nProcessing {tech_area}...")
        try:
            result = await process_tech_area(tech_area)
            all_results.append(result)
            print(f"✅ Completed {tech_area}")

            # Save results to file
            filename = results_dir / f"results_{tech_area.replace(' ', '_')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Results for {tech_area}:\n\n")
                for company in result.companies:
                    f.write(f"Name: {company.name}\n")
                    f.write(f"Website: {company.website}\n")
                    f.write(f"Technology Area: {company.tech_area}\n")
                    f.write("-" * 50 + "\n")
                f.write("\nSummary:\n")
                f.write(result.summary)
            
            # Add delay to respect API limits
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Error processing {tech_area}: {e}")
            # Saving error files in the same results directory
            filename = results_dir / f"error_{tech_area.replace(' ', '_')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Error processing {tech_area}: {str(e)}")
    
    return all_results

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

if __name__ == "__main__":
    # Run the main process
    asyncio.run(main())
    
    # Query and display the results from the database
    query_database()
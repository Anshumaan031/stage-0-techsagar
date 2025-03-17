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
from utils import db
from utils import helper
import os

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

async def main():
    all_results = []
    results_dir = helper.ensure_results_directory()
    
    # Test database connection
    # try:
    #     session = SessionLocal()
    #     session.execute(text("SELECT 1"))
    #     print("✅ Successfully connected to MySQL database")
    #     session.close()
    # except SQLAlchemyError as e:
    #     print(f"❌ Failed to connect to database: {str(e)}")
    #     return

    # Define the technology areas
    # TECHNOLOGY_AREAS = [
    #     "AI and ML", "Application Infrastructure and Software", "Augmented and Virtual Reality",
    #     "Blockchain", "Cloud Computing and Virtualization", "Computer Vision", "Cryptology",
    #     "Cybersecurity", "Data Science", "Digital Forensics", "Enterprise Business Technologies",
    #     "Hardware, Semiconductors, and Embedded", "Human Computer Interaction", 
    #     "Identity Management and Authentication", "Internet of Things", "Location and Presence", 
    #     "Material Science", "Mobility and End Points", "Natural Language Processing", 
    #     "Next Generation Computing", "Operating Systems", "Quantum Technology",
    #     "Software Defined Infrastructure", "Unmanned Aerial Vehicles", 
    #     "Wireless and Networking Technologies", "5G and 6G"
    # ]

    TECHNOLOGY_AREAS = ["Computer Vision"]

    for tech_area in TECHNOLOGY_AREAS:
        print(f"\nProcessing {tech_area}...")
        try:
            result = await helper.process_tech_area(tech_area)
            all_results.append(result)
            print(f"✅ Completed {tech_area}")

            # Save results to file in the results directory
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
    
    return all_results

if __name__ == "__main__":
    # Run the main process
    asyncio.run(main())
    
    # Query and display the results from the database
    # query_database()
from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict
from datetime import date
from pathlib import Path
from agent import company_search_agent

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient
from utils import db
from utils import helper
import json

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

class CompanyInfo(BaseModel):
    name: str = Field(description='Name of the company')
    website: str = Field(description='Official website URL of the company')
    tech_area: str = Field(description='Primary technology area of the company')

class CompanySearchResult(BaseModel):
    companies: List[CompanyInfo] = Field(description='List of companies with their details')
    summary: str = Field(description='Brief summary of the search results')

def load_existing_companies() -> Dict:
    """Load the existing companies from the JSON file."""
    try:
        with open('filered-data-company-14feb-array.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading existing companies: {str(e)}")
        return {}


async def process_tech_area(tech_area: str) -> CompanySearchResult:
    """Process a single technology area to find relevant startups."""
    deps = CompanySearchDependencies(
        tech_area=tech_area,
        todays_date=date.today().strftime("%Y-%m-%d"),
        max_results=10
    )

    result = await company_search_agent.run(
        f'top emerging Indian startups in {tech_area} technology with their official websites',
        deps=deps
    )

    # Load existing companies
    existing_companies = load_existing_companies()

    #Save the results to database
    db.save_to_database(result.data.companies, existing_companies)

    return result.data

def ensure_results_directory():
    """Create results directory if it doesn't exist."""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    return results_dir
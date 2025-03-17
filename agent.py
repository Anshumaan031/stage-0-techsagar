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
# from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
# from langchain_community.tools import DuckDuckGoSearchRun
from tavily import AsyncTavilyClient
from utils import db
from utils import helper

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

# Define the Company model for the database
class CompanyDB(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    website = Column(String(255), nullable=False)
    tech_area = Column(String(100), index=True, nullable=False)
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

# Create the agent with specific focus on company extraction
company_search_agent = Agent(
    'openai:gpt-4',
    # tools=[duckduckgo_search_tool()],
    deps_type=CompanySearchDependencies,
    result_type=CompanySearchResult,
    system_prompt='''You are an expert at researching Indian technology startups.
    Your task is to:
    1. Make ONE comprehensive search query that includes company names AND their websites
    3. Use both the duckduckgo_search_tool and the Tavily API to get search results
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

# @company_search_agent.tool
# async def get_ddg_search(search_data: RunContext[SearchDataclass], query: str, query_number: int) -> dict[str, Any]:
#     """Tool for getting DuckDuckGo search results for Indian startups in specific tech areas.
#     This complements the Tavily search by providing an alternative source of information.
#     """
#     print(f"DuckDuckGo search query {query_number}: {query}")
    
#     # Initialize the DuckDuckGo search tool
#     ddg_search = DuckDuckGoSearchRun()
    
#     # Execute the search
#     try:
#         # DuckDuckGo search returns results as a string
#         results_text = ddg_search.invoke(query)
        
#         # Process the results to match the format expected by the agent
#         # We'll structure it similar to how Tavily results are structured
#         processed_results = {
#             "query": query,
#             "results": [
#                 {
#                     "content": results_text,
#                     "source": "DuckDuckGo Search",
#                     "score": 1.0,  # Default score
#                 }
#             ],
#             "search_depth": "standard",
#             "source": "duckduckgo"
#         }
        
#         return processed_results
#     except Exception as e:
#         print(f"Error in DuckDuckGo search: {str(e)}")
#         # Return empty results in case of error
#         return {
#             "query": query,
#             "results": [],
#             "search_depth": "standard",
#             "source": "duckduckgo",
#             "error": str(e)
#         }
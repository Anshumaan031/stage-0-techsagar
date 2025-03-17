from __future__ import annotations as _annotations 

import os 
from dotenv import load_dotenv 
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict, Union, Optional 
from datetime import date 
from pathlib import Path
import httpx 
import re 

from pydantic_ai import agent, ModelRetry, RunContext 
from pydantic import BaseModel, Field, validator 
from tavily import AsyncTavilyClient 


#load environment 
load_dotenv() 

#setup api keys 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") 
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY") 

#setup tavily client 
tavily_client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"]) 

#data Models 
@dataclass
class SearchDataclass:
    max_results: int 
    tech_area: str 
    todays_date: str 


@dataclass
class StartupDependencies:
    tech_area: str 
    todays_date: str 
    max_results: int 

class StartupCandidate(BaseModel):
    name: str = Field(description="Name of the potential startup")
    tech_area: str = Field(description="Primary technology area of the startup")

class StartupCandidateList(BaseModel):
    candidates: List[StartupCandidate] = Field(description="List of potential startup candidates")
    summary: str = Field(description="Brief summary of the startup candidates")

class StartupWithWebsite(BaseModel):
    name: str = Field(description="Name of the startup")
    website: str = Field(description="Official website URL of the startup")
    tech_area: str = Field(description="Primary technology area of the startup")




startup_finder_agent = agent.Agent(
    'openai:gpt-4o-mini',
    deps_type=StartupDependencies,
    result_type=StartupCandidateList,
    system_prompt='''You are an expert at researching emerging Indian technology startups.
    Your task is to identify promising Indian startups in a specific technology area.
    
    IMPORTANT GUIDELINES:
    1. Focus ONLY on INDIAN startups (companies based in India or founded by Indians in India)
    2. Look for EMERGING startups, not established companies
       - Startups should be less than 7 years old if possible
       - Avoid large enterprises or well-known companies like TCS, Infosys, etc.
    4. Find 5-7 promising startups per technology area
    
    DO NOT include any companies unless you have high confidence they are Indian startups.
    DO NOT include website URLs at this stage - that will be handled separately.
    '''
)

@startup_finder_agent.tool
async def get_startup_search(search_data: RunContext[SearchDataclass], query: str, query_number: int) -> dict[str, Any]:
    """Tool for getting web search results for Indian startups in specific tech areas."""
    print(f"Search query {query_number}: {query}")
    results = await tavily_client.get_search_context(
        query=query,
        max_results=search_data.deps.max_results,
        search_depth="advanced"
    )
    return results 


#AGENT 2: WEBSITE FINDER
# this agent finds official websites for companies
website_finder_agent = agent.Agent(
    'openai:gpt-4o-mini',
    result_type=StartupWithWebsite,
    system_prompt='''You are an expert at finding official websites for companies.

    Given a startup name and technology area, your task is to:
    1. Find the OFFICIAL website for this company
    2. Make sure it is the correct company (check that the company name and tech area match)
    3. Verify that the website domain looks legitimate (not a social media page or listing site)'

    IMPORTANT:
    - Only return websites that you have high confidence are the official company websites
    - For Indian startups, websites often end with .in, .co.in, or .com
    - Do not confuse with similarly named international companies
    - Check that the company appears to be based in India
    '''

@website_finder_agent.tool
async def search_company_website(query: str) -> dict[str, Any]:
    """tool for finding the official website for the company"""
    print(f"Website search query: {query}")
    results = await tavily_client.get_search_context(
        query=query,
        max_results=3,
        search_depth="basic"
    )
    return results


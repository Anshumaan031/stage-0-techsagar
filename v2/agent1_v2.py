from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict
import json

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

# Load environment variables
load_dotenv()

# Setup API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# Setup Tavily Client
tavily_client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Data Models for Agent 1: Company Research
@dataclass
class CompanyResearchDependencies:
    tech_areas: List[str]
    max_results: int = 5
    search_depth: str = "advanced"  # "basic" or "advanced"

class CompanyInfo(BaseModel):
    name: str = Field(description='Name of the company')
    tech_area: str = Field(description='Primary technology area of the company')
    description: str = Field(description='Brief description of what the company does')

class TechAreaResult(BaseModel):
    companies: List[CompanyInfo] = Field(description='List of companies in this tech area')
    summary: str = Field(description='Brief summary of findings for this tech area')
    query_used: str = Field(description='Search query used for this tech area')

class CompanyResearchResult(BaseModel):
    results: Dict[str, TechAreaResult] = Field(description='Results organized by technology area')
    total_companies_found: int = Field(description='Total number of companies found across all tech areas')

# Create the research agent
company_research_agent = Agent(
    'openai:gpt-4',
    deps_type=CompanyResearchDependencies,
    result_type=CompanyResearchResult,
    system_prompt='''You are an expert at researching emerging Indian technology startups.
    Your task is to analyze search results and extract information about promising Indian startups
    in specific technology areas.
    
    IMPORTANT GUIDELINES:
    1. Focus ONLY on INDIAN startups (companies based in India or founded by Indians in India)
    2. Look for EMERGING startups, not established companies
       - Startups should be relatively new (ideally less than 7-10 years old)
       - Avoid large enterprises or well-known companies like TCS, Infosys, Wipro, etc.
    3. Prioritize companies with innovative approaches or technologies
    4. Find 5-7 promising startups per technology area
    5. Provide a brief description of what each company does
    
    DO NOT include any company unless you have high confidence it is an Indian startup.
    Extract information ONLY from the search results provided.
    
    Your output should be a structured collection of tech area results, each containing:
    - A list of companies with their details
    - A summary of findings for that tech area
    - The search query used
    
    Also include a count of the total number of companies found across all tech areas.
    '''
)

@company_research_agent.tool
async def search_indian_startups(search_data: RunContext[CompanyResearchDependencies], tech_area: str) -> dict[str, Any]:
    """Tool for searching for Indian startups in a specific technology area."""
    # Create optimized search query
    search_query = f"top emerging Indian startups in {tech_area} technology funding recent innovation"
    print(f"Searching for: {tech_area} with query: {search_query}")
    
    # Use Tavily for web search
    tavily_results = await tavily_client.get_search_context(
        query=search_query,
        max_results=search_data.deps.max_results,
        search_depth=search_data.deps.search_depth
    )
    
    # Add the query to the results for reference
    tavily_results["query_used"] = search_query
    tavily_results["tech_area"] = tech_area
    
    return tavily_results

# Example usage
async def main():
    """Example of using the company research agent."""
    # Define tech areas to research
    tech_areas = [
        "AI and ML",
        "Blockchain",
        "FinTech"
    ]
    
    # Set up dependencies
    deps = CompanyResearchDependencies(
        tech_areas=tech_areas,
        max_results=5
    )
    
    # Run the agent
    print(f"Starting research for {len(tech_areas)} technology areas: {', '.join(tech_areas)}")
    result = await company_research_agent.run(
        "Research emerging Indian startups in the specified technology areas",
        deps=deps
    )
    
    # Output results as JSON
    json_output = result.data.json(indent=2)
    print("\nResearch completed successfully!")
    
    # Save results to file
    with open("research_results.json", "w") as f:
        f.write(json_output)
    print("Results saved to research_results.json")
    
    # Display summary
    print(f"\nSummary: Found {result.data.total_companies_found} companies across {len(tech_areas)} technology areas")
    for tech_area, area_result in result.data.results.items():
        print(f"  - {tech_area}: {len(area_result.companies)} companies")

if __name__ == "__main__":
    asyncio.run(main())
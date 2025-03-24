from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict
from datetime import date
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

# Data Models
@dataclass
class ResearchDependencies:
    tech_area: str
    max_results: int
    search_depth: str = "advanced"  # "basic" or "advanced"

class CompanyInfo(BaseModel):
    name: str = Field(description='Name of the company')
    tech_area: str = Field(description='Primary technology area of the company')
    description: str = Field(description='Brief description of what the company does')
    
class CompanyResearchResult(BaseModel):
    companies: List[CompanyInfo] = Field(description='List of companies with their details')
    summary: str = Field(description='Brief summary of the research results')

# Create the research agent
company_research_agent = Agent(
    'openai:gpt-4o-mini',
    deps_type=ResearchDependencies,
    result_type=CompanyResearchResult,
    system_prompt='''You are an expert at researching emerging Indian technology startups.
    Your task is to analyze search results and extract information about promising Indian startups
    in a specific technology area.
    
    IMPORTANT GUIDELINES:
    1. Focus ONLY on INDIAN startups (companies based in India or founded by Indians in India)
    2. Look for EMERGING startups, not established companies
       - Startups should be relatively new (ideally less than 7-10 years old)
       - Avoid large enterprises or well-known companies like TCS, Infosys, Wipro, etc.
    3. Prioritize companies with innovative approaches or technologies
    4. Find at least 20 promising startups per technology area
    5. Provide a brief description of what each company does
    
    DO NOT include any company unless you have high confidence it is an Indian startup.
    Extract information ONLY from the search results provided.
    '''
)

@company_research_agent.tool
async def search_indian_startups(search_data: RunContext[ResearchDependencies], query: str) -> dict[str, Any]:
    """Tool for searching for Indian startups in specific technology areas."""
    print(f"Search query: {query}")
    
    # Use Tavily for web search
    tavily_results = await tavily_client.get_search_context(
        query=query,
        max_results=search_data.deps.max_results,
        search_depth=search_data.deps.search_depth
    )
    
    return tavily_results

async def research_tech_area(tech_area: str, max_results: int = 5) -> Dict:
    """Research startups for a specific technology area and return results."""
    deps = ResearchDependencies(
        tech_area=tech_area,
        max_results=max_results
    )
    
    # Create optimized search query
    search_query = f"top emerging Indian startups in {tech_area} technology funding recent innovation"
    
    try:
        # Run the agent to get research results
        result = await company_research_agent.run(search_query, deps=deps)
        
        # Convert to dictionary for easy JSON serialization
        output = {
            "tech_area": tech_area,
            "companies": [company.dict() for company in result.data.companies],
            "summary": result.data.summary,
            "query_used": search_query
        }
        
        return output
    
    except Exception as e:
        print(f"Error researching {tech_area}: {e}")
        return {
            "tech_area": tech_area,
            "companies": [],
            "summary": f"Error occurred during research: {str(e)}",
            "query_used": search_query
        }

async def main():
    """Main function to test the research agent."""
    # Example technology areas
    tech_areas = [
        "Blockchain"
    ]
    
    all_results = {}
    
    for tech_area in tech_areas:
        print(f"\nResearching: {tech_area}")
        result = await research_tech_area(tech_area)
        all_results[tech_area] = result
        
        # Print some basic information about what was found
        print(f"Found {len(result['companies'])} companies")
        
        # Add delay to respect API limits
        await asyncio.sleep(2)
    
    # Save results to JSON file
    with open("research_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\nAll research completed and saved to research_results.json")

if __name__ == "__main__":
    asyncio.run(main())
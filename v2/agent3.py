from __future__ import annotations as _annotations

import os
import json
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import GeminiModel
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
class WebsiteFinderDependencies:
    company_name: str
    tech_area: str
    company_details: Dict
    max_results: int = 3
    search_depth: str = "advanced"  # "basic" or "advanced"

class WebsiteInfo(BaseModel):
    company_name: str = Field(description='Name of the company')
    official_website: str = Field(description='Official website URL of the company')
    tech_area: str = Field(description='Primary technology area of the company')
    confidence_score: int = Field(description='Confidence score for the website (1-10)', ge=1, le=10)
    verification_notes: str = Field(description='Notes explaining the verification process')

class WebsiteSearchResult(BaseModel):
    websites: List[WebsiteInfo] = Field(description='List of verified company websites')
    summary: str = Field(description='Summary of the website search results')

model = GeminiModel('gemini-2.0-flash', provider='google-gla')


# Create the website finder agent
website_finder_agent = Agent(
    model=model,
    deps_type=WebsiteFinderDependencies,
    result_type=WebsiteSearchResult,
    system_prompt='''You are an expert at finding and verifying official websites for Indian technology startups.
    
    For each company, your task is to:
    
    1. Find the OFFICIAL company website (not third-party sites, LinkedIn, Crunchbase, etc.)
    2. Verify the authenticity of the website by checking:
       - Domain name matches or is closely related to company name
       - Website content confirms it's the company's official site
       - Contact information includes Indian addresses/phone numbers
       - Website looks professionally developed and maintained
    
    3. Assign a confidence score (1-10) based on your verification:
       - 10: Absolutely certain this is the official website
       - 7-9: Very confident but with minor uncertainties
       - 4-6: Moderate confidence, some verification issues
       - 1-3: Low confidence, significant verification issues
    
    4. Provide detailed verification notes explaining:
       - How you verified this is the official website
       - Any discrepancies or issues that affected your confidence score
       - Any additional relevant observations
    
    ONLY return websites that you're reasonably confident are official (score 5+).
    DO NOT include any website unless you've verified it with multiple sources.
    BE THOROUGH - official websites are critical for the accuracy of our database.
    '''
)

@website_finder_agent.tool
async def search_company_website(search_data: RunContext[WebsiteFinderDependencies], query: str) -> dict[str, Any]:
    """Tool for searching and verifying official company websites."""
    print(f"Website search query: {query}")
    
    # Use Tavily for web search
    tavily_results = await tavily_client.get_search_context(
        query=query,
        max_results=search_data.deps.max_results,
        search_depth=search_data.deps.search_depth
    )
    
    return tavily_results

async def find_company_website(company: Dict, tech_area: str) -> Dict:
    """Find and verify the official website for a validated Indian startup."""
    company_name = company["name"]
    print(f"\nFinding website for: {company_name}")
    
    # Create dependency object with company info
    deps = WebsiteFinderDependencies(
        company_name=company_name,
        tech_area=tech_area,
        company_details=company
    )
    
    # Create optimized search query for website finding
    website_query = f"{company_name} official website India technology startup genuine authentic"
    
    try:
        # Run the agent to find the official website
        result = await website_finder_agent.run(website_query, deps=deps)
        
        # Return the result
        return {
            "company_name": company_name,
            "websites": [website.dict() for website in result.data.websites],
            "summary": result.data.summary
        }
        
    except Exception as e:
        print(f"Error finding website for {company_name}: {e}")
        return {
            "company_name": company_name,
            "websites": [],
            "summary": f"Failed to find website due to error: {str(e)}"
        }

def ensure_results_directory():
    """Create results directory if it doesn't exist."""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    return results_dir

async def main():
    """Main function to find official websites for validated Indian startups."""
    # Load results from agent2
    try:
        with open("agent2_results.json", "r") as f:
            validation_results = json.load(f)
    except FileNotFoundError:
        print("Error: agent2_results.json not found. Run agent2.py first.")
        return
    
    website_results = {}
    all_websites = []
    
    # Process each tech area
    for tech_area, data in validation_results.items():
        print(f"\nProcessing websites for tech area: {tech_area}")
        area_results = []
        
        # Filter for companies that passed validation as Indian startups
        valid_companies = [
            company for company in data["validated_companies"] 
            if company["is_indian"] and company["is_startup"]
        ]
        
        if not valid_companies:
            print(f"No valid Indian startups found for {tech_area}.")
            continue
        
        print(f"Found {len(valid_companies)} valid Indian startups for {tech_area}.")
        
        # Process each valid company
        for company in valid_companies:
            website_result = await find_company_website(company, tech_area)
            area_results.append(website_result)
            
            # Extract websites with high confidence for the final consolidated list
            for website_info in website_result.get("websites", []):
                if website_info.get("confidence_score", 0) >= 7:  # Only include high confidence websites
                    all_websites.append({
                        "name": website_info["company_name"],
                        "website": website_info["official_website"],
                        "tech_area": website_info["tech_area"],
                        "confidence": website_info["confidence_score"]
                    })
            
            # Add delay to respect API limits
            await asyncio.sleep(2)
        
        # Add results for this tech area
        website_results[tech_area] = {
            "tech_area": tech_area,
            "company_websites": area_results,
            "count": len(area_results)
        }
    
    # Save detailed results to JSON file
    with open("agent3_results.json", "w") as f:
        json.dump(website_results, f, indent=2)
    
    # Create a consolidated CSV-friendly format for all high-confidence websites
    results_dir = ensure_results_directory()
    consolidated_file = results_dir / "verified_companies.json"
    
    with open(consolidated_file, "w") as f:
        json.dump(all_websites, f, indent=2)
    
    print(f"\nWebsite search completed!")
    print(f"Detailed results saved to agent3_results.json")
    print(f"Consolidated high-confidence results saved to {consolidated_file}")
    print(f"Found {len(all_websites)} verified websites across all tech areas.")

if __name__ == "__main__":
    asyncio.run(main())
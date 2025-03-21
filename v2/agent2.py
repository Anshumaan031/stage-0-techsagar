from __future__ import annotations as _annotations

import os
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, Union
from datetime import date
import json

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
class ValidationDependencies:
    company_info: Dict
    max_results: int = 3
    search_depth: str = "advanced"  # "basic" or "advanced"

class ValidationResult(BaseModel):
    name: str = Field(description='Name of the company')
    is_indian: bool = Field(description='Whether the company is based in India or founded by Indians in India')
    is_startup: bool = Field(description='Whether the company is an emerging startup (not an established company)')
    founded_year: Optional[int] = Field(None, description='Year when the company was founded, if available')
    founders: Optional[str] = Field(None, description='Names of the founders, if available')
    headquarters: Optional[str] = Field(None, description='Location of headquarters, if available')
    funding_info: Optional[str] = Field(None, description='Brief information about funding, if available')
    validation_notes: str = Field(description='Notes explaining the validation decision')

class CompanyValidationResult(BaseModel):
    validated_companies: List[ValidationResult] = Field(description='List of validated companies with detailed information')
    summary: str = Field(description='Summary of the validation results')

model = GeminiModel('gemini-2.0-flash', provider='google-gla')

# Create the validation agent
validation_agent = Agent(
    model=model,
    deps_type=ValidationDependencies,
    result_type=CompanyValidationResult,
    system_prompt='''You are an expert at validating Indian technology startups.
    Your task is to analyze each company and verify two key criteria:
    
    1. Is it truly an INDIAN company?
       - Company should be based in India OR founded by Indians in India
       - Check headquarters location, founders' nationality/origin
       
    2. Is it truly a STARTUP (not an established company)?
       - Startups should be relatively new (founded within the last 10 years)
       - Should not be large enterprises or well-established corporations
       - Typically would have raised funding but not be publicly traded (with some exceptions)
       
    For each company, perform thorough research to validate these criteria.
    Provide detailed validation notes explaining your decision.
    
    When possible, gather additional information like:
    - Founded year
    - Founders' names
    - Headquarters location
    - Funding information
    
    BE SKEPTICAL - reject companies if you cannot find sufficient evidence that they meet BOTH criteria.
    '''
)

@validation_agent.tool
async def search_company_info(validation_data: RunContext[ValidationDependencies], query: str) -> dict[str, Any]:
    """Tool for searching detailed information about a company to validate its status."""
    print(f"Validation search query: {query}")
    
    # Use Tavily for web search
    tavily_results = await tavily_client.get_search_context(
        query=query,
        max_results=validation_data.deps.max_results,
        search_depth=validation_data.deps.search_depth
    )
    
    return tavily_results

async def validate_companies(input_data: Dict) -> Dict:
    """Validate companies from agent1 results and return detailed validation results."""
    tech_area = input_data["tech_area"]
    companies = input_data["companies"]
    
    all_validated_companies = []
    
    for company in companies:
        company_name = company["name"]
        print(f"\nValidating: {company_name}")
        
        # Create dependency object with company info
        deps = ValidationDependencies(
            company_info=company
        )
        
        # Create optimized search query for validation
        validation_query = f"{company_name} startup India company headquarters founders funding year founded"
        
        try:
            # Run the agent to validate this company
            result = await validation_agent.run(validation_query, deps=deps)
            
            # Add validated results to our list
            all_validated_companies.extend(result.data.validated_companies)
            
            # Add delay to respect API limits
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error validating {company_name}: {e}")
            # Add a failed validation record
            all_validated_companies.append(
                ValidationResult(
                    name=company_name,
                    is_indian=False,
                    is_startup=False,
                    validation_notes=f"Validation failed due to error: {str(e)}"
                )
            )
    
    # Generate overall summary
    valid_indian_startups = [c for c in all_validated_companies if c.is_indian and c.is_startup]
    
    summary = f"Validation completed for {len(all_validated_companies)} companies in the {tech_area} sector. "
    summary += f"Found {len(valid_indian_startups)} valid Indian startups. "
    summary += f"{len(all_validated_companies) - len(valid_indian_startups)} companies failed validation."
    
    # Create final result
    validation_result = {
        "tech_area": tech_area,
        "validated_companies": [comp.dict() for comp in all_validated_companies],
        "summary": summary,
        "original_query": input_data.get("query_used", "")
    }
    
    return validation_result

async def main():
    """Main function to test the validation agent."""
    # Load results from agent1
    try:
        with open("agent1_results.json", "r") as f:
            research_results = json.load(f)
    except FileNotFoundError:
        print("Error: research_results.json not found. Run agent1.py first.")
        return
    
    validation_results = {}
    
    # Process each tech area
    for tech_area, data in research_results.items():
        print(f"\nValidating companies for: {tech_area}")
        
        # Limit to first 5 companies for testing purposes
        # Remove this slice in production
        test_data = data.copy()
        test_data["companies"] = data["companies"][:5]
        
        validation_result = await validate_companies(test_data)
        validation_results[tech_area] = validation_result
    
    # Save validation results to JSON file
    with open("agent2_results.json", "w") as f:
        json.dump(validation_results, f, indent=2)
    
    print("\nValidation completed and saved to validation_results.json")
    
    # Print a summary of results
    for tech_area, results in validation_results.items():
        valid_count = sum(1 for company in results["validated_companies"] if company["is_indian"] and company["is_startup"])
        total_count = len(results["validated_companies"])
        
        print(f"\n{tech_area}: {valid_count}/{total_count} companies validated as Indian startups")

if __name__ == "__main__":
    asyncio.run(main())
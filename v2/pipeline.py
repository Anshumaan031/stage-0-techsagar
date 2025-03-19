from __future__ import annotations as _annotations

import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict
from datetime import date, datetime
import argparse

from dotenv import load_dotenv
from pydantic import BaseModel

# Import agents from each module
from agent1 import research_tech_area
from agent2 import validate_companies
from agent3 import find_company_website

# Load environment variables
load_dotenv()

class PipelineConfig:
    """Configuration for the agent pipeline."""
    
    def __init__(self, 
                 tech_areas: List[str] = None,
                 max_results_per_search: int = 50,
                 run_all_agents: bool = True,
                 start_from_agent: int = 1,
                 output_dir: str = "results"):
        
        self.tech_areas = tech_areas or [
            "AI and ML",
            "Blockchain",
            "Cybersecurity",
            "IoT"
        ]
        self.max_results_per_search = max_results_per_search
        self.run_all_agents = run_all_agents
        self.start_from_agent = start_from_agent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create a timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a run directory
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        self.run_dir.mkdir(exist_ok=True)

def save_results(data: Dict, filename: str, config: PipelineConfig):
    """Save results to a JSON file in the run directory."""
    filepath = config.run_dir / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Results saved to {filepath}")
    return filepath

async def run_agent1(config: PipelineConfig):
    """Run the research agent (agent1) to find startups."""
    print("\n==== RUNNING AGENT 1: STARTUP RESEARCH ====")
    
    all_results = {}
    
    for tech_area in config.tech_areas:
        print(f"\nResearching: {tech_area}")
        result = await research_tech_area(tech_area, config.max_results_per_search)
        all_results[tech_area] = result
        
        # Print basic information
        company_count = len(result.get("companies", []))
        print(f"Found {company_count} potential companies for {tech_area}")
        
        # Add delay to respect API limits
        await asyncio.sleep(2)
    
    # Save the results
    filepath = save_results(all_results, "agent1_results.json", config)
    return all_results, filepath

async def run_agent2(research_results: Dict, config: PipelineConfig):
    """Run the validation agent (agent2) to validate startups."""
    print("\n==== RUNNING AGENT 2: STARTUP VALIDATION ====")
    
    validation_results = {}
    
    for tech_area, data in research_results.items():
        print(f"\nValidating companies for: {tech_area}")
        validation_result = await validate_companies(data)
        validation_results[tech_area] = validation_result
        
        # Print summary
        valid_count = sum(1 for company in validation_result["validated_companies"] 
                         if company["is_indian"] and company["is_startup"])
        total_count = len(validation_result["validated_companies"])
        
        print(f"{tech_area}: {valid_count}/{total_count} companies validated as Indian startups")
    
    # Save the results
    filepath = save_results(validation_results, "agent2_results.json", config)
    return validation_results, filepath

async def run_agent3(validation_results: Dict, config: PipelineConfig):
    """Run the website finder agent (agent3) to find official websites."""
    print("\n==== RUNNING AGENT 3: WEBSITE FINDER ====")
    
    website_results = {}
    all_websites = []
    
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
    
    # Save detailed results
    filepath = save_results(website_results, "agent3_results.json", config)
    
    # Save consolidated results
    consolidated_filepath = config.run_dir / "verified_companies.json"
    with open(consolidated_filepath, "w") as f:
        json.dump(all_websites, f, indent=2)
    
    print(f"\nWebsite search completed!")
    print(f"Found {len(all_websites)} verified websites across all tech areas.")
    print(f"Consolidated results saved to {consolidated_filepath}")
    
    return website_results, filepath

async def run_pipeline(config: PipelineConfig):
    """Run the full pipeline of agents."""
    print(f"\n===== STARTING PIPELINE RUN: {config.timestamp} =====")
    print(f"Tech Areas: {', '.join(config.tech_areas)}")
    print(f"Output Directory: {config.run_dir}")
    
    # Track our progress through the pipeline
    research_results = None
    validation_results = None
    website_results = None
    
    # Run Agent 1: Research
    if config.start_from_agent <= 1:
        research_results, research_filepath = await run_agent1(config)
        if not config.run_all_agents:
            return {
                "research_results": research_results,
                "research_filepath": research_filepath
            }
    else:
        # Load previous results
        try:
            with open("agent1_results.json", "r") as f:
                research_results = json.load(f)
                print("Loaded existing research results from agent1_results.json")
        except FileNotFoundError:
            print("Error: agent1_results.json not found but required for starting from agent 2 or 3.")
            return None
    
    # Run Agent 2: Validation
    if config.start_from_agent <= 2:
        validation_results, validation_filepath = await run_agent2(research_results, config)
        if not config.run_all_agents and config.start_from_agent == 2:
            return {
                "validation_results": validation_results,
                "validation_filepath": validation_filepath
            }
    else:
        # Load previous results
        try:
            with open("agent2_results.json", "r") as f:
                validation_results = json.load(f)
                print("Loaded existing validation results from agent2_results.json")
        except FileNotFoundError:
            print("Error: agent2_results.json not found but required for starting from agent 3.")
            return None
    
    # Run Agent 3: Website Finder
    website_results, website_filepath = await run_agent3(validation_results, config)
    
    # Generate a final report
    final_report = {
        "timestamp": config.timestamp,
        "tech_areas": config.tech_areas,
        "summary": {
            "companies_researched": sum(len(data.get("companies", [])) for data in research_results.values()),
            "companies_validated": sum(
                sum(1 for company in data["validated_companies"] if company["is_indian"] and company["is_startup"])
                for data in validation_results.values()
            ),
            "websites_found": sum(len(area.get("company_websites", [])) for area in website_results.values())
        },
        "filepaths": {
            "research": str(config.run_dir / "agent1_results.json"),
            "validation": str(config.run_dir / "agent2_results.json"),
            "websites": str(config.run_dir / "agent3_results.json"),
            "consolidated": str(config.run_dir / "verified_companies.json")
        }
    }
    
    # Save the final report
    report_filepath = save_results(final_report, "pipeline_report.json", config)
    
    print("\n===== PIPELINE RUN COMPLETED =====")
    print(f"Tech Areas Processed: {', '.join(config.tech_areas)}")
    print(f"Companies Researched: {final_report['summary']['companies_researched']}")
    print(f"Companies Validated as Indian Startups: {final_report['summary']['companies_validated']}")
    print(f"Websites Found: {final_report['summary']['websites_found']}")
    print(f"Results Directory: {config.run_dir}")
    
    return {
        "research_results": research_results,
        "validation_results": validation_results,
        "website_results": website_results,
        "final_report": final_report,
        "report_filepath": report_filepath
    }

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the startup research pipeline")
    
    parser.add_argument("--tech-areas", "-t", type=str, nargs="+",
                        help="List of technology areas to research")
    
    parser.add_argument("--max-results", "-m", type=int, default=5,
                        help="Maximum number of search results per query")
    
    parser.add_argument("--agent", "-a", type=int, choices=[1, 2, 3], default=1,
                        help="Start from specific agent (1: Research, 2: Validation, 3: Website)")
    
    parser.add_argument("--run-single", "-s", action="store_true",
                        help="Run only the specified agent instead of the full pipeline")
    
    parser.add_argument("--output-dir", "-o", type=str, default="results",
                        help="Directory to store results")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Create configuration
    config = PipelineConfig(
        tech_areas=args.tech_areas,
        max_results_per_search=args.max_results,
        run_all_agents=not args.run_single,
        start_from_agent=args.agent,
        output_dir=args.output_dir
    )
    
    # Run the pipeline
    asyncio.run(run_pipeline(config))
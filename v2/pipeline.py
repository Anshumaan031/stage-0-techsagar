from flask import Flask, request, jsonify
import asyncio
import os
import json
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv

# Import agent modules
from agent1 import research_tech_area
from agent2 import validate_companies
from agent3 import find_company_website, ensure_results_directory
from flask_cors import CORS
from utils.db import save_company_profiles

# Load environment variables
load_dotenv()

# Setup Flask app
app = Flask(__name__)
CORS(app)

# Helper function to run async functions in sync context
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If no event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(coro)
    return result

@app.route('/api/pipeline', methods=['POST'])
def run_pipeline():
    try:
        # Get request data
        data = request.json
        
        if not data or 'tech_area' not in data:
            return jsonify({'error': 'Tech area is required'}), 400
        
        tech_area = data['tech_area']
        max_results = data.get('max_results', 5)
        
        # Create async function to run all agents
        async def run_all_agents():
            # Step 1: Research using agent1
            research_result = await research_tech_area(tech_area, max_results)
            
            # Step 2: Validate using agent2
            validation_result = await validate_companies(research_result)
            
            # Step 3: Find websites for all valid companies
            valid_companies = [
                company for company in validation_result['validated_companies'] 
                if company.get('is_indian') is True and company.get('is_startup') is True
            ]
            
            website_results = []
            all_websites = []
            
            for company in valid_companies:
                # Call find_company_website with the correct parameters
                website_result = await find_company_website(company, tech_area)
                website_results.append(website_result)
                
                # Extract high confidence websites
                for website_info in website_result.get('websites', []):
                    if website_info.get('confidence_score', 0) >= 7:
                        all_websites.append({
                            'name': website_info['company_name'],
                            'website': website_info['official_website'],
                            'tech_area': website_info['tech_area'],
                            'confidence': website_info['confidence_score']
                        })
                
                # Add delay to respect API limits
                await asyncio.sleep(1)
            
            # Create website response
            website_response = {
                'tech_area': tech_area,
                'company_websites': website_results,
                'count': len(website_results),
                'high_confidence_websites': all_websites
            }
            
            #save_website_data(all_websites)  # Original table
            save_company_profiles(all_websites)  # New ts_entity_company_profile table
            
            return {
                'research': research_result,
                'validation': validation_result,
                'websites': website_response
            }
        
        # Run the pipeline
        result = run_async(run_all_agents())
        
        # Save results to JSON files (optional)
        tech_area_safe = tech_area.replace(' ', '_')
        results_dir = ensure_results_directory()
        
        with open(f"{results_dir}/pipeline_result_{tech_area_safe}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'api_version': '2.0',
        'pipeline': True,
        'agents': ['research', 'validate', 'websites']
    })

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
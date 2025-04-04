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
from utils.db import save_website_data  

# Load environment variables
load_dotenv()

# Setup Flask app
app = Flask(__name__)
# Configure CORS with more specific options
# CORS(app, resources={r"/api/*": {
#     "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
#     "methods": ["GET", "POST", "OPTIONS"],
#     "allow_headers": ["Content-Type", "Authorization"],
#     "expose_headers": ["Content-Type"],
#     "supports_credentials": True
# }})

CORS(app)
 

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
            
            # Step 3: Find websites using agent3
            website_result = await find_company_website({
                'tech_area': tech_area,
                'companies': validation_result['validated_companies']
            })
            
            return {
                'research': research_result,
                'validation': validation_result,
                'websites': website_result
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

def run_async(coroutine):
    """Helper function to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
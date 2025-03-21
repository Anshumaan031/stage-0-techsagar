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

# Load environment variables
load_dotenv()

# Setup Flask app
app = Flask(__name__)
CORS(app) 

# Helper function to run async functions in sync context
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(coro)
    loop.close()
    return result

# Agent 1 Endpoint - Research Indian Startups in Tech Area
@app.route('/api/research', methods=['POST'])
def research_startups():
    try:
        # Get request data
        data = request.json
        
        if not data or 'tech_area' not in data:
            return jsonify({'error': 'Tech area is required'}), 400
        
        tech_area = data['tech_area']
        max_results = data.get('max_results', 5)
        
        # Call agent1's research function
        result = run_async(research_tech_area(tech_area, max_results))
        
        # Save result to JSON file (optional)
        with open(f"research_result_{tech_area.replace(' ', '_')}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Agent 2 Endpoint - Validate Companies
@app.route('/api/validate', methods=['POST'])
def validate_startups():
    try:
        # Get request data
        data = request.json
        
        if not data or 'tech_area' not in data or 'companies' not in data:
            return jsonify({'error': 'Tech area and companies are required'}), 400
        
        # Structure input data in the format expected by validate_companies
        input_data = {
            'tech_area': data['tech_area'],
            'companies': data['companies'],
            'query_used': data.get('query_used', '')
        }
        
        # Call agent2's validation function
        result = run_async(validate_companies(input_data))
        
        # Save result to JSON file (optional)
        with open(f"validation_result_{data['tech_area'].replace(' ', '_')}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Agent 3 Endpoint - Find Official Websites
@app.route('/api/websites', methods=['POST'])
def find_websites():
    try:
        # Get request data
        data = request.json
        
        if not data or 'tech_area' not in data or 'validated_companies' not in data:
            return jsonify({'error': 'Tech area and companies are required'}), 400
        
        tech_area = data['tech_area']
        companies = data['validated_companies']
        
        # Filter for companies where both is_indian and is_startup are True
        valid_companies = [
            company for company in companies 
            if company.get('is_indian') is True and company.get('is_startup') is True
        ]
        
        if not valid_companies:
            return jsonify({
                'tech_area': tech_area,
                'company_websites': [],
                'count': 0,
                'high_confidence_websites': [],
                'message': 'No valid Indian startups found to search for websites.'
            })
        
        # Process each valid company to find its website
        results = []
        new_websites = []  # Renamed for clarity
        
        for company in valid_companies:
            # Call agent3's website finder function
            website_result = run_async(find_company_website(company, tech_area))
            results.append(website_result)
            
            # Extract high confidence websites
            for website_info in website_result.get('websites', []):
                if website_info.get('confidence_score', 0) >= 7:  # Only include high confidence websites
                    new_websites.append({
                        'name': website_info['company_name'],
                        'website': website_info['official_website'],
                        'tech_area': website_info['tech_area'],
                        'confidence': website_info['confidence_score']
                    })
        
        # Create response with ONLY new websites
        response = {
            'tech_area': tech_area,
            'company_websites': results,
            'count': len(results),
            'high_confidence_websites': new_websites.copy()  # Make a copy to ensure it's not modified
        }
        
        # Save results to files
        with open(f"website_result_{tech_area.replace(' ', '_')}.json", "w") as f:
            json.dump(response, f, indent=2)
        
        # Save consolidated websites to verified_companies.json
        results_dir = ensure_results_directory()
        consolidated_file = results_dir / "verified_companies.json"
        
        # Read existing data if file exists
        existing_websites = []
        if consolidated_file.exists():
            try:
                with open(consolidated_file, "r") as f:
                    existing_websites = json.load(f)
            except:
                pass
        
        # Create combined list for saving to file
        combined_websites = new_websites.copy()
        combined_websites.extend(existing_websites)
        
        # Write back to file
        with open(consolidated_file, "w") as f:
            json.dump(combined_websites, f, indent=2)
        
        # Return only the new results
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'api_version': '1.0',
        'agents': ['research', 'validate', 'websites']
    })

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
from flask import Flask, request, jsonify
import os
import json
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import threading
import nest_asyncio
from functools import wraps

# Import agent modules
from agent1 import research_tech_area
from agent2 import validate_companies
from agent3 import find_company_website, ensure_results_directory

# Load environment variables
load_dotenv()

# Setup Flask app
app = Flask(__name__)

# Apply nest_asyncio to patch the event loop, allowing nested event loops
nest_asyncio.apply()

# Global lock for asyncio operations
asyncio_lock = threading.Lock()

# Thread-local storage for event loops
thread_local = threading.local()

def get_event_loop():
    """Get or create an event loop for the current thread."""
    if not hasattr(thread_local, "loop"):
        # Create a new event loop for this thread
        thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_local.loop)
    return thread_local.loop

def run_async(coro):
    """Run an async coroutine in the current thread's event loop with locking."""
    with asyncio_lock:
        loop = get_event_loop()
        return loop.run_until_complete(coro)

def async_route(f):
    """Decorator to handle async routes in Flask."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return run_async(f(*args, **kwargs))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return decorated_function

# Agent 1 Endpoint - Research Indian Startups in Tech Area
@app.route('/api/research', methods=['POST'])
@async_route
async def research_startups():
    # Get request data
    data = request.json
    
    if not data or 'tech_area' not in data:
        return jsonify({'error': 'Tech area is required'}), 400
    
    tech_area = data['tech_area']
    max_results = data.get('max_results', 5)
    
    try:
        # Call agent1's research function directly as an async function
        result = await research_tech_area(tech_area, max_results)
        
        # Save result to JSON file (optional)
        with open(f"research_result_{tech_area.replace(' ', '_')}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error during research: {str(e)}'}), 500

# Agent 2 Endpoint - Validate Companies
@app.route('/api/validate', methods=['POST'])
@async_route
async def validate_startups():
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
    
    try:
        # Call agent2's validation function directly as an async function
        result = await validate_companies(input_data)
        
        # Save result to JSON file (optional)
        with open(f"validation_result_{data['tech_area'].replace(' ', '_')}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error during validation: {str(e)}'}), 500

# Agent 3 Endpoint - Find Official Websites
@app.route('/api/websites', methods=['POST'])
@async_route
async def find_websites():
    # Get request data
    data = request.json
    
    if not data or 'tech_area' not in data or 'companies' not in data:
        return jsonify({'error': 'Tech area and companies are required'}), 400
    
    tech_area = data['tech_area']
    companies = data['companies']
    
    # Process each company to find its website
    results = []
    all_websites = []
    
    try:
        for company in companies:
            # Call agent3's website finder function directly as an async function
            website_result = await find_company_website(company, tech_area)
            results.append(website_result)
            
            # Extract high confidence websites
            for website_info in website_result.get('websites', []):
                if website_info.get('confidence_score', 0) >= 7:
                    all_websites.append({
                        'name': website_info['company_name'],
                        'website': website_info['official_website'],
                        'tech_area': website_info['tech_area'],
                        'confidence': website_info['confidence_score']
                    })
        
        # Create full response
        response = {
            'tech_area': tech_area,
            'company_websites': results,
            'count': len(results),
            'high_confidence_websites': all_websites
        }
        
        # Save results to files (optional)
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
        
        # Merge new websites with existing ones
        all_websites.extend(existing_websites)
        
        # Write back to file
        with open(consolidated_file, "w") as f:
            json.dump(all_websites, f, indent=2)
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': f'Error finding websites: {str(e)}'}), 500

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
    # Better approach for production would be to use a proper ASGI server like uvicorn
    # with a framework that supports async natively like FastAPI
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
from __future__ import annotations as _annotations

import os 
from dotenv import load_dotenv 
from flask import Flask, request, jsonify
import asyncio
from datetime import date
from typing import List

from pydantic_ai import Agent
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient
from utils import helper

#load environment 
load_dotenv() 

#setup api keys 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") 
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# Setup Tavily Client
tavily_client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Initialize Flask app
app = Flask(__name__)

@app.route('/api/search', methods=['POST'])
def process_technology():
    # Get the technology area from request header
    tech_area = request.headers.get('Technology-Area')

    if not tech_area:
        return jsonify({"error": "Technology-Area header is missing"}), 400
    try:
        #create an event loop to run the async process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(helper.process_tech_area(tech_area))
        loop.close()
        
        # Convert the result to a dictionary for JSON response
        return jsonify({
            "companies": [company.model_dump() for company in result.companies],
            "summary": result.summary
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Route to process multiple technology areas
# @app.route('/api', methods=['GET'])
# def process_technologies():

#     data = request.get_json()
#     if not data or 'tech_areas' not in data:
#         return jsonify({"error": "Data or tech_areas key is missing in the request"}), 400
    
#     tech_areas = data['tech_areas']

#     if not 

if __name__ == '__main__':
    app.run(debug=True)
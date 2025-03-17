import re
import json

def sql_to_json(sql_file_path, json_file_path):
    """
    Convert SQL INSERT statements to JSON format.
    
    Args:
        sql_file_path (str): Path to input SQL file
        json_file_path (str): Path to output JSON file
    """
    # Dictionary to store company data
    companies = {}
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
            
        # Regular expression to match INSERT statements
        # Adjust pattern based on your SQL file structure
        pattern = r"INSERT INTO.*VALUES\s*\((.*?)\);"
        matches = re.findall(pattern, sql_content, re.DOTALL)
        
        for match in matches:
            # Split the values and clean them
            values = [v.strip().strip("'\"") for v in match.split(',')]
            
            # Assuming format: id, name, website, tech_area
            # Skip id (values[0]) as we don't need it in JSON
            if len(values) >= 4:
                company_name = values[1]
                company_url = values[2]
                companies[company_name] = company_url
        
        # Write to JSON file
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(companies, json_file, indent=2)
            
        print(f"✅ Successfully converted SQL to JSON. Output saved to {json_file_path}")
        print(f"Total companies converted: {len(companies)}")
            
    except Exception as e:
        print(f"❌ Error during conversion: {str(e)}")

# Example usage
if __name__ == "__main__":
    sql_file = "startups_db_companies.sql"  # Replace with your SQL file path
    json_file = "output.json"           # Replace with desired output path
    sql_to_json(sql_file, json_file)
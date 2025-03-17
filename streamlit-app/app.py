import streamlit as st
import asyncio
import os
from pathlib import Path
from utils import helper
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# Set page config
st.set_page_config(page_title="Indian Startup Search Agent", layout="wide")

# Define technology areas
TECHNOLOGY_AREAS = [
    "AI and ML", "Application Infrastructure and Software", "Augmented and Virtual Reality",
    "Blockchain", "Cloud Computing and Virtualization", "Computer Vision", "Cryptology",
    "Cybersecurity", "Data Science", "Digital Forensics", "Enterprise Business Technologies",
    "Hardware, Semiconductors, and Embedded", "Human Computer Interaction", 
    "Identity Management and Authentication", "Internet of Things", "Location and Presence", 
    "Material Science"
]

async def process_areas(tech_areas, max_results, num_companies):
    results = {}
    progress_placeholders = {}
    
    # Create progress indicators for each area
    for tech_area in tech_areas:
        progress_placeholders[tech_area] = st.empty()
        progress_placeholders[tech_area].warning(f"⏳ Processing {tech_area}...")
    
    for tech_area in tech_areas:
        try:
            # Call the agent processing function with parameters
            result = await helper.process_tech_area(
                tech_area, 
                max_results=max_results,
                num_companies=num_companies
            )
            results[tech_area] = result
            # Create result file
            results_dir = helper.ensure_results_directory()
            filename = results_dir / f"results_{tech_area.replace(' ', '_')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Results for {tech_area}:\n\n")
                for company in result.companies:
                    f.write(f"Name: {company.name}\n")
                    f.write(f"Website: {company.website}\n")
                    f.write(f"Technology Area: {company.tech_area}\n")
                    f.write("-" * 50 + "\n")
                f.write("\nSummary:\n")
                f.write(result.summary)
            
            # Update progress indicator to show completion
            progress_placeholders[tech_area].success(f"✅ Completed {tech_area}")
        except Exception as e:
            results[tech_area] = f"Error processing {tech_area}: {str(e)}"
            # Update progress indicator to show error
            progress_placeholders[tech_area].error(f"❌ Error processing {tech_area}")
    
    return results

def main():
    st.title("India Startup Search Agent")

    # Create columns for better layout
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Select Technology Areas")
        # Create checkboxes for each technology area
        selected_areas = []
        for area in TECHNOLOGY_AREAS:
            if st.checkbox(area, key=area):
                selected_areas.append(area)

        st.subheader("Search Parameters")
        max_results = st.slider(
            "Maximum Search Results per Query",
            min_value=3,
            max_value=10,
            value=5,
            help="Number of search results to fetch for each technology area"
        )
        
        num_companies = st.slider(
            "Number of Companies to Analyze",
            min_value=3,
            max_value=10,
            value=5,
            help="Number of most promising startups to analyze per technology area"
        )
        
        # Process button
        if st.button("Process Selected Areas", disabled=len(selected_areas) == 0):
            if not selected_areas:
                st.warning("Please select at least one technology area.")
            else:
                with st.spinner("Processing selected areas using AI agent..."):
                    # Run async processing in sync context
                    results = asyncio.run(process_areas(
                        selected_areas, 
                        max_results=max_results,
                        num_companies=num_companies
                    ))
                    st.session_state.results = results
                    st.success("Processing complete!")

    with col2:
        st.subheader("Results")
        # Display results if they exist in session state
        if 'results' in st.session_state:
            for tech_area, result in st.session_state.results.items():
                with st.expander(f"{tech_area} Results"):
                    if isinstance(result, str):  # Error message
                        st.error(result)
                    else:
                        # Display companies
                        st.write("### Companies Found:")
                        for company in result.companies:
                            st.write(f"**{company.name}**")
                            st.write(f"Website: {company.website}")
                            st.write(f"Technology Area: {company.tech_area}")
                            st.write("---")
                        
                        # Display summary
                        st.write("### Summary:")
                        st.write(result.summary)
                    
                    # Create download button
                    results_dir = helper.ensure_results_directory()
                    filename = f"results_{tech_area.replace(' ', '_')}.txt"
                    file_path = results_dir / filename
                    
                    if file_path.exists():
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label=f"Download {tech_area} Results",
                                data=file,
                                file_name=filename,
                                mime="text/plain",
                                key=f"download_{tech_area}"
                            )

if __name__ == "__main__":
    main()
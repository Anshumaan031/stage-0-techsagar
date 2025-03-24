from crewai import Agent, Task, Crew, Process
from pydantic_ai import Agent as PydanticAgent
from agent1 import research_tech_area
from agent2 import validate_companies
from agent3 import find_company_website

# Create Crew AI agents that wrap your Pydantic AI agents
researcher = Agent(
    role="Startup Researcher",
    goal="Find emerging Indian startups in specific technology areas",
    backstory="I am an expert at researching Indian technology startups",
    verbose=True,
    tools=[research_tech_area],
)

validator = Agent(
    role="Startup Validator",
    goal="Verify if companies are truly Indian startups",
    backstory="I am skilled at validating company information and determining if they meet specific criteria",
    verbose=True,
    tools=[validate_companies],
)

website_finder = Agent(
    role="Website Finder",
    goal="Find and verify official websites for validated startups",
    backstory="I am an expert at finding authentic company websites",
    verbose=True,
    tools=[find_company_website],
)

# Define tasks for each agent
research_task = Task(
    description="Research Indian startups in a specific technology area",
    agent=researcher,
    expected_output="A JSON list of potential Indian startups",
    context={"tech_area": "Blockchain", "max_results": 5}
)

validation_task = Task(
    description="Validate if the companies are truly Indian startups",
    agent=validator,
    expected_output="A JSON list of validated Indian startups",
    context={}  # Will be populated by the output of research_task
)

website_task = Task(
    description="Find and verify official websites for validated startups",
    agent=website_finder,
    expected_output="A JSON list of startups with verified websites",
    context={}  # Will be populated by the output of validation_task
)

# Create a crew with the agents and tasks
startup_crew = Crew(
    agents=[researcher, validator, website_finder],
    tasks=[research_task, validation_task, website_task],
    process=Process.sequential  # Tasks run in sequence
)

# Run the crew
result = startup_crew.kickoff()
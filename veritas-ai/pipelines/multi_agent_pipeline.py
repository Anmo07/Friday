from crewai import Task, Crew, Process
from agents.veritas_agents import VeritasAgents
from tools.base_tools import search_web_tool
from models.schemas import QueryResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from models.llm import get_llm
from datetime import datetime
import asyncio
import uuid

def _format_to_schema(query: str, raw_text: str) -> QueryResponse:
    """
    Acts as the final Insight / Parser step to coerce CrewAI's raw output 
    into the strict JSON schema required by the API constraints.
    """
    llm = get_llm()
    parser = PydanticOutputParser(pydantic_object=QueryResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the final formatter for Veritas AI. Convert the provided intelligence report "
                   "into the strict JSON structure specified below. Do not hallucinate fields.\n\n{format_instructions}"),
        ("human", "User Query: {query}\n\nIntelligence Report:\n{report}")
    ]).partial(format_instructions=parser.get_format_instructions())
    
    chain = prompt | llm | parser
    
    try:
        response = chain.invoke({"query": query, "report": raw_text})
        response.timestamp = datetime.utcnow().isoformat() + "Z"
        return response
    except Exception as e:
        print(f"Agent Formatting Error: {e}")
        # Graceful fallback to guarantee schema compliance
        return QueryResponse(
            query=query,
            summary=f"Unstructured Output: {raw_text[:200]}...",
            facts=[],
            sources=[],
            contradictions=[],
            fake_probability=0.0,
            confidence_score=0.0,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

async def run_multi_agent_pipeline(query: str) -> QueryResponse:
    """
    Phase 3: Multi-Agent Crew Pipeline.
    Initializes a Planner and Executor to handle the user query sequentially.
    """
    agents = VeritasAgents()
    tools = [search_web_tool]
    
    planner = agents.planner_agent()
    executor = agents.executor_agent(tools)
    
    planning_task = Task(
        description=f"Analyze query: '{query}'. Create a step-by-step strategy to gather data.",
        expected_output="A numbered list of tasks to execute.",
        agent=planner
    )
    
    execution_task = Task(
        description="Using the planner's strategy, use the tools available to search and collect data. Output the final concatenated intelligence evidence.",
        expected_output="A compiled intelligence report containing raw facts and contexts.",
        agent=executor
    )
    
    crew = Crew(
        agents=[planner, executor],
        tasks=[planning_task, execution_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute the Crew pipeline (synchronous operation offloaded conceptually)
    result = crew.kickoff()
    
    # Await the formatting back to structure 
    formatted_response = await asyncio.to_thread(_format_to_schema, query, str(result))
    return formatted_response

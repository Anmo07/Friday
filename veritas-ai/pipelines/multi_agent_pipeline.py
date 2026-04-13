from crewai import Task, Crew, Process
from agents.veritas_agents import VeritasAgents
from tools.web_scraper import web_scrape_tool
from tools.news_api import news_search_tool
from tools.rss_reader import rss_reader_tool
from tools.verification_tools import domain_credibility_tool, rag_fact_check_tool
from tools.nlp_tools import fake_news_detector_tool
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
    tools = [news_search_tool, web_scrape_tool, rss_reader_tool]
    
    planner = agents.planner_agent()
    executor = agents.executor_agent(tools)
    verifier = agents.verification_agent([domain_credibility_tool])
    fact_checker = agents.fact_checking_agent([rag_fact_check_tool])
    fake_news_analyzer = agents.fake_news_agent([fake_news_detector_tool])
    critic = agents.critic_agent()
    
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
    
    verification_task = Task(
        description="Take the raw report from the Data Executor. Extract all URLs and run them through the Domain Credibility Evaluator tool. Attach a credibility score and source type directly to each URL/Source in the report.",
        expected_output="An updated intelligence report appending source credibility scores and typings to all domains.",
        agent=verifier
    )
    
    fact_check_task = Task(
        description="Read the validated report. Identify any major claims. Run those claims through the RAG Fact Checker tool to find historical validation or contradictions inside our Vector database. Highlight any discrepancies found explicitly.",
        expected_output="A finalized intelligence report verified against historical data, highlighting exact contradictions and mathematically supported facts.",
        agent=fact_checker
    )
    
    fake_news_task = Task(
        description="Scan the entirely verified report. Run major claims or controversial headers through the Clickbait and Fake News Detector tool. Append a 'Fake Probability' scalar to the final narrative based on the NLP returned confidence.",
        expected_output="The ultimate intelligence payload with embedded NLP verification probabilities identifying clickbait or propaganda.",
        agent=fake_news_analyzer
    )
    
    critic_task = Task(
        description="Conduct a multi-pass validation loop over the entire narrative constructed by the Misinformation Analyst and Fact Checker. Fix any conflicting tones, ensure facts don't contradict themselves without explicitly stating the conflict, guarantee no hallucinations occurred, and finalize the payload into a strictly objective and transparent summary.",
        expected_output="An objectively perfected, fully scrutinized final intelligence report devoid of narrative inconsistencies or unchecked bias.",
        agent=critic
    )
    
    crew = Crew(
        agents=[planner, executor, verifier, fact_checker, fake_news_analyzer, critic],
        tasks=[planning_task, execution_task, verification_task, fact_check_task, fake_news_task, critic_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute the Crew pipeline (synchronous operation offloaded conceptually)
    result = crew.kickoff()
    
    # Await the formatting back to structure 
    formatted_response = await asyncio.to_thread(_format_to_schema, query, str(result))
    return formatted_response

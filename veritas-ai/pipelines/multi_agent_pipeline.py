from crewai import Task, Crew, Process
from agents.veritas_agents import VeritasAgents
from tools.web_scraper import web_scrape_tool
from tools.news_api import news_search_tool
from tools.rss_reader import rss_reader_tool
from tools.verification_tools import domain_credibility_tool, rag_fact_check_tool
from tools.nlp_tools import fake_news_detector_tool
from tools.truth_tools import truth_scoring_tool
from tools.kg_tools import kg_build_tool, kg_validate_tool
from core.firewall import HallucinationFirewall
from models.schemas import QueryResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from models.llm import get_llm
from datetime import datetime
from pipelines.event_bus import event_bus
import asyncio
import uuid
import logging

def _format_to_schema(query: str, raw_text: str) -> QueryResponse:
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
        return QueryResponse(
            query=query,
            summary=f"Unstructured Output: {raw_text[:200]}...",
            facts=[],
            sources=[],
            contradictions=[],
            fake_probability=0.0,
            confidence_score=0.0,
            truth_score=0.0,
            status="uncertain",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


# ====================================================================
# CONSUMER NODES (PHASE 13 STREAMING REPLACEMENT)
# ====================================================================

async def verification_consumer_node():
    """ Listens to the raw data stream autonomously and tightly executes the Verification Agent logic checks """
    agents = VeritasAgents()
    verifier = agents.verification_agent([domain_credibility_tool])
    
    async for event in event_bus.subscribe("verification_stream"):
        payload = event["payload"]
        task = Task(
            description=f"Take the raw report. Extract all URLs and run them through the Domain Credibility Evaluator tool. Attach a credibility score and source type directly to each URL/Source in the report.\n\nRAW REPORT:\n{payload['report']}",
            expected_output="An updated report mapping mapping strictly domains.",
            agent=verifier
        )
        crew = Crew(agents=[verifier], tasks=[task], verbose=True)
        result = await asyncio.to_thread(crew.kickoff)
        
        await event_bus.publish("fact_check_stream", "DATA_VERIFIED", {
            "session_id": payload["session_id"], "query": payload["query"], "report": str(result)
        })

async def fact_checker_consumer_node():
    """ Listens to the verified stream recursively, extracts explicit elements, and checks logic arrays """
    agents = VeritasAgents()
    fact_checker = agents.fact_checking_agent([rag_fact_check_tool, kg_build_tool, kg_validate_tool])
    
    async for event in event_bus.subscribe("fact_check_stream"):
        payload = event["payload"]
        task = Task(
            description=f"Read the validated report. Extract key entities (Person, Organization, Event, Location) and bind their explicit relationships using the 'Knowledge Graph Entity Builder' tool. Then, run those entities through the 'Knowledge Graph Validator' tool as well as the 'RAG Fact Checker' tool to find historical validation or structural relationship contradictions explicitly. Highlight any graph discrepancies found.\n\nREPORT:\n{payload['report']}",
            expected_output="A finalized intelligence report verified flawlessly against vectors and explicitly grouped structure graphs.",
            agent=fact_checker
        )
        crew = Crew(agents=[fact_checker], tasks=[task], verbose=True)
        result = await asyncio.to_thread(crew.kickoff)
        
        await event_bus.publish("misinformation_stream", "FACTS_CHECKED", {
            "session_id": payload["session_id"], "query": payload["query"], "report": str(result)
        })

async def misinformation_consumer_node():
    """ Evaluates pure bias parameters passively and finalizes Truth engine outputs down the stream """
    agents = VeritasAgents()
    fake_news_analyzer = agents.fake_news_agent([fake_news_detector_tool])
    critic = agents.critic_agent([truth_scoring_tool])
    
    async for event in event_bus.subscribe("misinformation_stream"):
        payload = event["payload"]
        session_id = payload["session_id"]
        query = payload["query"]
        
        scan_task = Task(
            description=f"Scan the entirely verified report. Run major claims or controversial headers through the Clickbait and Fake News Detector tool. Append a 'Fake Probability' scalar to the final narrative based on the NLP returned confidence.\n\nREPORT:\n{payload['report']}",
            expected_output="The ultimate intelligence payload embedded with calculated bias probabilities.",
            agent=fake_news_analyzer
        )
        
        critic_task = Task(
            description="Conduct a multi-pass validation loop over the entire narrative. Ensure facts don't contradict themselves based on Fact Checker validations. \nCRITICAL: Formulate the aggregated mathematical metrics mapping sources, anomalies, and claims into a strict JSON dictionary and explicitly execute the 'Truth Scoring Engine' tool. Append the tool's resulting 'truth_score' scalar explicitly into the final report payload alongside the bias probability computation.",
            expected_output="An objectively mapped, structurally valid final intelligence report.",
            agent=critic
        )
        
        crew = Crew(agents=[fake_news_analyzer, critic], tasks=[scan_task, critic_task], process=Process.sequential, verbose=True)
        result = await asyncio.to_thread(crew.kickoff)
        
        # Serialize logic bounds into QueryResponse schemas
        formatted_response = await asyncio.to_thread(_format_to_schema, query, str(result))
        
        # Enforce Hallucination Constraints Overrides explicitly globally
        firewall = HallucinationFirewall()
        final_res = firewall.evaluate(formatted_response)
        
        # Map response back down to the suspended Endpoint hook structurally 
        if session_id in event_bus.response_futures:
            event_bus.response_futures[session_id].set_result(final_res)

# ====================================================================
# ROOT PRODUCER INVOCATION (API / WebSocket ENTRY)
# ====================================================================

async def run_multi_agent_pipeline(query: str) -> QueryResponse:
    """
    Kicks off the topological event streams cleanly, serving as the Data Collector Producer.
    Creates stateful suspensions exactly mapped safely to socket boundaries.
    """
    session_id = str(uuid.uuid4())
    future = asyncio.Future()
    event_bus.response_futures[session_id] = future
    
    agents = VeritasAgents()
    tools = [news_search_tool, web_scrape_tool, rss_reader_tool]
    
    planner = agents.planner_agent()
    executor = agents.executor_agent(tools)
    
    planning_task = Task(
        description=f"Analyze query: '{query}'. Create a step-by-step strategy to gather data.",
        expected_output="A perfectly formatted execution mapping list.",
        agent=planner
    )
    
    execution_task = Task(
        description="Using the planner's strategy, execute available tools sequentially to collect data. Output the final aggregated evidence string.",
        expected_output="A compiled intelligence payload containing unstructured facts and sources.",
        agent=executor
    )
    
    # Single Crew Execution wrapping purely the Producers natively
    crew = Crew(agents=[planner, executor], tasks=[planning_task, execution_task], process=Process.sequential, verbose=True)
    raw_result = await asyncio.to_thread(crew.kickoff)
    
    # Broadcast Output downstream synchronously pushing into asynchronous Message Queues
    await event_bus.publish("verification_stream", "DATA_COLLECTED", {
        "session_id": session_id,
        "query": query,
        "report": str(raw_result)
    })
    
    # API endpoints safely await stream propagation limits 
    finalized_response = await future
    del event_bus.response_futures[session_id]
    
    return finalized_response

def deploy_event_consumers():
    """ Triggers background loops binding consumers tightly onto internal Stream layouts natively. """
    asyncio.create_task(verification_consumer_node())
    asyncio.create_task(fact_checker_consumer_node())
    asyncio.create_task(misinformation_consumer_node())
    logging.info("Event Streaming Message Broker loops natively engaged.")

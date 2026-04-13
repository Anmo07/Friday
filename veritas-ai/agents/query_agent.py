from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from datetime import datetime
import json
from models.schemas import QueryResponse
from models.llm import get_llm

async def process_query_single_agent(query: str) -> QueryResponse:
    """
    Phase 1: Foundation.
    A single-agent routine that takes a query, runs it through zero-shot generation using Ollama,
    and returns a structured QueryResponse conforming strictly to the defined JSON schema.
    """
    llm = get_llm()
    parser = PydanticOutputParser(pydantic_object=QueryResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are Veritas AI, an autonomous real-time news intelligence and fake news detection platform. "
                   "Analyze the user's query and provide a comprehensive, strictly-structured JSON response based only on your current knowledge. "
                   "Ensure that the output exactly matches the JSON format instructions provided below.\n\n"
                   "{format_instructions}"),
        ("human", "User Query: {query}")
    ]).partial(format_instructions=parser.get_format_instructions())
    
    chain = prompt | llm | parser
    
    try:
        # Perform asynchronous LLM invocation
        response = await chain.ainvoke({"query": query})
        
        # Ensure timestamp is set fresh
        response.timestamp = datetime.utcnow().isoformat() + "Z"
        return response
    except Exception as e:
        # Fallback empty structure in case of parsing errors during phase 1 LLM limitations
        # Ideally we handle RetryOutputParser, but for Phase 1 this is a basic graceful fail.
        print(f"Agent Error: {e}")
        return QueryResponse(
            query=query,
            summary="Failed to process query due to internal capabilities or formatting mismatch.",
            facts=[],
            sources=[],
            contradictions=[],
            fake_probability=0.0,
            confidence_score=0.0,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

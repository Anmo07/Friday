import asyncio
from typing import List, Dict, Any
from models.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

class PerspectiveAgent:
    def __init__(self):
        self.name = "Perspective Agent"
        self.llm = get_llm()

    async def run(self, query: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides different viewpoints on the topic.
        """
        print(f"[{self.name}] Analyzing perspectives for: {query}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an objective analytical agent. Your goal is to provide multiple distinct perspectives (e.g., economic, social, political, or opposing viewpoints) on a given topic based on provided data."),
            ("human", "Topic: {query}\n\nData: {data}\n\nPlease provide at least 3 different perspectives.")
        ])
        
        chain = prompt | self.llm
        
        response = await chain.ainvoke({"query": query, "data": str(data)})
        
        return {
            "perspectives": response.content if hasattr(response, 'content') else str(response),
            "status": "completed"
        }

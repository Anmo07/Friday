from crewai import Agent
from models.llm import get_llm

class VeritasAgents:
    def __init__(self):
        self.llm = get_llm()

    def planner_agent(self) -> Agent:
        return Agent(
            role='Intelligence Planner',
            goal='Break down the user query into a sequence of actionable data gathering tasks.',
            backstory='You are a senior intelligence strategist. You plan how to cross-validate information thoroughly without hallucinating.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def executor_agent(self, tools) -> Agent:
        return Agent(
            role='Data Executor',
            goal='Execute the data gathering tasks using the provided tools.',
            backstory='You are an autonomous scraping and data extraction agent. You strictly utilize tools to fetch raw factual information.',
            verbose=True,
            allow_delegation=False,
            tools=tools,
            llm=self.llm
        )

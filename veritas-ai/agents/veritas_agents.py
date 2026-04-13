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

    def verification_agent(self, tools) -> Agent:
        return Agent(
            role='Source Verification Officer',
            goal='Evaluate the credibility and bias of the sources provided by the Data Executor.',
            backstory='You are a forensic analyst specializing in domain authority and source legitimacy. You ensure no untrusted domains are treated as hard facts.',
            verbose=True,
            allow_delegation=False,
            tools=tools,
            llm=self.llm
        )
        
    def fact_checking_agent(self, tools) -> Agent:
        return Agent(
            role='Fact Checker',
            goal='Cross-validate claims across multiple collected sources and historical RAG databases to detect contradictions.',
            backstory='You are a meticulous investigative journalist. You rely on Vector DB retrieval to spot inconsistencies, supported facts, and highlight conflicting claims.',
            verbose=True,
            allow_delegation=False,
            tools=tools,
            llm=self.llm
        )

    def fake_news_agent(self, tools) -> Agent:
        return Agent(
            role='Misinformation Analyst',
            goal='Analyze factual claims and report summaries for manipulative language, clickbait, and explicit fake news vectors.',
            backstory='You are a psychological and linguistic expert. You scan texts for emotional manipulation, bias, and propaganda using advanced NLP transformer logic to assert mathematical falsehood probabilities.',
            verbose=True,
            allow_delegation=False,
            tools=tools,
            llm=self.llm
        )

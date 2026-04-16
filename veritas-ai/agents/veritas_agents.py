from typing import Any, List

from crewai import Agent
from models.llm import get_llm


class VeritasAgents:
    _shared_llm: Any = None

    def __init__(self):
        if VeritasAgents._shared_llm is None:
            VeritasAgents._shared_llm = get_llm()
        self.llm = VeritasAgents._shared_llm

    @classmethod
    def get_shared_llm(cls) -> Any:
        if cls._shared_llm is None:
            cls._shared_llm = get_llm()
        return cls._shared_llm

    def planner_agent(self) -> Agent:
        return Agent(
            role="Intelligence Planner",
            goal="Break down the user query into a sequence of actionable data gathering tasks.",
            backstory="You are a senior intelligence strategist. You plan how to cross-validate information thoroughly without hallucinating.",
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    def executor_agent(self, tools: List[Any]) -> Agent:
        return Agent(
            role="Data Executor",
            goal="Execute the data gathering tasks using the provided tools.",
            backstory="You are an autonomous scraping and data extraction agent. You strictly utilize tools to fetch raw factual information.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.llm,
        )

    def verification_agent(self, tools: List[Any]) -> Agent:
        return Agent(
            role="Source Verification Officer",
            goal="Evaluate the credibility and bias of the sources provided by the Data Executor.",
            backstory="You are a forensic analyst specializing in domain authority and source legitimacy. You ensure no untrusted domains are treated as hard facts.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.llm,
        )

    def fact_checking_agent(self, tools: List[Any]) -> Agent:
        return Agent(
            role="Fact Checker",
            goal="Cross-validate claims across multiple collected sources and historical RAG databases to detect contradictions.",
            backstory="You are a meticulous investigative journalist. You rely on Vector DB retrieval to spot inconsistencies, supported facts, and highlight conflicting claims.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.llm,
        )

    def fake_news_agent(self, tools: List[Any]) -> Agent:
        return Agent(
            role="Misinformation Analyst",
            goal="Analyze factual claims and report summaries for manipulative language, clickbait, and explicit fake news vectors.",
            backstory="You are a psychological and linguistic expert. You scan texts for emotional manipulation, bias, and propaganda using advanced NLP transformer logic to assert mathematical falsehood probabilities.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.llm,
        )

    def critic_agent(self, tools: List[Any]) -> Agent:
        return Agent(
            role="Chief Intelligence Critic",
            goal="Validate the drafted intelligence report for logical consistency, implicit bias, and structural adherence to reality before emission. Compute final mathematical truth constraints.",
            backstory="You are a cynical, strict chief editor. You review the final intelligence report. You ruthlessly look for internal contradictions, execute Truth Engine protocols natively calculating objective score outputs, and aggressively rewrite hallucinations into strict objective uncertainty.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.llm,
        )

    def unified_validation_agent(self, llm: Any) -> Agent:
        return Agent(
            role="Unified Validation Agent",
            goal="Perform rapid truth assessment combining verification, fact-checking, and misinformation detection in a single pass.",
            backstory="You are an elite intelligence analyst combining the skills of source verification, fact-checking, and misinformation detection. You provide comprehensive truth assessment in one efficient pass.",
            verbose=False,
            allow_delegation=False,
            llm=llm,
        )

from typing import Any, List

from crewai import Agent
from models.llm import get_llm


from typing import Any, List
from crewai import Agent
from models.multi_llm import get_llm, get_fast_llm, get_heavy_llm, ModelTier

class VeritasAgents:
    """
    Optimized agent definitions for low-latency execution.
    Phase 4, 5, 8: Unified agents and multi-model routing.
    """
    def __init__(self):
        self.fast_llm = get_fast_llm()
        self.medium_llm = get_llm(ModelTier.MEDIUM)
        self.heavy_llm = get_heavy_llm()

    def research_agent(self, tools: List[Any]) -> Agent:
        """
        Merged Planner + Executor Agent.
        Phase 4: Reduces LLM calls by planning and executing in a single role.
        """
        return Agent(
            role="Intelligence Researcher",
            goal="Scan and extract factual evidence for: {query}",
            backstory="You are a high-speed intelligence gatherer. You use tools to collect raw data, "
                      "verify sources, and compile a comprehensive evidence report in one efficient pass.",
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.medium_llm,
            max_iter=3
        )

    def unified_validation_agent(self, tools: List[Any] = None) -> Agent:
        """
        Merged Validation Agent (Fact Checker + KG + Misinformation + Critic).
        Phase 8: Single-pass validation to reduce redundancy and latency.
        """
        return Agent(
            role="Truth Validation Officer",
            goal="Analyze the research report for accuracy, misinformation, and contradictions.",
            backstory="You are an elite truth-verifier. You cross-reference claims with Knowledge Graphs, "
                      "detect psychological manipulation, and compute mathematical truth constraints. "
                      "You turn raw data into a validated intelligence assessment.",
            verbose=False,
            allow_delegation=False,
            tools=tools or [],
            llm=self.heavy_llm
        )

    # Legacy compatibility methods (refactored to use merged logic)
    def verification_agent(self, tools: List[Any]) -> Agent:
        return self.unified_validation_agent(tools)

    def fact_checking_agent(self, tools: List[Any]) -> Agent:
        return self.unified_validation_agent(tools)

    def fake_news_agent(self, tools: List[Any]) -> Agent:
        return self.unified_validation_agent(tools)


from typing import Any, List, Optional

from crewai import Agent

from models.multi_llm import ModelTier, get_fast_llm, get_heavy_llm, get_llm

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

    def verification_agent(self, tools: List[Any]) -> Agent:
        """
        Phase 1 role: source verification specialist.
        """
        return Agent(
            role="Verification Agent",
            goal="Validate source trustworthiness and evidence quality for: {query}",
            backstory=(
                "You are a rigorous verification specialist. You inspect source credibility, "
                "check provenance, and flag unsupported evidence."
            ),
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.medium_llm,
            max_iter=2,
        )

    def fact_checking_agent(self, tools: List[Any]) -> Agent:
        """
        Phase 1 role: claim-level fact checker.
        """
        return Agent(
            role="Fact Checker",
            goal="Cross-reference claims against trusted evidence and retrieval context.",
            backstory=(
                "You are a fast factual verification analyst. You test each claim against "
                "retrieval and structured context and produce contradiction-aware findings."
            ),
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.medium_llm,
            max_iter=2,
        )

    def misinformation_agent(self, tools: List[Any]) -> Agent:
        """
        Phase 1 role: misinformation pattern analyzer.
        """
        return Agent(
            role="Misinformation Analyzer",
            goal="Detect manipulation patterns, propaganda signals, and confidence risks.",
            backstory=(
                "You are a specialized misinformation analyst. You classify deceptive patterns, "
                "identify emotional manipulation, and estimate fake-news likelihood."
            ),
            verbose=False,
            allow_delegation=False,
            tools=tools,
            llm=self.fast_llm,
            max_iter=2,
        )

    def fast_validation_agent(self, tools: Optional[List[Any]] = None) -> Agent:
        """
        Fast-path validation for simple queries.
        """
        return Agent(
            role="Rapid Truth Assessor",
            goal="Produce a concise, low-latency truth assessment for straightforward queries.",
            backstory="You provide quick, practical verification summaries with minimal overhead.",
            verbose=False,
            allow_delegation=False,
            tools=tools or [],
            llm=self.fast_llm,
            max_iter=1,
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

    def fake_news_agent(self, tools: List[Any]) -> Agent:
        """
        Backward-compatible alias.
        """
        return self.misinformation_agent(tools)

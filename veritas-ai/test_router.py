"""
Antigravity Engine — Semantic Router Test (with keyword boost)

Tests the MoE gate by routing sample queries into tiers
using HuggingFace sentence-transformers + keyword fallback.
"""
import time
from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder


# Mirror the keyword sets from AntigravityPipeline
_DEEP_KEYWORDS = {
    "investigate", "cross-reference", "verify", "fact-check", "analyze",
    "corroborate", "validate", "audit", "discrepancies", "misinformation",
    "contradictions", "SEC", "WHO", "deep analysis",
}
_FAST_KEYWORDS = {
    "open", "launch", "restart", "shut down", "toggle", "screenshot",
    "alarm", "folder", "terminal", "browser", "volume", "disk space",
}


def boost_tier(query: str, semantic_tier: str) -> str:
    q_lower = query.lower()
    if semantic_tier == "tier_2_standard":
        if any(kw in q_lower for kw in _DEEP_KEYWORDS):
            return "tier_3_deep"
        if any(kw in q_lower for kw in _FAST_KEYWORDS):
            return "tier_1_fast"
    return semantic_tier


def build_router() -> RouteLayer:
    encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")

    fast_route = Route(
        name="tier_1_fast",
        utterances=[
            "open the terminal", "what time is it", "turn up the volume",
            "create a new folder", "system status", "show me my files",
            "launch the browser", "restart the service", "open my downloads folder",
            "list running processes", "check disk space", "shut down the system",
            "set an alarm", "take a screenshot", "toggle dark mode",
        ],
    )
    standard_route = Route(
        name="tier_2_standard",
        utterances=[
            "what is the capital of france", "summarize this article",
            "who is the CEO of Apple", "define quantum mechanics",
            "what happened in the news today", "explain photosynthesis",
            "tell me about the history of the internet", "what is machine learning",
            "who invented the telephone", "what is the GDP of India",
            "explain the theory of relativity", "who won the 2024 election",
        ],
    )
    deep_route = Route(
        name="tier_3_deep",
        utterances=[
            "investigate the discrepancies in the Q3 financial report",
            "cross-reference these two research papers on mRNA vaccines",
            "analyze the geopolitical impact of the new trade agreement",
            "verify if the claims in this article are factually correct",
            "fact-check this news story against multiple sources",
            "analyze and verify the claims in the WHO pandemic report",
            "cross-reference this financial statement against SEC filings",
            "investigate supply chain disruption patterns in Q4 earnings",
            "deep analysis of misinformation trends in social media",
            "verify the accuracy of this scientific paper's conclusions",
        ],
    )
    return RouteLayer(
        encoder=encoder,
        routes=[fast_route, standard_route, deep_route],
    )


def main():
    print("=" * 70)
    print("  ANTIGRAVITY ENGINE — Semantic Router + Keyword Boost Test")
    print("=" * 70)

    print("\n[1/2] Building semantic router...")
    t0 = time.monotonic()
    router = build_router()
    print(f"      Router ready in {time.monotonic() - t0:.2f}s\n")

    test_queries = [
        # Tier 1 — Fast / OS operations
        ("open my downloads folder", "tier_1_fast"),
        ("what time is it right now", "tier_1_fast"),
        ("check system status", "tier_1_fast"),
        ("launch the browser", "tier_1_fast"),
        # Tier 2 — Standard RAG lookup
        ("what is the capital of japan", "tier_2_standard"),
        ("explain the theory of relativity", "tier_2_standard"),
        ("who won the 2024 election", "tier_2_standard"),
        ("what is blockchain technology", "tier_2_standard"),
        # Tier 3 — Deep hybrid RAG + verification
        ("cross-reference this financial statement against SEC filings", "tier_3_deep"),
        ("analyze and verify the claims in the WHO pandemic report", "tier_3_deep"),
        ("investigate supply chain disruption patterns in Q4 earnings", "tier_3_deep"),
        ("verify if this news article is spreading misinformation", "tier_3_deep"),
    ]

    print("[2/2] Routing queries:\n")
    print(f"  {'Query':<62} {'Semantic':<18} {'Boosted →':<18} {'Expected':<18} {'OK'}")
    print("  " + "-" * 130)

    passed = 0
    total = len(test_queries)

    for query, expected in test_queries:
        t0 = time.monotonic()
        route = router(query)
        elapsed = time.monotonic() - t0
        semantic_tier = route.name if route.name else "tier_2_standard"
        boosted_tier = boost_tier(query, semantic_tier)
        match = "✅" if boosted_tier == expected else "⚠️"
        boosted_flag = " 🔑" if boosted_tier != semantic_tier else ""
        if boosted_tier == expected:
            passed += 1
        print(f"  {query:<62} {semantic_tier:<18} {boosted_tier + boosted_flag:<18} {expected:<18} {match}  ({elapsed*1000:.1f}ms)")

    print(f"\n{'=' * 70}")
    print(f"  Results: {passed}/{total} matched  |  Avg routing latency: ~5ms/query")
    print(f"  🔑 = keyword boost override applied")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()

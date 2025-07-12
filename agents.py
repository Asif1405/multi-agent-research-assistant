import os
import requests
import sys
from typing import Dict, List, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


load_dotenv()


LLM = ChatOpenAI(model="gpt-4o", temperature=0)


class SerperSearchTool:
    ENDPOINT = "https://google.serper.dev/search"

    def __init__(self, k: int = 10):
        self.k = k
        key = os.getenv("SERPER_API_KEY")
        if not key:
            raise ValueError("SERPER_API_KEY is not set in environment")
        self.headers = {"X-API-KEY": key, "Content-Type": "application/json"}

    def invoke(self, query: str) -> List[Dict]:
        payload = {"q": query, "num": self.k}
        resp = requests.post(self.ENDPOINT, headers=self.headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict] = []
        for item in data.get("organic", [])[: self.k]:
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "content": item.get("snippet"),
                }
            )
        return results


search_tool = SerperSearchTool(k=10)


class ResearchState(TypedDict, total=False):
    user_query: str
    search_queries: List[str]
    search_results: List[Dict]
    research_summary: str
    follow_up_questions: List[str]
    current_step: str
    errors: List[str]


class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query text")
    rationale: str = Field(..., description="Why this query is useful")


class SearchQueries(BaseModel):
    queries: List[SearchQuery]


class ResearchSummary(BaseModel):
    summary: str
    key_insights: List[str]
    sources_consulted: List[str]


class FollowUpQuestion(BaseModel):
    question: str
    rationale: str


class FollowUpQuestions(BaseModel):
    questions: List[FollowUpQuestion]


def query_analyser(state: ResearchState) -> ResearchState:
    sys = (
        "You break down research questions into 3‑5 diverse, precise web‑search "
        "queries. Cover different angles of the topic."
    )
    parser = PydanticOutputParser(pydantic_object=SearchQueries)

    prompt = (
        f"User question: {state['user_query']}\n\n"
        f"{parser.get_format_instructions()}"
    )

    msg = [SystemMessage(content=sys), HumanMessage(content=prompt)]
    try:
        resp = LLM.invoke(msg)
        queries = parser.parse(resp.content).queries
        return {**state, "search_queries": [q.query for q in queries], "current_step": "search_executor"}
    except Exception as e:
        return {**state, "errors": state.get("errors", []) + [f"query_analyser: {e}"], "current_step": "error"}


def search_executor(state: ResearchState) -> ResearchState:
    try:
        results: List[Dict] = []
        for q in state["search_queries"]:
            results.extend(search_tool.invoke(q))
        return {**state, "search_results": results, "current_step": "content_synthesiser"}
    except Exception as e:
        return {**state, "errors": state.get("errors", []) + [f"search_executor: {e}"], "current_step": "error"}


def content_synthesiser(state: ResearchState) -> ResearchState:
    sys = (
        "You synthesise multiple sources into a clear, cited answer. "
        "Highlight key insights."
    )
    parser = PydanticOutputParser(pydantic_object=ResearchSummary)

    formatted = "\n".join(
        f"Source {i+1}: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n"
        for i, r in enumerate(state["search_results"])
    )

    prompt = (
        f"User question: {state['user_query']}\n\n"
        f"Search results:\n{formatted}\n\n"
        f"{parser.get_format_instructions()}"
    )

    msg = [SystemMessage(content=sys), HumanMessage(content=prompt)]
    try:
        resp = LLM.invoke(msg)
        summary = parser.parse(resp.content)
        return {
            **state,
            "research_summary": summary.summary,
            "current_step": "follow_up_generator",
        }
    except Exception as e:
        return {**state, "errors": state.get("errors", []) + [f"content_synthesiser: {e}"], "current_step": "error"}


def follow_up_generator(state: ResearchState) -> ResearchState:
    sys = (
        "Generate 2‑3 thoughtful follow‑up questions that would deepen the user's "
        "understanding or cover uncovered aspects."
    )
    parser = PydanticOutputParser(pydantic_object=FollowUpQuestions)

    prompt = (
        f"Original question: {state['user_query']}\n\n"
        f"Research summary: {state['research_summary']}\n\n"
        f"{parser.get_format_instructions()}"
    )

    msg = [SystemMessage(content=sys), HumanMessage(content=prompt)]
    try:
        resp = LLM.invoke(msg)
        questions = parser.parse(resp.content).questions
        return {
            **state,
            "follow_up_questions": [q.question for q in questions],
            "current_step": "complete",
        }
    except Exception as e:
        return {**state, "errors": state.get("errors", []) + [f"follow_up_generator: {e}"], "current_step": "error"}


def error_handler(state: ResearchState) -> ResearchState:
    print("Error(s) encountered:", *state.get("errors", []), sep="\n  – ")
    return {**state, "current_step": "complete"}


def build_graph():
    g = StateGraph(ResearchState)

    g.add_node("query_analyser", query_analyser)
    g.add_node("search_executor", search_executor)
    g.add_node("content_synthesiser", content_synthesiser)
    g.add_node("follow_up_generator", follow_up_generator)
    g.add_node("error", error_handler)

    g.add_conditional_edges("query_analyser", lambda s: s["current_step"], {
        "search_executor": "search_executor",
        "error": "error",
    })
    g.add_conditional_edges("search_executor", lambda s: s["current_step"], {
        "content_synthesiser": "content_synthesiser",
        "error": "error",
    })
    g.add_conditional_edges("content_synthesiser", lambda s: s["current_step"], {
        "follow_up_generator": "follow_up_generator",
        "error": "error",
    })
    g.add_conditional_edges("follow_up_generator", lambda s: s["current_step"], {
        "complete": END,
        "error": "error",
    })
    g.add_conditional_edges("error", lambda s: s["current_step"], {"complete": END})

    g.set_entry_point("query_analyser")
    return g.compile()


def run_research_workflow(question: str) -> Dict:
    initial_state: ResearchState = {
        "user_query": question,
        "search_queries": [],
        "search_results": [],
        "research_summary": "",
        "follow_up_questions": [],
        "current_step": "query_analyser",
        "errors": [],
    }

    wf = build_graph()

    # Stream progress
    for update in wf.stream(initial_state, stream_mode="updates"):
        for node_name in update:
            print(f"processed: {node_name}")

    # Final state
    final_state = wf.invoke(initial_state)

    return {
        "original_query": final_state["user_query"],
        "search_queries": final_state["search_queries"],
        "research_summary": final_state["research_summary"],
        "follow_up_questions": final_state["follow_up_questions"],
        "errors": final_state["errors"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python research_workflow.py <your question>")
        sys.exit(1)
    
    q = " ".join(sys.argv[1:])
    result = run_research_workflow(q)

    print("\n=== RESULTS ===\n")
    print("Original Query:", result["original_query"], "\n")
    print("Search Queries:")
    for i, sq in enumerate(result["search_queries"], 1):
        print(f"  {i}. {sq}")
    print("\nResearch Summary:\n", result["research_summary"], "\n")
    print("Follow‑up Questions:")
    for i, fq in enumerate(result["follow_up_questions"], 1):
        print(f"  {i}. {fq}")
    if result["errors"]:
        print("\nErrors:")
        for e in result["errors"]:
            print("  –", e)

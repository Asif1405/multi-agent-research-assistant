import os
import requests
import gradio as gr
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


search_tool = SerperSearchTool(k=5)  # Reduced from 10 to 5 for faster inference


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
    print("\n🔍 STEP 1: Query Analysis")
    print(f"   User Query: {state['user_query']}")
    
    sys = (
        "You break down research questions into EXACTLY 3 diverse, precise web-search "
        "queries. Cover the most important angles of the topic. Keep in mind we are in 2025 , "
        "so use the latest information and trends. Each query should be concise, "
        "relevant, and designed to yield useful search results."
        " Each query should have a rationale explaining its importance."
        " Do not use 2025 in the query unless it is absolutely necessary."
    )
    parser = PydanticOutputParser(pydantic_object=SearchQueries)

    prompt = (
        f"User question: {state['user_query']}\n\n"
        f"Generate EXACTLY 3 search queries.\n\n"
        f"{parser.get_format_instructions()}"
    )

    msg = [SystemMessage(content=sys), HumanMessage(content=prompt)]
    try:
        resp = LLM.invoke(msg)
        queries = parser.parse(resp.content).queries[:3]  # Ensure only 3 queries
        print(f"   Generated {len(queries)} search queries:")
        for i, q in enumerate(queries, 1):
            print(f"     {i}. {q.query}")
        return {**state, "search_queries": [q.query for q in queries], "current_step": "search_executor"}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {**state, "errors": state.get("errors", []) + [f"query_analyser: {e}"], "current_step": "error"}


def search_executor(state: ResearchState) -> ResearchState:
    print("\n🌐 STEP 2: Executing Web Searches")
    try:
        results: List[Dict] = []
        for i, q in enumerate(state["search_queries"], 1):
            print(f"   Searching ({i}/{len(state['search_queries'])}): {q}")
            search_results = search_tool.invoke(q)
            results.extend(search_results)
            print(f"     Found {len(search_results)} results")
        
        print(f"   Total results collected: {len(results)}")
        return {**state, "search_results": results, "current_step": "content_synthesiser"}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {**state, "errors": state.get("errors", []) + [f"search_executor: {e}"], "current_step": "error"}


def content_synthesiser(state: ResearchState) -> ResearchState:
    print("\n📝 STEP 3: Synthesizing Content")
    print(f"   Processing {len(state['search_results'])} search results")
    
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
        print("   Generating research summary...")
        resp = LLM.invoke(msg)
        summary = parser.parse(resp.content)
        print("   ✅ Summary generated successfully")
        print(f"   Summary length: {len(summary.summary)} characters")
        return {
            **state,
            "research_summary": summary.summary,
            "current_step": "follow_up_generator",
        }
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {**state, "errors": state.get("errors", []) + [f"content_synthesiser: {e}"], "current_step": "error"}


def follow_up_generator(state: ResearchState) -> ResearchState:
    print("\n💡 STEP 4: Generating Follow-up Questions")
    
    sys = (
        "Generate EXACTLY 2 thoughtful follow‑up questions that would deepen the user's "
        "understanding or cover uncovered aspects. Be concise."
    )
    parser = PydanticOutputParser(pydantic_object=FollowUpQuestions)

    prompt = (
        f"Original question: {state['user_query']}\n\n"
        f"Research summary: {state['research_summary']}\n\n"
        f"Generate EXACTLY 2 follow-up questions.\n\n"
        f"{parser.get_format_instructions()}"
    )

    msg = [SystemMessage(content=sys), HumanMessage(content=prompt)]
    try:
        print("   Generating follow-up questions...")
        resp = LLM.invoke(msg)
        questions = parser.parse(resp.content).questions[:2]  # Ensure only 2 questions
        print(f"   Generated {len(questions)} follow-up questions:")
        for i, q in enumerate(questions, 1):
            print(f"     {i}. {q.question}")
        return {
            **state,
            "follow_up_questions": [q.question for q in questions],
            "current_step": "complete",
        }
    except Exception as e:
        print(f"   ❌ Error: {e}")
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
    print("\n" + "="*60)
    print("🚀 STARTING RESEARCH WORKFLOW")
    print("="*60)
    print(f"Question: {question}")
    print("="*60)
    
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

    # Don't use both stream and invoke - just use invoke
    final_state = wf.invoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ WORKFLOW COMPLETED")
    print("="*60)
    if final_state["errors"]:
        print("⚠️  Errors encountered during workflow:")
        for e in final_state["errors"]:
            print(f"   - {e}")
    else:
        print("✨ No errors - workflow completed successfully!")
    print("="*60 + "\n")

    return {
        "original_query": final_state["user_query"],
        "search_queries": final_state["search_queries"],
        "research_summary": final_state["research_summary"],
        "follow_up_questions": final_state["follow_up_questions"],
        "errors": final_state["errors"],
        "progress": []  # Removed streaming to avoid duplicate execution
    }


# Gradio App Functions
def process_query(query, history):
    """Process the research query and return formatted results"""
    if not query.strip():
        return "", history, gr.update(visible=False), "", gr.update(value=None)
    
    # Show processing status
    history.append(("User", query))
    
    try:
        # Run the research workflow
        result = run_research_workflow(query)
        
        # Format the response
        response = f"## 📊 Research Summary\n\n{result['research_summary']}\n\n"
        
        # Add search queries used
        if result['search_queries']:
            response += "### 🔍 Search Queries Used:\n"
            for i, sq in enumerate(result['search_queries'], 1):
                response += f"{i}. {sq}\n"
            response += "\n"
        
        # Add any errors
        if result['errors']:
            response += "### ⚠️ Errors Encountered:\n"
            for e in result['errors']:
                response += f"- {e}\n"
            response += "\n"
        
        history.append(("Assistant", response))
        
        # Create follow-up questions buttons
        if result['follow_up_questions']:
            return "", history, gr.update(visible=True, value=result['follow_up_questions']), result['follow_up_questions'], gr.update(value=None)
        else:
            return "", history, gr.update(visible=False), [], gr.update(value=None)
            
    except Exception as e:
        error_msg = f"❌ An error occurred: {str(e)}"
        history.append(("Assistant", error_msg))
        return "", history, gr.update(visible=False), [], gr.update(value=None)


def use_follow_up(question, current_questions):
    """Handle follow-up question selection"""
    if question in current_questions:
        return question
    return ""


# Create Gradio Interface
with gr.Blocks(theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
        # 🔬 AI Research Assistant
        
        Ask any question and I'll search the web, synthesize information, and suggest follow-up questions.
        """
    )
    
    # Store current follow-up questions
    current_questions = gr.State([])
    
    with gr.Row():
        with gr.Column(scale=4):
            query_input = gr.Textbox(
                label="Your Question",
                placeholder="Enter your research question here...",
                lines=2
            )
            submit_btn = gr.Button("🚀 Research", variant="primary")
        
    # Chat history
    chatbot = gr.Chatbot(
        label="Research Results",
        height=400,
        type="tuples"
    )
    
    # Follow-up questions section
    with gr.Column(visible=False) as follow_up_section:
        gr.Markdown("### 💡 Suggested Follow-up Questions")
        follow_up_btns = gr.Radio(
            label="Click a question to research it:",
            choices=[],
            interactive=True
        )
        use_follow_up_btn = gr.Button("Research Selected Question", variant="secondary")
    
    # Clear button
    clear_btn = gr.Button("🗑️ Clear History")
    
    # Event handlers
    submit_btn.click(
        process_query,
        inputs=[query_input, chatbot],
        outputs=[query_input, chatbot, follow_up_section, current_questions, follow_up_btns]
    )
    
    query_input.submit(
        process_query,
        inputs=[query_input, chatbot],
        outputs=[query_input, chatbot, follow_up_section, current_questions, follow_up_btns]
    )
    
    # Update follow-up buttons when questions are available
    current_questions.change(
        lambda q: gr.update(choices=q if q else []),
        inputs=[current_questions],
        outputs=[follow_up_btns]
    )
    
    # Handle follow-up question selection
    use_follow_up_btn.click(
        use_follow_up,
        inputs=[follow_up_btns, current_questions],
        outputs=[query_input]
    ).then(
        lambda: [],  # Clear chat history
        outputs=[chatbot]
    ).then(
        process_query,
        inputs=[query_input, chatbot],
        outputs=[query_input, chatbot, follow_up_section, current_questions]
    )
    
    # Clear history
    clear_btn.click(
        lambda: ("", [], gr.update(visible=False), [], gr.update(value=None)),
        outputs=[query_input, chatbot, follow_up_section, current_questions, follow_up_btns]
    )
    
    # Add examples
    gr.Examples(
        examples=[
            "What are the latest developments in quantum computing?",
            "How does climate change affect ocean ecosystems?",
            "What are the best practices for remote team management?",
            "Explain the difference between machine learning and deep learning"
        ],
        inputs=query_input
    )

# Launch the app
if __name__ == "__main__":
    print("\n🚀 Launching Research Assistant Gradio App...")
    print("📍 Access the app at: http://localhost:7860")
    print("💡 Press CTRL+C to stop the server\n")
    
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860
    )

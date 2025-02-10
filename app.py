from flask import Flask, render_template, request, jsonify
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict, Annotated
import os
from langchain import hub
from langchain.chat_models import init_chat_model


app = Flask(__name__)

db = SQLDatabase.from_uri(os.getenv("DATABASE_URI"))

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("Missing GROQ_API_KEY.")

os.environ["GROQ_API_KEY"] = groq_api_key

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

llm = init_chat_model("llama3-8b-8192", model_provider="groq")

query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

class QueryOutput(TypedDict):
    """Generated SQL query."""
    query: Annotated[str, ..., "Syntactically valid SQL query."]


def write_query(state: State):
    """Generate SQL query to fetch information."""
    prompt = query_prompt_template.invoke(
        {
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": db.get_table_info(),
            "input": state["question"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}


def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    try:
        result = execute_query_tool.invoke(state["query"])
        return {"result": result}
    except Exception as e:
        return {"result": f"Error executing query: {str(e)}"}



def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    if not state["result"] or "Error" in state["result"]:
        return {"answer": "I don't know. The information isn't available in the database."}

    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, directly provide only the final answer "
        "without repeating the question, SQL query, or SQL result.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)

    raw_response = response.content
    final_answer = raw_response.split("Based on the SQL result,")[-1].strip() \
        if "Based on the SQL result," in raw_response else raw_response.strip()
    
    return {"answer": final_answer}



graph_builder = StateGraph(State).add_sequence(
    [write_query, execute_query, generate_answer]
)
graph_builder.add_edge(START, "write_query")
graph = graph_builder.compile()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json.get("question")
    if not user_question:
        return jsonify({"error": "No question provided."}), 400

    response_data = {}

    try:
        for step in graph.stream({"question": user_question}, stream_mode="updates"):
            response_data.update(step)
        
        final_answer = response_data.get("generate_answer", {}).get("answer", "I don't know.")
        return jsonify({
            "full_response": response_data,
            "final_answer": final_answer
        })
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  
    app.run(host="0.0.0.0", port=port)

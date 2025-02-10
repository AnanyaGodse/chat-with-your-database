# Chat with Your Database

This project is a SQL-powered Chat Assistant built with Flask, LangChain, llama3-8b from Groq, and a state-driven execution flow. The assistant accepts natural language questions from users, formulates SQL queries to retrieve data from a database, executes those queries, and generates a meaningful final response.

### How the Assistant Works
The assistant works by processing user questions in the following steps:

1. Receive User Question:
The user provides a question via the /ask API endpoint.

2. Query Generation:
A structured query prompt is built by invoking a pre-defined template from the LangChain Hub. The LLM (llama3-8b-8192 from Groq) generates a syntactically valid SQL query based on this prompt.

3. Query Execution:
The assistant uses QuerySQLDatabaseTool to run the generated query against the SQL database.

4. Answer Generation:
Based on the query result, the assistant generates a concise answer using the LLM.

5. Response:
The assistant returns the full response and final answer to the user.




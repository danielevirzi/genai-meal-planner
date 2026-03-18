# **🗺️ Project Roadmap: GenAI Meal Planner & Grocery Assistant**

This document outlines the development phases for a deterministic multi-agent system designed to generate meal plans and grocery lists. The system extracts constraints from natural language input, queries a nutritional/economic database, and uses an orchestrated LLM architecture to guarantee structured and validated outputs.

## **🛠️ Technology Stack Summary**

| Component | Chosen Technology | Primary Purpose |
| :---- | :---- | :---- |
| **Backend & API** | FastAPI \+ Pydantic | Endpoint exposure, data validation, and I/O schemas. |
| **Orchestration** | LangGraph | State management, execution graph, and validation loops. |
| **Guardrails & Metadata** | GLiNER | Prompt relevance classification (Guardrail) and metadata extraction for MLflow evaluation. |
| **LLM Inference** | Gemini API | High-performance cloud LLM for generation and tool calling. |
| **Agents & Output** | Pydantic AI | Constraining the LLM to generate strictly validated JSON outputs. |
| **Optimization** | DSPy | Algorithmic prompt optimization for the Planner Agent. |
| **Experimentation** | MLflow | Tracking metrics, experiments, hyperparameters, and evaluation metadata. |
| **Observability** | Langfuse \+ Prometheus \+ Grafana | LLM call tracking (Langfuse) and system/API metrics. |
| **Infrastructure** | Docker \+ Docker Compose | Containerization of microservices for isolation and deployment. |

## **📍 Phase 1: Data Foundations & Backend API**

**Objective:** Create the core infrastructure to manage ingredient information deterministically.

* \[✅\] Design the database schema (e.g., SQLite) with tables: Ingredients, Prices, Macronutrients, Allergens, Alternatives.
* \[✅\] Populate the database with an initial dataset (mock data).
* \[✅\] Develop CRUD APIs using **FastAPI**.
* \[✅\] Create **Pydantic** models for strict validation of API requests and responses.
* \[✅\] Write basic unit tests for the endpoints.

## **📍 Phase 2: LLM Integration, Guardrails & Metadata Extraction**

**Objective:** Integrate the Gemini API for generative tasks and database retrieval, while configuring GLiNER for prompt security and evaluation metadata.

* \[ \] Set up the **Gemini API** integration (handling API keys and client setup).
* \[ \] Configure Gemini to use **Structured Outputs** and **Tool Calling** so the LLM can autonomously query the FastAPI endpoints (from Phase 1\) to fetch necessary context (e.g., ingredient prices, nutritional info) based on the user's prompt.
* \[ \] Implement a **GLiNER**\-based classifier to act as a **Guardrail**, evaluating the relevance of the user's input (e.g., blocking off-topic requests before routing them to the LLM).
* \[ \] Configure **GLiNER** to extract specific entities from both the initial prompt and the final generated output to create structured **Metadata**.
* \[ \] Integrate the metadata pipeline so these GLiNER-extracted data points are ready to be logged into **MLflow** for downstream evaluation and experiment tracking.

## **📍 Phase 3: Agents & Structured Generation (Pydantic AI & DSPy)**

**Objective:** Build the "brain" of the system, ensuring it consistently produces the correct format.

* \[ \] Define complex **Pydantic** schemas for the final output: Recipe, Meal, Day, WeeklyPlan, GroceryList.
* \[ \] Implement the Planner Agent using **Pydantic AI**, connecting it to the Gemini API.
* \[ \] Create a small dataset of examples (Prompt \-\> Valid Meal Plan).
* \[ \] Configure **DSPy** to run prompt optimization for the Planner Agent, minimizing hallucinations and improving constraint adherence.
* \[ \] Develop the deterministic logic or the Validator Agent to check constraints (e.g., calculating total cost vs. budget, cross-checking allergens).

## **📍 Phase 4: Multi-Agent Orchestration with LangGraph**

**Objective:** Unify all components into a cyclic and resilient workflow.

* \[ \] Define the **LangGraph** State (e.g., user\_input, db\_context, current\_plan, validation\_errors, iteration\_count, metadata).
* \[ \] Transform the components from previous phases into graph "Nodes":
  1. guardrail\_node (GLiNER relevance check).
  2. generate\_plan\_node (Pydantic AI \+ Gemini Tool Calling).
  3. validate\_plan\_node (Validator).
  4. metadata\_extraction\_node (GLiNER metadata creation).
* \[ \] Implement "Conditional Edges":
  * If guardrail\_node fails \-\> Return immediate rejection message.
  * If validate\_plan\_node returns errors and iteration\_count \< Max \-\> Return to generate\_plan\_node passing the errors.
  * If validate\_plan\_node passes \-\> Go to metadata\_extraction\_node, then output.

## **📍 Phase 5: MLOps, Observability, and Deployment**

**Objective:** Make the system monitorable, measurable, and ready for a production-like environment.

* \[ \] Integrate **Langfuse** into the graph and agents to track tokens, LLM latency, and exact prompt traces within the LangGraph cycle.
* \[ \] Configure **MLflow** to log DSPy runs and the GLiNER-generated metadata, tracking which prompts result in fewer error loops and evaluating output quality.
* \[ \] Expose FastAPI application metrics (requests/sec, response times) via **Prometheus**.
* \[ \] Create a **Grafana** dashboard linked to Prometheus to visualize system health.
* \[ \] Write the final docker-compose.yml to orchestrate the simultaneous startup of: FastAPI, LangGraph worker, DB, Prometheus, Grafana, MLflow, and Langfuse (or use cloud versions where preferred).

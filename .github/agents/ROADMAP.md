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

## **📍 Phase 2: LLM Integration & Agent Foundations (Completed Core)**

**Objective:** Establish a working Gemini + Pydantic AI foundation with typed agents, prompts, secure configuration, and deterministic tests.

* \[✅\] Set up **Gemini API** integration with centralized provider/model configuration and API-key resolution.
* \[✅\] Configure default runtime for **Google Generative Language API** (non-Vertex) so `GOOGLE_API_KEY` works out of the box.
* \[✅\] Implement reusable prompt templates/builders for Planner, Retriever, and Validator.
* \[✅\] Implement **Pydantic AI** agents:
  * Planner agent with structured output schema.
  * Retriever agent with tool-calling hooks.
  * Validator agent with structured issue reporting.
* \[✅\] Add unit tests for prompts, Gemini configuration, and all agents using `TestModel`/override patterns.
* \[✅\] Add secure env scaffolding (`.env.example` tracked, `.env` ignored) and documentation.
* \[ \] Wire Retriever tool dependencies to real FastAPI endpoint clients (currently test doubles/mocks in unit tests).

## **📍 Phase 3: Planning Intelligence & Optimization**

**Objective:** Upgrade the Phase 2 foundation into production-grade meal-planning intelligence with richer schemas, deterministic constraint logic, and optimization.

* \[ \] Expand planner output to final domain schemas: **Recipe, Meal, Day, WeeklyPlan, GroceryList**.
* \[ \] Build deterministic validation logic for hard constraints (budget, allergens, macro targets, serving counts) and integrate into Validator flow.
* \[ \] Create a curated dataset of examples (Prompt \-\> Valid Meal Plan) for quality benchmarking.
* \[ \] Configure **DSPy** prompt optimization for Planner quality (constraint adherence, hallucination reduction, consistency).
* \[ \] Define evaluation metrics and acceptance criteria to compare baseline vs optimized planner behavior.
* \[ \] Prepare validator/planner feedback loop contract for LangGraph orchestration in Phase 5.

## **📍 Phase 4: GLiNER Guardrails & Metadata Logic**

**Objective:** Implement GLiNER-based relevance guardrails and deterministic metadata extraction as a first-class pipeline stage.

* \[ \] Implement a **GLiNER** relevance classifier to block or reroute off-topic user requests before planning.
* \[ \] Define and validate GLiNER label taxonomy for meal-planning entities (budget, allergens, goals, ingredient preferences, constraints).
* \[ \] Build structured metadata extraction from:
  * user input (intent, constraints, entities)
  * final validated output (coverage, substitutions, unresolved gaps)
* \[ \] Add confidence thresholds and fallback behavior for low-confidence GLiNER predictions.
* \[ \] Define metadata contract/schema for downstream logging and evaluation in **MLflow**.
* \[ \] Add unit tests for guardrail decisions and metadata extraction consistency.

## **📍 Phase 5: Multi-Agent Orchestration with LangGraph**

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

## **📍 Phase 6: MLOps, Observability, and Deployment**

**Objective:** Make the system monitorable, measurable, and ready for a production-like environment.

* \[ \] Integrate **Langfuse** into the graph and agents to track tokens, LLM latency, and exact prompt traces within the LangGraph cycle.
* \[ \] Configure **MLflow** to log DSPy runs and the GLiNER-generated metadata, tracking which prompts result in fewer error loops and evaluating output quality.
* \[ \] Expose FastAPI application metrics (requests/sec, response times) via **Prometheus**.
* \[ \] Create a **Grafana** dashboard linked to Prometheus to visualize system health.
* \[ \] Write the final docker-compose.yml to orchestrate the simultaneous startup of: FastAPI, LangGraph worker, DB, Prometheus, Grafana, MLflow, and Langfuse (or use cloud versions where preferred).

# **🗺️ Project Roadmap: GenAI Meal Planner & Grocery Assistant**

This document outlines the development phases for a deterministic multi-agent system designed to generate meal plans and grocery lists. The system extracts constraints from natural language input, queries a nutritional/economic database, and uses an orchestrated LLM architecture to guarantee structured and validated outputs.

## **🛠️ Technology Stack Summary**

| Component | Chosen Technology | Primary Purpose |
| :---- | :---- | :---- |
| **Backend & API** | FastAPI \+ Pydantic | Endpoint exposure, data validation, and I/O schemas. |
| **Orchestration** | LangGraph | State management, execution graph, and validation loops. |
| **Data Extraction** | GLiNER | Fast NER to extract constraints (budget, allergies) pre-LLM. |
| **LLM Inference** | vLLM | High-performance model serving for local open-source models. |
| **Agents & Output** | Pydantic AI | Constraining the LLM to generate strictly validated JSON outputs. |
| **Optimization** | DSPy | Algorithmic prompt optimization for the Planner Agent. |
| **Experimentation** | MLflow | Tracking metrics, experiments, and hyperparameters. |
| **Observability** | Langfuse \+ Prometheus \+ Grafana | LLM call tracking (Langfuse) and system/API metrics. |
| **Infrastructure** | Docker \+ Docker Compose | Containerization of microservices for isolation and deployment. |

## **📍 Phase 1: Data Foundations & Backend API**

**Objective:** Create the core infrastructure to manage ingredient information deterministically.

* \[ \] Design the database schema (e.g., SQLite) with tables: Ingredients, Prices, Macronutrients, Allergens, Alternatives.
* \[ \] Populate the database with an initial dataset (mock data).
* \[ \] Develop CRUD APIs using **FastAPI**.
* \[ \] Create **Pydantic** models for strict validation of API requests and responses.
* \[ \] Write basic unit tests for the endpoints.

## **📍 Phase 2: Fast Extraction & Local LLM Setup**

**Objective:** Prepare the AI models for text processing and inference.

* \[ \] Spin up a Docker container with **vLLM** and download a suitable open-source model (e.g., Llama-3-8B-Instruct or Mistral, preferably quantized).
* \[ \] Implement a Python script using **GLiNER** for Named Entity Recognition.
* \[ \] Train or configure GLiNER to recognize specific entities: Allergen, Preferred\_Ingredient, Target\_Budget.
* \[ \] Create a function that takes the GLiNER output and calls the FastAPI endpoints (from Phase 1\) to enrich the context (e.g., fetch prices for the requested ingredients).

## **📍 Phase 3: Agents & Structured Generation (Pydantic AI & DSPy)**

**Objective:** Build the "brain" of the system, ensuring it consistently produces the correct format.

* \[ \] Define complex **Pydantic** schemas for the final output: Recipe, Meal, Day, WeeklyPlan, GroceryList.
* \[ \] Implement the Planner Agent using **Pydantic AI**, connecting it to the vLLM server.
* \[ \] Create a small dataset of examples (Prompt \-\> Valid Meal Plan).
* \[ \] Configure **DSPy** to run prompt optimization for the Planner Agent, minimizing hallucinations and improving constraint adherence.
* \[ \] Develop the deterministic logic or the Validator Agent to check constraints (e.g., calculating total cost vs. budget, cross-checking allergens).

## **📍 Phase 4: Multi-Agent Orchestration with LangGraph**

**Objective:** Unify all components into a cyclic and resilient workflow.

* \[ \] Define the **LangGraph** State (e.g., user\_input, extracted\_entities, db\_context, current\_plan, validation\_errors, iteration\_count).
* \[ \] Transform the components from previous phases into graph "Nodes":
  1. extract\_and\_fetch\_node (GLiNER \+ API).
  2. generate\_plan\_node (Pydantic AI).
  3. validate\_plan\_node (Validator).
* \[ \] Implement "Conditional Edges":
  * If validate\_plan\_node returns errors and iteration\_count \< Max \-\> Return to generate\_plan\_node passing the errors.
  * If validate\_plan\_node passes \-\> Go to the output node.

## **📍 Phase 5: MLOps, Observability, and Deployment**

**Objective:** Make the system monitorable, measurable, and ready for a production-like environment.

* \[ \] Integrate **Langfuse** into the graph and agents to track tokens, LLM latency, and exact prompt traces within the LangGraph cycle.
* \[ \] Configure **MLflow** to log DSPy runs, tracking which prompts result in fewer error loops in the graph.
* \[ \] Expose FastAPI application metrics (requests/sec, response times) via **Prometheus**.
* \[ \] Create a **Grafana** dashboard linked to Prometheus to visualize system health.
* \[ \] Write the final docker-compose.yml to orchestrate the simultaneous startup of: FastAPI, vLLM, LangGraph worker, DB, Prometheus, Grafana, MLflow, and Langfuse (or use cloud versions where preferred).

# Herzliya Transport Simulator Optimizer

### A Behavioral Digital Twin & Multi-Agent Optimization Engine

## 🎯 Project Vision

The Herzliya Transport Optimizer is a sophisticated simulation environment designed to solve urban transit inefficiency. Unlike static models, this project creates a **Behavioral Digital Twin** of Herzliya, Israel. It simulates a full operational day (06:00–22:00), modeling the unique sociological pulse of the city — from morning surges at the Herzliya Train Station to late-night shifts in the Pituach high-tech district.

## 🧠 Core Architecture

### 1. Context-Aware Demand (RAG + LLM)

The simulation uses a Retrieval-Augmented Generation (RAG) pipeline to ground passenger behavior in real-world local patterns.

- **Knowledge Base:** A curated dataset of Herzliya's movement patterns (e.g., Reichman University schedules, tech-hub shifts, and school dismissals).
- **Deterministic Scaling:** LLM-generated baseline personas are processed by a custom scaler that handles time-jittering and spatial distribution, allowing for massive, realistic load testing without artificial "clumping."

### 2. High-Fidelity Agentic Simulation

Every bus and passenger is a discrete agent with specific internal logic:

- **Bus Logic:** Manages real-time navigation, stop-duration, and capacity constraints. The system logs "left-behind" events as a primary KPI for the optimizer.
- **Geospatial Intelligence:** Powered by PostgreSQL/GeoAlchemy2 and OSRM, calculating precise travel times based on actual road topology rather than straight-line distance.

### 3. The Multi-Agent Optimization Council

Post-simulation, a CrewAI team performs an adversarial analysis of the logs:

- 📢 **The Neighborhood Advocate:** Identifies underserved residential zones through a social equity lens.
- 📊 **The Demand & Flow Analyst:** Scans O-D matrices for "latent demand" and missing network links.
- 🗺️ **The Chief Route Architect:** Redraws topological stop sequences to maximize coverage.

## 📂 Repository Structure

```text
TransportSim-Optimizer/
├── .github/workflows/
│   └── ci.yml                         # Continuous Integration pipeline
├── scripts/
│   ├── build_vector_db.py             # Embeds transit patterns into ChromaDB
│   ├── generate_llm_demand.py         # AI-driven baseline trip generator
│   └── scale_demand.py                # Mathematical extrapolator for mass load
├── src/
│   ├── agents/
│   │   ├── bus.py                     # Bus agent: movement, capacity, stop logic
│   │   └── passenger.py               # Passenger agent: routing and boarding logic
│   ├── crew/
│   │   ├── agents.py                  # CrewAI agent definitions
│   │   ├── board.py                   # Crew board orchestration
│   │   ├── metrics.py                 # KPI and performance metric collectors
│   │   ├── rag_retriever.py           # ChromaDB RAG query interface
│   │   └── tasks.py                   # CrewAI task definitions
│   ├── data/
│   │   └── herzliya_patterns.txt      # Behavioral knowledge base for ChromaDB
│   ├── database/                      # PostgreSQL utils, geospatial extractors, and routing edges
│   ├── simulation/
│   │   ├── clock.py                   # Simulated time engine
│   │   ├── config.py                  # Neighborhood bounds and simulation constants
│   │   ├── dispatcher.py              # Bus dispatch and assignment logic
│   │   └── orchestrator.py            # Top-level simulation loop controller
│   ├── ui/                            # Streamlit dashboard and log parsers
│   └── main.py                        # Core simulation entry point
├── tests/                             # Comprehensive test suite (Agents, DB, Crew, Routing)
├── .env                               # Local environment variables (gitignored)
├── pyproject.toml
├── requirements.txt
└── README.md
```


## 🛠️ Technology Stack

| Category | Tools |
|---|---|
| AI / LLM | OpenAI API, CrewAI, ChromaDB (Vector Store) |
| Backend | Python 3.12, Pandas, NumPy |
| Database | Neon (PostgreSQL), SQLAlchemy, GeoAlchemy2 |
| Geospatial | GeoPandas, Shapely, OSRM API |
| Frontend | Streamlit, Folium |
| DevOps | Docker, Azure App Service (B1 Tier), GitHub Container Registry (GHCR) |

## 🧪 Engineering Standards

This project is following professional software engineering workflows:

- **Test-Driven Development (TDD):** A robust `pytest` suite with a strict "One Assert Per Test" policy.
- **Static Type Checking:** Full `mypy` integration ensures type-safety across complex agent interactions.
- **Fast Linting:** Adheres to PEP 8 and modern Python best practices via `Ruff`.

```python
# Example of TDD isolation in tests/test_passenger_navigator.py
def test_navigator_sorts_stops_by_distance(navigator):
    # Testing that standing near North Station makes it the primary choice
    closest = navigator.get_closest_stops(lat=0.8, lon=0.0, count=2)
    assert closest == ["North Station", "Center Station"]
```

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/matan-roditi/TransportSim-Optimizer
cd TransportSim-Optimizer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory and configure your API keys and database credentials:

```ini
# Database Credentials
PG_HOST=localhost
PG_PORT=5432
PG_DB=
PG_USER=
PG_PASSWORD=

# AI Credentials
OPENAI_API_KEY=
OPENAI_MODEL_NAME=
```

## 🚦 Running the Simulation

The simulation relies on a fully hydrated database and vector store. Run the pipeline in the following order:

### 1. Build the Vector Database (RAG)

Embeds the local Herzliya transit patterns into ChromaDB for the AI to reference.

```bash
python scripts/build_vector_db.py
```

### 2. Generate the Commuter Demand

Triggers the LLM to build baseline passenger flow, then automatically scales it up to load-test the system (outputs to `herzliya_demand_scaled.json`).

```bash
python scripts/generate_llm_demand.py
```

### 3. Launch the Dashboard

Boot up the Streamlit UI to watch the multi-agent system attempt to optimize the traffic.

```bash
streamlit run src/ui/app.py
```

## ✅ Running Tests

To ensure the integrity of the routing logic, database connections, and agent behaviors, run the test suite:

```bash
pytest tests/
```
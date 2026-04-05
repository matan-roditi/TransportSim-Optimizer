# Transport Simulator Optimizer

An AI-powered, multi-agent simulation engine designed to optimize public transportation routing in Herzliya, Israel. This project utilizes CrewAI, advanced Large Language Models, and a custom RAG (Retrieval-Augmented Generation) pipeline to generate highly realistic, context-aware urban mobility patterns and dynamically dispatch transit resources.

## 🚀 Core Features

* **Multi-Agent Orchestration:** Utilizes autonomous agents (Passengers, Buses, Dispatchers) operating on a simulated clock to test urban transit efficiency under pressure.
* **RAG-Augmented Passenger Demand:** Integrates ChromaDB with OpenAI to generate context-aware passenger flows based on real Herzliya behavioral patterns (e.g., tech hub commutes, university class schedules, and train station bottlenecks).
* **Deterministic Traffic Scaling:** Features a mathematical extrapolator to safely scale AI-generated baseline trips into massive datasets with time-jittering for robust load testing.
* **Geospatial Routing:** Connects to a PostgreSQL database to calculate accurate, real-world travel times between hundreds of local bus stops using geospatial node mapping.
* **Interactive Dashboard:** Includes a live Streamlit and Folium UI to visualize network congestion, bus routing, and passenger metrics in real-time.

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

- **AI & LLM:** OpenAI API, CrewAI, ChromaDB
- **Data & Geospatial:** PostgreSQL, SQLAlchemy, GeoAlchemy2, GeoPandas, Shapely
- **Frontend & Visualization:** Streamlit, Folium, Streamlit-Folium
- **Core Logic:** Python, Pandas, NumPy, Pytest

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

## 🧪 Running Tests

To ensure the integrity of the routing logic, database connections, and agent behaviors, run the test suite:

```bash
pytest tests/
```
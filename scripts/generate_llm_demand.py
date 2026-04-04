import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402
from crew.rag_retriever import fetch_time_context  # noqa: E402
from simulation.config import HERZLIYA_NEIGHBORHOODS  # noqa: E402

load_dotenv()

ROOT_DIR = os.path.abspath(os.path.join(current_dir, ".."))
OUTPUT_FILE = os.path.join(ROOT_DIR, "herzliya_demand.json")

# All valid neighborhood names — must match simulation/config.py exactly
VALID_NEIGHBORHOODS = HERZLIYA_NEIGHBORHOODS

# --- Demand configuration ---
START_HOUR = 6       # 06:00
END_HOUR = 22        # up to but not including 22:00
TOTAL_PASSENGERS = 600

# Relative demand weights per hour — reflects morning peak (07-09), evening peak (16-18)
_DEMAND_WEIGHTS = {
    6: 1, 7: 3, 8: 5, 9: 3, 10: 1.5, 11: 1, 12: 1.5,
    13: 2, 14: 1.5, 15: 2, 16: 4, 17: 5, 18: 3, 19: 2, 20: 1, 21: 0.5,
}


def _build_time_slots() -> list:
    hours = list(range(START_HOUR, END_HOUR))
    weights = [_DEMAND_WEIGHTS.get(h, 1) for h in hours]
    total_weight = sum(weights)
    slots = []
    assigned = 0
    for i, h in enumerate(hours):
        if i == len(hours) - 1:
            count = TOTAL_PASSENGERS - assigned
        else:
            count = round(TOTAL_PASSENGERS * weights[i] / total_weight)
        assigned += count
        slots.append((f"{h:02d}:00", count))
    return slots


TIME_SLOTS = _build_time_slots()


def build_augmented_prompt(time_str: str, count: int) -> str:
    # Fetch real-world behavioral context from the ChromaDB vector store
    context = fetch_time_context(time_str)
    context_block = context if context else "Standard traffic flow, no special events."

    neighborhoods_str = ", ".join(VALID_NEIGHBORHOODS)

    prompt = f"""You are an urban transit generator creating passenger data for Herzliya around {time_str}.

CONTEXTUAL FACTS:
{context_block}

VALID NEIGHBORHOODS (use ONLY these exact names):
{neighborhoods_str}

TASK: Generate exactly {count} realistic passenger trips that align with the contextual facts above.
Each trip must reflect real commuter patterns for this time of day.

IMPORTANT - departure time spreading:
- Spread "departing_time" naturally across the full hour from {time_str} to the next hour.
- Do NOT cluster times at round values like XX:00 or XX:30.
- Use varied minutes (e.g. :04, :11, :17, :24, :38, :47, :53) to simulate organic arrival patterns.
- Distribute times so no single minute has more than 2-3 passengers.

Return ONLY a valid JSON array with NO extra text, markdown, or code fences.
Each element must be a JSON object with exactly these three keys:
  "departing_time": "HH:MM"  (string, between {time_str} and the next hour)
  "origin_neighborhood": one of the valid neighborhoods above
  "destination_neighborhood": one of the valid neighborhoods above (must differ from origin)

Example:
[
  {{"departing_time": "{time_str}", "origin_neighborhood": "Herzliya_B", "destination_neighborhood": "Train_Station"}}
]
"""
    return prompt


def generate_demand_for_slot(client: OpenAI, time_str: str, count: int) -> list:
    prompt = build_augmented_prompt(time_str, count)

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-5-mini"),
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps its response in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    passengers = json.loads(raw)

    # Validate each entry: required keys, valid neighborhood names, no self-trips
    valid = []
    for p in passengers:
        if (
            isinstance(p, dict)
            and "departing_time" in p
            and "origin_neighborhood" in p
            and "destination_neighborhood" in p
            and p["origin_neighborhood"] in VALID_NEIGHBORHOODS
            and p["destination_neighborhood"] in VALID_NEIGHBORHOODS
            and p["origin_neighborhood"] != p["destination_neighborhood"]
        ):
            valid.append(p)

    return valid


def generate_demand() -> None:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    all_passengers: list = []

    print(f"Starting LLM demand generation across {len(TIME_SLOTS)} time slots...")

    for time_str, count in TIME_SLOTS:
        try:
            print(f"  Generating {count} passengers for {time_str}...", flush=True)
            batch = generate_demand_for_slot(client, time_str, count)
            all_passengers.extend(batch)
            print(f"  {time_str}: {len(batch)} valid passengers collected.")
        except Exception as e:
            # Log and continue — a single failed slot should not abort the whole run
            print(f"  WARNING: Failed to generate slot {time_str}: {e}. Skipping.")

    # Sort chronologically so the demand file reads cleanly
    all_passengers.sort(key=lambda p: p["departing_time"])

    output = {"passengers": all_passengers}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"\nDemand generation complete. {len(all_passengers)} passengers written to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_demand()

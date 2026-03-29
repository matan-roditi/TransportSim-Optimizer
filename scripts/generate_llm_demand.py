import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configure the logger to format messages with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file to secure the API key
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_herzliya_demand_matrix() -> None:
    """
    Prompts the LLM to generate a realistic daily commute schedule for Herzliya.
    Saves the output to a JSON file to be consumed by the simulation.
    """
    logger.info("Connecting to the LLM to generate Herzliya commute data...")

    # We ask for a specific JSON object structure to ensure perfect parsing
    # The neighborhood list has been expanded to cover the entire city
    prompt = """
    You are an expert urban mobility data generator modeling the daily commute patterns of Herzliya, Israel. 

    Generate a realistic travel demand matrix for an average weekday from 06:00 to 22:00. 
    Scale: 1 passenger object in your output represents exactly 200 real citizens of Herzliya(about 500 passengers representing the 100,000 population). 
    Consider Herzliya's specific geography, such as morning commutes toward the tech hubs in Pituach and evening returns to residential zones.
    Note that big part of the population goes in the morning to the train station near Herzliya_B, and returns from there in the evening.
    Note the distinction between "Herzliya_Pituach" (the beachside residential strip) and "Herzliya_Pituach_Business" (the tech/business park).
    "Herzliya_Pituach_Business" should be a very frequent DESTINATION in the morning peak (06:00-09:30) and a very frequent ORIGIN in the evening peak (16:00-20:00), reflecting heavy tech-worker commutes.

    Each passenger object must include:
    - departing_time: The time they start their commute (HH:MM format)
    - origin_neighborhood: The neighborhood they depart from
    - destination_neighborhood: The neighborhood they are heading to    

    You must strictly limit locations to the following exact neighborhood names:
    [
        "Herzliya_Pituach", "Herzliya_Pituach_Business", "Marina", "Nof_Yam", "Herzliya_B", 
        "Green_Herzliya", "Young_Herzliya", "Galil_Yam", "City_Center", 
        "Neve_Yisrael", "Neve_Amirim", "Shikun_Darom", "Neve_Amal", 
        "Yad_HaTisha", "Gan_Rashal", "Neve_Oved"
    ]

    You must return ONLY a valid JSON object with a single key called "passengers". 
    The value must be an array of objects. Do not include any conversational text or markdown formatting. 

    The JSON schema must be exactly:
    {
      "passengers": [
        {
          "departing_time": "HH:MM",
          "origin_neighborhood": "string",
          "destination_neighborhood": "string"
        }
      ]
    }
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are a data output system that only returns pure, raw JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        raw_json_string = response.choices[0].message.content

        # Parse the string into a Python dictionary to verify it is valid JSON
        if raw_json_string is None:
            raise ValueError("Received empty response from the API.")

        demand_data = json.loads(raw_json_string)

        output_path = "herzliya_demand.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(demand_data, f, indent=4)

        logger.info(f"Success! Generated {len(demand_data['passengers'])} passenger batches.")
        logger.info(f"Data saved safely to {output_path}")

    except Exception as e:
        logger.error(f"An error occurred during generation: {e}")

if __name__ == "__main__":
    generate_herzliya_demand_matrix()
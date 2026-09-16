from dotenv import load_dotenv
import os
import json
import google.genai

load_dotenv(".env")
api_key = os.environ.get("API_KEY")

client = google.genai.GenerativeModel(api_key=api_key)

def build_claim_extraction_prompt(user_text: str) -> str:
    ALLOWED_VALUES = {
    "compute_model": ["EC2", "LAMBDA", "ECS", "EKS", "UNSPECIFIED"],
    "trigger": ["API_GATEWAY", "EVENTBRIDGE", "SQS", "S3", "UNSPECIFIED"],
    "monitoring": ["CLOUDWATCH", "UNSPECIFIED"],
    "dependencies": ["SQS", "SNS", "S3", "UNSPECIFIED"],
    "database": ["DYNAMODB", "RDS", "UNSPECIFIED"],
    }
    schema_description = "\n".join(
        f'- "{field}": one of {values}'
        for field, values in ALLOWED_VALUES.items()
    )

    prompt = f"""You are extracting structured architecture claims from a user's description.
            Return ONLY a JSON object with these exact fields. Each field's value must come only 
            from its allowed list below — never invent a new value.{schema_description}
            For "trigger", "dependencies", and "monitoring", return a JSON array of matching values 
            (can be multiple, or ["UNSPECIFIED"] if none apply).    For "compute_model" and "database", 
            return a single string value.User's architecture description:"{user_text}"

            Return only the JSON object. No explanation, no markdown formatting."""

    return prompt


def call_llm(prompt: str) -> str:
    """
    Sends the prompt to the LLM API and returns the raw text response.
    This part is just plumbing — the API call itself.
    """
    pass


def parse_llm_response(raw_response: str) -> dict:
    """
    Takes the raw text the LLM returned and parses it into a Python dict.

    TODO: decide how I handle the case where the LLM doesn't return
    clean JSON (e.g. wraps it in ```json fences, or adds a stray sentence).
    """
    pass


def extract_claims(user_text: str) -> dict:
    """
    Orchestrator: ties the above three functions together.
    Input: user's raw architecture description (a string).
    Output: a structured dict of claims, ready to be compared
    against Stage 3/4's extracted "ground truth" later.
    """
    prompt = build_claim_extraction_prompt(user_text)
    raw_response = call_llm(prompt)
    claims = parse_llm_response(raw_response)
    return claims


if __name__ == "__main__":
    # Quick manual test while building — replace with a real pytest file later
    sample_text = "this is a monolith running on EC2"
    result = extract_claims(sample_text)
    print(result)

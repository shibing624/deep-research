import tiktoken
from openai import OpenAI
import json
from .config import get_config
from .text_splitter import RecursiveCharacterTextSplitter
from loguru import logger


# Initialize clients based on configuration
def _get_openai_client():
    """Get OpenAI client if configured"""
    config = get_config()
    if config["openai"]["api_key"]:
        return OpenAI(
            api_key=config["openai"]["api_key"],
            base_url=config["openai"]["base_url"]
        )
    return None


def _get_fireworks_client():
    """Get Fireworks client if configured"""
    config = get_config()
    if config["fireworks"]["api_key"]:
        return OpenAI(
            api_key=config["fireworks"]["api_key"],
            base_url=config["fireworks"]["base_url"]
        )
    return None


# Get clients
openai_client = _get_openai_client()

# Constants
MIN_CHUNK_SIZE = 140
encoder = tiktoken.get_encoding("cl100k_base")  # Using cl100k as a replacement for o200k_base

logger.info(f"OpenAI client: {openai_client}, model: {get_config()['openai']['model']}")


def get_model():
    """Get the appropriate model based on configuration"""
    config = get_config()

    # Check for custom model in OpenAI
    if config["openai"]["model"] != "o3-mini" and openai_client:
        return {
            "client": openai_client,
            "model": config["openai"]["model"]
        }

    # Default to OpenAI
    if openai_client:
        return {
            "client": openai_client,
            "model": "o3-mini"  # Default model
        }

    raise ValueError("No model configuration found. Please set OpenAI or Fireworks API keys in config.")


def trim_prompt(prompt, context_size=None):
    """Trim prompt to maximum context size"""
    if context_size is None:
        context_size = get_config()["research"]["context_size"]

    if not prompt:
        return ""

    length = len(encoder.encode(prompt))
    if length <= context_size:
        return prompt

    overflow_tokens = length - context_size
    # Estimate characters to remove (3 chars per token on average)
    chunk_size = len(prompt) - overflow_tokens * 3

    if chunk_size < MIN_CHUNK_SIZE:
        return prompt[:MIN_CHUNK_SIZE]

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    trimmed_prompt = splitter.split_text(prompt)[0] or ""

    # Handle case where trimmed prompt is same length as original
    if len(trimmed_prompt) == len(prompt):
        return trim_prompt(prompt[:chunk_size], context_size)

    # Recursively trim until within context size
    return trim_prompt(trimmed_prompt, context_size)


def generate_object(model_config, system, prompt, schema):
    """Generate structured output from the model"""
    client = model_config["client"]
    model_name = model_config["model"]
    if schema:
        prompt = f"{prompt}\n\njson schema: \n{schema}"
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    # Extract and return the JSON content
    content = response.choices[0].message.content
    logger.debug(f"Generated content: {content}")
    # In a real implementation, we would validate against the schema here
    # For simplicity, we're just returning the parsed JSON
    ans = json.loads(content)
    return ans

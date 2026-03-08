import tiktoken

# Note: Cost estimation disabled for local Ollama models (free)
ENCODING_MODEL = "o200k_base"
INPUT_COST_PER_TOKEN = 0.000005
OUTPUT_COST_PER_TOKEN = 0.000015
IMAGE_INFERENCE_COST = 0.003825
EMBEDDING_COST = 0.02 / 1000000 # Assumes new ada-3-small


# Cost estimation is disabled for local Ollama models (free to use)
def estimate_llm_cost(input_content: str, output_content: str) -> float:
    encoding = tiktoken.get_encoding(ENCODING_MODEL)
    input_tokens = encoding.encode(input_content)
    output_tokens = encoding.encode(output_content)
    input_costs = len(input_tokens) * INPUT_COST_PER_TOKEN
    output_costs = len(output_tokens) * OUTPUT_COST_PER_TOKEN
    return input_costs + output_costs


def estimate_embedding_cost(model, docs):
    # For Ollama models (local, free), return $0
    if model and ('ollama:' in model or 'nomic' in model):
        return 0.0
    
    # For OpenAI or other API models, calculate costs
    try:
        encoding = tiktoken.encoding_for_model(model)
        total_tokens = sum(len(encoding.encode(str(doc))) for doc in docs)
        return total_tokens * EMBEDDING_COST
    except (KeyError, ValueError):
        # If model not found, assume it's free (local model)
        return 0.0


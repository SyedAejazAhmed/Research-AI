import os
from typing import Any

OLLAMA_EMBEDDING_MODEL = os.environ.get(
    "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
)

_SUPPORTED_PROVIDERS = [
    # "openai",  # Removed for Ollama-only setup
    # "azure_openai",  # Removed for Ollama-only setup
    "cohere",
    "gigachat",
    "google_vertexai",
    "google_genai",
    "fireworks",
    "ollama",
    "together",
    "mistralai",
    "huggingface",
    "nomic",
    "voyageai",
    "dashscope",
    "custom",
    "bedrock",
    "aimlapi",
    "netmind",
]


class Memory:
    def __init__(self, embedding_provider: str, model: str, **embedding_kwargs: Any):
        _embeddings = None
        match embedding_provider:
            case "custom":
                # Use Ollama for custom embedding setup
                from langchain_ollama import OllamaEmbeddings
                
                _embeddings = OllamaEmbeddings(
                    model=OLLAMA_EMBEDDING_MODEL,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    **embedding_kwargs,
                )
            # case "openai":  # Removed for Ollama-only setup
            #     from langchain_openai import OpenAIEmbeddings
            #     # Support custom OpenAI-compatible APIs via OPENAI_BASE_URL
            #     if "openai_api_base" not in embedding_kwargs and os.environ.get("OPENAI_BASE_URL"):
            #         embedding_kwargs["openai_api_base"] = os.environ["OPENAI_BASE_URL"]
            #     _embeddings = OpenAIEmbeddings(model=model, **embedding_kwargs)
            # case "azure_openai":  # Removed for Ollama-only setup
            #     from langchain_openai import AzureOpenAIEmbeddings
            #     _embeddings = AzureOpenAIEmbeddings(
            #         model=model,
            #         azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            #         openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
            #         openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            #         **embedding_kwargs,
            #     )
            case "cohere":
                from langchain_cohere import CohereEmbeddings

                _embeddings = CohereEmbeddings(model=model, **embedding_kwargs)
            case "google_vertexai":
                from langchain_google_vertexai import VertexAIEmbeddings

                _embeddings = VertexAIEmbeddings(model=model, **embedding_kwargs)
            case "google_genai":
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                _embeddings = GoogleGenerativeAIEmbeddings(
                    model=model, **embedding_kwargs
                )
            case "fireworks":
                from langchain_fireworks import FireworksEmbeddings

                _embeddings = FireworksEmbeddings(model=model, **embedding_kwargs)
            case "gigachat":
                from langchain_gigachat import GigaChatEmbeddings

                _embeddings = GigaChatEmbeddings(model=model, **embedding_kwargs)
            case "ollama":
                from langchain_ollama import OllamaEmbeddings

                _embeddings = OllamaEmbeddings(
                    model=model,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    **embedding_kwargs,
                )
            case "together":
                from langchain_together import TogetherEmbeddings

                _embeddings = TogetherEmbeddings(model=model, **embedding_kwargs)
            case "netmind":
                from langchain_netmind import NetmindEmbeddings

                _embeddings = NetmindEmbeddings(model=model, **embedding_kwargs)
            case "mistralai":
                from langchain_mistralai import MistralAIEmbeddings

                _embeddings = MistralAIEmbeddings(model=model, **embedding_kwargs)
            case "huggingface":
                from langchain_huggingface import HuggingFaceEmbeddings

                _embeddings = HuggingFaceEmbeddings(model_name=model, **embedding_kwargs)
            case "nomic":
                from langchain_nomic import NomicEmbeddings

                _embeddings = NomicEmbeddings(model=model, **embedding_kwargs)
            case "voyageai":
                from langchain_voyageai import VoyageAIEmbeddings

                _embeddings = VoyageAIEmbeddings(
                    voyage_api_key=os.environ["VOYAGE_API_KEY"],
                    model=model,
                    **embedding_kwargs,
                )
            case "dashscope":
                from langchain_community.embeddings import DashScopeEmbeddings

                _embeddings = DashScopeEmbeddings(model=model, **embedding_kwargs)
            case "bedrock":
                from langchain_aws.embeddings import BedrockEmbeddings

                _embeddings = BedrockEmbeddings(model_id=model, **embedding_kwargs)
            case "aimlapi":
                # Use Ollama instead of OpenAI for AIMLAPI
                from langchain_ollama import OllamaEmbeddings

                _embeddings = OllamaEmbeddings(
                    model=OLLAMA_EMBEDDING_MODEL,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    **embedding_kwargs,
                )
            case _:
                raise Exception("Embedding not found.")

        self._embeddings = _embeddings

    def get_embeddings(self):
        return self._embeddings

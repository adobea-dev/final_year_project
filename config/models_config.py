class ModelConfig:
    """
    Configuration for all LLM, vector DB, and embedding parameters.
    """

    # === LLM MODEL ===
    OLLAMA_MODEL = "tinyllama"     

    # === Embeddings ===
    EMBEDDING_MODEL = "all-minilm"  
    # === VectorDB ===
    VECTOR_DB_PATH = "vectordb/autochek_index"

    # === Chunking for documents ===
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50


model_config = ModelConfig()
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
    ) -> None:
        self.model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            f"query: {text}",
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        embedding = self.model.encode(
            [f"passage: {text}" for text in texts],
            normalize_embeddings=True,
        )

        return embedding.tolist()

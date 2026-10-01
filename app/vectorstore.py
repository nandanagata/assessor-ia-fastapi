"""Cliente Qdrant e geração centralizada de embeddings."""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pymongo import MongoClient
from qdrant_client import QdrantClient, models
import uuid

from app.config import GEMINI_API_KEY, MONGODB_URI, QDRANT_API_KEY, QDRANT_URL

COLLECTION_MEMORIA = "memoria_resumos"
COLLECTION_FAQ = "faq_chunks"
COLLECTION_RESTRICOES_PERFIL = "restricoes_perfil"
EMBEDDING_DIM = 768

class _LazyQdrantClient:
    """Adia a conexão com o Qdrant até a primeira operação real."""

    _client: QdrantClient | None = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                check_compatibility=False,
            )
        return self._client

    def __getattr__(self, nome: str):
        return getattr(self._get_client(), nome)


qdrant = _LazyQdrantClient()

_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2-preview",
    google_api_key=GEMINI_API_KEY,
)
_collections_prontas = False
_mongo: MongoClient | None = None
_indice_perfil_criado = False


def garantir_collections() -> None:
    """Cria as collections e o índice de `user_id` quando ainda não existem."""
    global _collections_prontas
    if _collections_prontas:
        return
    configuracao = models.VectorParams(
        size=EMBEDDING_DIM,
        distance=models.Distance.COSINE,
    )
    if not qdrant.collection_exists(COLLECTION_MEMORIA):
        qdrant.create_collection(COLLECTION_MEMORIA, vectors_config=configuracao)
    if not qdrant.collection_exists(COLLECTION_FAQ):
        qdrant.create_collection(COLLECTION_FAQ, vectors_config=configuracao)
    try:
        qdrant.create_payload_index(
            collection_name=COLLECTION_MEMORIA,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    except Exception as erro:
        if "already exists" not in str(erro).lower():
            raise
    _collections_prontas = True


def gerar_embedding(texto: str) -> list[float]:
    """Gera um vetor de 768 dimensões para um texto."""
    return _embeddings.embed_query(texto, output_dimensionality=EMBEDDING_DIM)


def gerar_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Gera embeddings em lote usando o mesmo modelo e dimensionalidade."""
    return _embeddings.embed_documents(
        textos, output_dimensionality=EMBEDDING_DIM
    )

def _colecao_perfis():
    """Obtém a collection de perfis e garante unicidade por usuário."""
    global _mongo, _indice_perfil_criado
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI não está configurada.")
    if _mongo is None:
        _mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5_000)
    colecao = _mongo["assessor"]["perfis"]
    if not _indice_perfil_criado:
        colecao.create_index("user_id", unique=True)
        _indice_perfil_criado = True
    return colecao


def salvar_perfil_mongo(dados_estruturados: dict) -> None:
    """Cria ou substitui os dados estruturados de um usuário."""
    _colecao_perfis().update_one(
        {"user_id": dados_estruturados["user_id"]},
        {"$set": dados_estruturados},
        upsert=True,
    )


def consultar_perfil_mongo(user_id: str) -> dict | None:
    """Consulta o perfil estruturado do usuário, sem expor o identificador MongoDB."""
    return _colecao_perfis().find_one({"user_id": user_id}, {"_id": 0})


def _garantir_collection_restricoes() -> None:
    if not qdrant.collection_exists(COLLECTION_RESTRICOES_PERFIL):
        qdrant.create_collection(
            collection_name=COLLECTION_RESTRICOES_PERFIL,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )
    try:
        qdrant.create_payload_index(
            collection_name=COLLECTION_RESTRICOES_PERFIL,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    except Exception as erro:
        if "already exists" not in str(erro).lower():
            raise


def salvar_restricoes_qdrant(user_id: str, restricoes: list[str]) -> None:
    """Substitui todas as restrições do usuário, com um vetor por frase."""
    _garantir_collection_restricoes()
    qdrant.delete(
        collection_name=COLLECTION_RESTRICOES_PERFIL,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            )
        ),
        wait=True,
    )
    points = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector=gerar_embedding(frase),
            payload={"user_id": user_id, "texto": frase},
        )
        for frase in restricoes
    ]
    if points:
        qdrant.upsert(
            collection_name=COLLECTION_RESTRICOES_PERFIL,
            points=points,
            wait=True,
        )


def buscar_restricoes_perfil(user_id: str, consulta: str, limite: int = 3) -> list[str]:
    """Busca semanticamente restrições pertencentes somente ao usuário atual."""
    if not qdrant.collection_exists(COLLECTION_RESTRICOES_PERFIL):
        return []
    resultado = qdrant.query_points(
        collection_name=COLLECTION_RESTRICOES_PERFIL,
        query=gerar_embedding(consulta),
        query_filter=models.Filter(
            must=[models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id),
            )]
        ),
        limit=limite,
        with_payload=True,
    )
    return [
        str(ponto.payload.get("texto", ""))
        for ponto in resultado.points
        if ponto.payload and ponto.payload.get("texto")
    ]

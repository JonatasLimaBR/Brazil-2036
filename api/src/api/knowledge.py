from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from api.bigquery_repo import RunQuery
from api.config import Config
from api.models import KnowledgeAskResponse, KnowledgeCitation

_INSUFFICIENT_EVIDENCE_ANSWER = (
    "Evidência insuficiente no corpus indexado para responder com confiança."
)


@dataclass(frozen=True)
class RetrievedNote:
    metric_id: str
    title: str
    body_text: str
    source_url: str
    distance: float


def retrieve(
    run_query: RunQuery,
    config: Config,
    *,
    question: str,
    metric_id_filter: str | None = None,
) -> list[RetrievedNote]:
    # Verified live against brasil2036-dev (BUILD_REPORT): VECTOR_SEARCH needs
    # no CREATE VECTOR INDEX at this corpus size (DESIGN D1), and a NULL-typed
    # @metric_id_filter combined with `WHERE @f IS NULL OR ...` works exactly
    # like a plain SQL filter would.
    sql = (
        "SELECT base.metric_id, base.title, base.body_text, base.source_url, distance "
        "FROM VECTOR_SEARCH("
        f"TABLE {config.rag_corpus_fqtn}, 'embedding', "
        "(SELECT ml_generate_embedding_result AS embedding FROM ML.GENERATE_EMBEDDING("
        f"MODEL {config.rag_embedding_model_fqtn}, (SELECT @question AS content))), "
        "top_k => @top_k, distance_type => 'COSINE') "
        "WHERE @metric_id_filter IS NULL OR base.metric_id = @metric_id_filter "
        "ORDER BY distance ASC"
    )
    rows = run_query(
        sql,
        {
            "question": question,
            "top_k": config.rag_top_k,
            "metric_id_filter": metric_id_filter,
        },
    )
    return [
        RetrievedNote(
            metric_id=r["metric_id"],
            title=r["title"],
            body_text=r["body_text"],
            source_url=r["source_url"],
            distance=float(r["distance"]),
        )
        for r in rows
    ]


class GenerateContent(Protocol):
    def __call__(self, *, model: str, prompt: str) -> str: ...


def compose_answer(
    question: str,
    notes: list[RetrievedNote],
    config: Config,
    *,
    generate: GenerateContent,
) -> KnowledgeAskResponse:
    # Deterministic gate, not an LLM decision (ADR-013, DESIGN §2): whether
    # there is "enough evidence to answer" is decided entirely by the
    # similarity threshold before the model is ever called. The model only
    # synthesizes text from notes this gate already accepted as relevant --
    # it never gets a chance to answer ungrounded.
    relevant = [n for n in notes if n.distance <= config.rag_similarity_threshold]
    if not relevant:
        return KnowledgeAskResponse(
            answer=_INSUFFICIENT_EVIDENCE_ANSWER, citations=[], evidence_sufficient=False
        )

    context = "\n\n".join(
        f"[{n.metric_id}] {n.title}: {n.body_text} (fonte: {n.source_url})" for n in relevant
    )
    prompt = (
        "Responda a pergunta em portugues, usando SOMENTE o contexto abaixo. "
        "Nunca invente informacao fora do contexto fornecido. "
        "Cite o metric_id de cada afirmacao entre colchetes, ex: [selic_mensal].\n\n"
        f"Contexto:\n{context}\n\nPergunta: {question}"
    )
    answer = generate(model=config.rag_generative_model, prompt=prompt)

    return KnowledgeAskResponse(
        answer=answer,
        citations=[
            KnowledgeCitation(metric_id=n.metric_id, title=n.title, source_url=n.source_url)
            for n in relevant
        ],
        evidence_sufficient=True,
    )


def build_genai_generate(project: str, region: str) -> GenerateContent:
    from google import genai

    client = genai.Client(vertexai=True, project=project, location=region)

    def generate(*, model: str, prompt: str) -> str:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text or ""

    return generate

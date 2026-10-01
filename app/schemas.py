from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

class ChatRequest(BaseModel):
    """O que o navegador envia no POST /chat."""
    session_id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    user_id: str = Field(
        default="usuario_teste",
        description="Identificador estável do usuário entre sessões.",
        examples=["usuario_teste"],
    )
    pergunta:   str = Field(..., min_length=1, examples=["gastei 50 reais no mercado"])


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""
    resposta:         str
    agentes_chamados: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    """Ainda não é usado — é do Passo 6 da Etapa 3."""
    session_id: str
    resumo:     str | None = None


class HealthCheck(BaseModel):
    """Resultado de uma dependência ou requisito da aplicação."""

    status: Literal["ok", "not_configured", "unavailable"]
    message: str


class HealthResponse(BaseModel):
    """Contrato do endpoint GET /health."""

    status: Literal["ok", "degraded"]
    checks: dict[str, HealthCheck]

class PerfilCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=120)
    renda_mensal: float = Field(..., gt=0, description="Renda deve ser maior que zero")
    gasto_fixo_mensal: float = Field(..., ge=0, description="Gasto deve ser maior ou igual a zero")
    horizonte_meses: int = Field(..., ge=1, le=120, description="Horizonte entre 1 e 120 meses")
    perfil_investidor: Literal["conservador", "moderado", "arrojado"]
    restricoes: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    ] = Field(..., min_length=1, max_length=5)

    @model_validator(mode="after")
    def validar_gasto_menor_que_renda(self):
        if self.gasto_fixo_mensal >= self.renda_mensal:
            raise ValueError("O gasto fixo mensal deve ser menor que a renda mensal")
        return self

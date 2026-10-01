import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas import PerfilCreate

app = importlib.import_module("app.main")
vectorstore = importlib.import_module("app.vectorstore")


DADOS_VALIDOS = {
    "user_id": "usuario_teste",
    "renda_mensal": 5_000,
    "gasto_fixo_mensal": 2_000,
    "horizonte_meses": 24,
    "perfil_investidor": "moderado",
    "restricoes": ["sem criptomoedas", "evitar alto risco"],
}


class PerfilTests(unittest.TestCase):
    def test_validacao_do_perfil(self):
        perfil = PerfilCreate.model_validate(DADOS_VALIDOS)
        self.assertEqual(perfil.user_id, "usuario_teste")

        for alteracao in (
            {"renda_mensal": 0},
            {"gasto_fixo_mensal": 5_000},
            {"horizonte_meses": 121},
            {"perfil_investidor": "agressivo"},
            {"restricoes": []},
        ):
            with self.subTest(alteracao=alteracao):
                with self.assertRaises(ValidationError):
                    PerfilCreate.model_validate(DADOS_VALIDOS | alteracao)

    def test_rota_perfil_persiste_as_duas_partes(self):
        salvar_mongo = Mock()
        salvar_qdrant = Mock()
        with (
            patch.object(app, "salvar_perfil_mongo", salvar_mongo),
            patch.object(app, "salvar_restricoes_qdrant", salvar_qdrant),
        ):
            resposta = TestClient(app.app).post("/perfil", json=DADOS_VALIDOS)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), DADOS_VALIDOS)
        salvar_mongo.assert_called_once_with({
            "user_id": "usuario_teste",
            "renda_mensal": 5_000.0,
            "gasto_fixo_mensal": 2_000.0,
            "horizonte_meses": 24,
            "perfil_investidor": "moderado",
        })
        salvar_qdrant.assert_called_once_with(
            "usuario_teste", ["sem criptomoedas", "evitar alto risco"]
        )

    def test_mongo_atualiza_um_perfil_por_usuario(self):
        colecao = Mock()
        dados = {"user_id": "usuario_teste", "renda_mensal": 5_000}
        with patch.object(vectorstore, "_colecao_perfis", return_value=colecao):
            vectorstore.salvar_perfil_mongo(dados)

        colecao.update_one.assert_called_once_with(
            {"user_id": "usuario_teste"}, {"$set": dados}, upsert=True
        )

    def test_qdrant_substitui_e_isola_restricoes(self):
        cliente = Mock()
        with (
            patch.object(vectorstore, "qdrant", cliente),
            patch.object(vectorstore, "_garantir_collection_restricoes"),
            patch.object(
                vectorstore,
                "gerar_embedding",
                side_effect=lambda texto: [float(len(texto))] * 768,
            ),
        ):
            vectorstore.salvar_restricoes_qdrant(
                "usuario_teste", ["sem criptomoedas", "evitar alto risco"]
            )

            seletor = cliente.delete.call_args.kwargs["points_selector"].filter
            self.assertEqual(seletor.must[0].match.value, "usuario_teste")
            pontos = cliente.upsert.call_args.kwargs["points"]
            self.assertEqual(
                [p.payload["texto"] for p in pontos],
                ["sem criptomoedas", "evitar alto risco"],
            )
            self.assertTrue(
                all(p.payload["user_id"] == "usuario_teste" for p in pontos)
            )
            self.assertTrue(all(len(p.vector) == 768 for p in pontos))

            cliente.collection_exists.return_value = True
            cliente.query_points.return_value = SimpleNamespace(points=[
                SimpleNamespace(payload={"texto": "sem criptomoedas"})
            ])
            resultado = vectorstore.buscar_restricoes_perfil(
                "usuario_teste", "não quero moedas digitais"
            )

        filtro = cliente.query_points.call_args.kwargs["query_filter"]
        self.assertEqual(filtro.must[0].match.value, "usuario_teste")
        self.assertEqual(resultado, ["sem criptomoedas"])


if __name__ == "__main__":
    unittest.main()

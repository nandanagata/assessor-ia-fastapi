# Justificativa da implementação do perfil financeiro

## 1. Quais arquivos foram criados ou modificados?

- `app/schemas.py`: criação do schema `PerfilCreate` e das validações do formulário.
- `app/main.py`: criação da rota `POST /perfil`.
- `app/vectorstore.py`: persistência no MongoDB e indexação e busca no Qdrant.
- `app/tools/financeiro.py`: criação da tool `consultar_perfil_usuario`.
- `app/prompts.py`: instruções para o especialista consultar o perfil antes de aconselhar.
- `app/graph.py`: não precisou ser alterado nesta implementação; o fluxo já importava a lista `TOOLS` e já propagava o `user_id` pelo `RunnableConfig`.
- `frontend/app.js`: definição do mesmo `user_id` usado pelo formulário.
- `frontend/perfil_front/perfil.css`: correção do caminho que importa o CSS principal.
- `tests/test_perfil.py`: testes automatizados do cadastro e da persistência.

O HTML e o JavaScript da tela de perfil não foram alterados. No CSS dessa tela, foi corrigida somente a importação de `style.css` para `../style.css`.

## 2. Por onde o perfil entra e onde cada parte é gravada?

O perfil entra na aplicação pela rota `POST /perfil`. A requisição possui `user_id`, `renda_mensal`, `gasto_fixo_mensal`, `horizonte_meses`, `perfil_investidor` e `restricoes`.

O FastAPI valida esses dados com o schema `PerfilCreate`. A renda deve ser maior que zero; o gasto fixo deve ser maior ou igual a zero e menor que a renda; o horizonte deve estar entre 1 e 120 meses; o perfil deve ser `conservador`, `moderado` ou `arrojado`; e devem existir entre uma e cinco restrições não vazias.

Os campos estruturados são gravados na collection `assessor.perfis` do MongoDB. O método `update_one`, com `upsert=True`, atualiza o perfil existente ou cria um novo documento. O índice único de `user_id` impede vários perfis para o mesmo usuário.

As restrições são gravadas na collection `restricoes_perfil` do Qdrant. Cada frase vira um ponto independente, com seu próprio vetor e um payload contendo `user_id` e `texto`. Antes da gravação, os pontos anteriores daquele usuário são removidos. Assim, o novo envio substitui completamente a lista antiga.

## 3. Como o texto livre é indexado e consultado?

Cada restrição é transformada em um embedding de 768 dimensões pelo modelo `gemini-embedding-2-preview`. Ao consultar o perfil, a pergunta também é transformada em embedding e enviada ao Qdrant.

O Qdrant usa distância de cosseno para localizar as restrições semanticamente mais próximas. Por exemplo, uma pergunta sobre “moedas digitais” pode encontrar uma restrição cadastrada como “não investir em criptomoedas”, mesmo sem repetir exatamente as mesmas palavras.

## 4. Foi criada uma tool ou duas? Por quê?

Foi criada uma única tool, chamada `consultar_perfil_usuario`. Ela recebe o contexto da pergunta, identifica o `user_id` pelo `RunnableConfig`, lê os dados estruturados no MongoDB e busca no Qdrant as restrições relevantes.

Uma única tool é suficiente porque todos esses dados pertencem ao mesmo perfil financeiro. O especialista recebe o contexto completo em uma chamada e não precisa conhecer os detalhes dos bancos utilizados.

## 5. Como os dados de usuários diferentes ficam isolados?

O `user_id` é propagado da requisição do chat para o contexto do LangGraph. A tool lê esse valor do `RunnableConfig`; o modelo não escolhe livremente qual usuário consultar.

No MongoDB, a consulta utiliza `{"user_id": user_id}`. No Qdrant, a busca aplica um filtro obrigatório no campo `user_id`. Dessa forma, uma consulta não recupera o perfil nem as restrições de outro usuário.

Na interface atual, o formulário e o chat usam o identificador estável `usuario_teste`, garantindo que o especialista encontre o cadastro preenchido na tela.

## 6. A tool consulta os bancos diretamente ou chama a própria API?

A tool consulta diretamente as funções da camada de persistência. Ela não faz uma requisição HTTP para a própria API.

Essa escolha evita uma chamada de rede desnecessária, reduz a quantidade de pontos de falha e reutiliza a mesma lógica de acesso ao MongoDB e ao Qdrant.

## 7. Por que não foi criado um agente de perfil?

O perfil não representa um novo assunto de atendimento. Ele fornece contexto para o especialista financeiro tomar decisões adequadas à renda, aos gastos, ao horizonte e às restrições do usuário.

Por isso, a consulta foi adicionada como ferramenta do especialista financeiro existente, sem criar um agente de perfil.

## 8. Por que o chat não pode alterar o cadastro?

O modelo interpreta linguagem natural e poderia entender incorretamente um pedido ou uma informação mencionada durante a conversa. Permitir alterações automáticas poderia modificar renda, gastos ou restrições por engano.

A escrita fica concentrada na tela de perfil, que apresenta campos explícitos e passa pelas validações do FastAPI. O chat apenas consulta esses dados.

## 9. Como o funcionamento foi verificado?

Foram executados quatro testes automatizados:

- validação dos campos do perfil;
- funcionamento da rota `POST /perfil`;
- atualização do perfil no MongoDB por `user_id`;
- substituição, busca e isolamento das restrições no Qdrant.

Também foi realizado um teste integrado com os serviços configurados. A gravação e a leitura no MongoDB funcionaram, a busca semântica no Qdrant encontrou uma restrição por significado e a atualização substituiu os pontos anteriores. Os dados temporários usados no teste foram removidos.

Por fim, foi feito um cadastro real pela API para `usuario_teste`, confirmando a persistência dos dados estruturados no MongoDB e da restrição no Qdrant Cloud.
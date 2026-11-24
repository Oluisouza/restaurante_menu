# Comanda Digital

Sistema de atendimento para restaurantes: abertura de comandas, lançamento de pedidos em tela de PDV, fila da cozinha, fechamento de conta e indicadores de venda. Na P2, o MVP virou um **mini-SaaS**: vários restaurantes usam a mesma instalação, cada um enxergando só os próprios dados, com papéis de acesso, dashboard e API REST.

**Disciplina:** Laboratório de Programação Full Stack
**Tema:** 09, Cardápio Digital
**Stack:** Django 5.2, PostgreSQL, Django REST Framework 3.18, Django Templates (MPA), Chart.js 4.5 e CSS próprio

---

## O que a P2 acrescentou

| Pilar | Como foi resolvido | Onde está |
|---|---|---|
| Multi-organização | Coluna discriminadora: todo dado de negócio tem FK para `Restaurante` | `core/models.py`, `core/utils.py` |
| Perfis de acesso | `Perfil` liga o usuário a um restaurante, com papel de **Gerente** ou **Atendente** | `core/models.py`, `core/utils.py`, `core/permissoes.py` |
| Dashboard | Métricas pelo ORM, filtro de período validado, gráfico, exportação em CSV | `atendimento/dashboard.py`, `atendimento/views.py` |
| API REST | DRF com autenticação, isolamento por restaurante e permissão por papel | `cardapio/api_views.py`, `atendimento/api_views.py` |

O estado do projeto na entrega da P1 está marcado com a tag `v1.0-base`. Tudo o que veio depois está no histórico de commits, um por intenção. As dívidas técnicas levantadas antes de começar a P2 estão em [`MELHORIAS_P1.md`](MELHORIAS_P1.md).

## A decisão central do projeto

O sistema trata as três situações reais de um salão com **uma única abstração**, a comanda:

| Situação | Como é representado |
|---|---|
| Viagem ou balcão | Comanda sem mesa (`mesa = NULL`) |
| Mesa compartilhada | Uma comanda vinculada à mesa |
| Contas individuais na mesma mesa | Várias comandas apontando para a mesma mesa |

A `ForeignKey` para `Mesa` é **opcional** e **não tem restrição de unicidade**. É essa escolha que faz os três casos caberem numa entidade só, e que resolve de graça o problema de dividir a conta: a conta nunca esteve junta.

## Multi-restaurante

Estratégia: **coluna discriminadora**. Um banco, um schema, uma migração. Todo model de negócio herda da base abstrata `DoRestaurante`, que acrescenta a FK `restaurante`. Os itens da comanda e os adicionais não têm a FK: pertencem ao restaurante pela comanda.

- **Um único lugar define o restaurante.** `restaurante_atual(request)` lê o restaurante do perfil do usuário logado. Usuário sem perfil, inclusive o superusuário, recebe **403** nas telas de negócio.
- **Toda consulta filtra.** Telas, busca, cozinha, resumo, dashboard, CSV e API partem de `filter(restaurante=...)`.
- **ID de outro restaurante na URL dá 404**, como se o registro não existisse: `get_object_or_404(..., restaurante=...)`.
- **O restaurante nunca vem do formulário.** Os formulários recebem `restaurante=` na construção, carimbam o registro e filtram os selects (categoria, mesa, prato, adicionais).
- **O model também se defende.** `clean()` recusa misturar restaurantes, por exemplo um prato na categoria de outro restaurante.
- **Unicidade por restaurante.** Dois restaurantes podem ter um prato chamado "Espresso" ou uma "Mesa 01"; o mesmo restaurante não pode repetir.
- **Migração sem perda dos dados da P1**, em três etapas: FK opcional, `RunPython` levando tudo para o "Restaurante padrão" e FK obrigatória.

## Papéis

| | Gerente | Atendente |
|---|---|---|
| Salão, comandas, PDV, cozinha, fechar conta, cardápio | Sim | Sim |
| Dashboard: cartões, ranking, formas de pagamento | Sim | Sim |
| Dashboard: gráfico por dia e exportação CSV | Sim | Não |
| Gerenciar cardápio (criar, editar, excluir) | Sim | Não (403) |
| API de pratos: ler | Sim | Sim |
| API de pratos: criar, alterar, apagar | Sim | Não (403) |

A permissão é aplicada em três camadas:

1. **Na view**, que é a proteção de verdade: o decorator `@gerente_requerido` devolve 403 mesmo para quem digita a URL à mão. Na API, a classe `GerenteAltera` libera leitura e restringe escrita.
2. **No template**, por conforto: o menu esconde o que o usuário não pode usar.
3. **No contexto**: o dado que o atendente não vê nem é calculado.

Um usuário novo nasce **Atendente** (menor privilégio). Na migração que criou o campo, os perfis que já existiam viraram Gerente, porque antes tinham acesso a tudo.

## Dashboard

Começa pelas perguntas do dono do restaurante:

| Pergunta | Métrica | Tipo |
|---|---|---|
| Quanto vendi no período? | Faturamento, comandas fechadas, ticket médio, descontos | KPI (`aggregate`) |
| O que mais sai? | Itens mais vendidos em unidades | Ranking (`values` + `annotate`) |
| Como as vendas evoluíram? | Faturamento por dia, com os dias sem venda preenchidos com zero | Série (`TruncDate`) |
| Como os clientes pagam? | Total e quantidade por forma de pagamento | Distribuição |

- Todas as métricas ficam em `atendimento/dashboard.py` e partem da mesma base: comandas **fechadas** de **um** restaurante no período. A tela, o resumo do dia, o CSV e a API chamam as mesmas funções, então não têm como divergir.
- O período é validado por um `PeriodoForm`: padrão dos últimos 30 dias, no máximo um ano, início antes do fim. Data malformada na URL mostra um aviso, nunca erro 500. Na API, ela responde 400.
- O gráfico usa `json_script` e Chart.js servido localmente pela pasta `static`, sem depender de CDN.
- O CSV sai com `;` e BOM para abrir direto no Excel em português, e neutraliza células que começam com `=`, `+`, `-` ou `@`, que o Excel executaria como fórmula.

## API REST

Autenticação por sessão do Django. Sem login, toda a API responde 403. A Browsable API do DRF aceita login em `/api-auth/login/`.

| Verbo | Endereço | Ação | Quem pode |
|---|---|---|---|
| GET | `/api/pratos/` | Listar os pratos do restaurante | Gerente e atendente |
| POST | `/api/pratos/` | Criar prato | Gerente |
| GET | `/api/pratos/<id>/` | Detalhar | Gerente e atendente |
| PUT, PATCH | `/api/pratos/<id>/` | Atualizar | Gerente |
| DELETE | `/api/pratos/<id>/` | Apagar (prato já usado em comanda ou combo responde 400) | Gerente |
| GET | `/api/dashboard/?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | Indicadores, ranking e formas de pagamento do período | Gerente e atendente |

O serializer lista os campos explicitamente e delega a validação ao model (`validate_constraints()`). As mesmas regras valem na tela, no Admin e na API, e uma violação vira **400 com mensagem**, nunca 500. Prato de outro restaurante responde 404.

## Decisões técnicas

**Preço congelado (snapshot).** `ItemComanda.preco_unitario` guarda uma cópia do preço no instante do lançamento, e `Comanda.total_pago` congela o valor no fechamento. Reajustar o cardápio não altera comandas passadas.

**`DecimalField` para dinheiro, com arredondamento explícito.** A taxa de serviço usa `ROUND_HALF_UP` (convenção de varejo). A prévia em JavaScript do fechamento calcula em centavos inteiros para chegar ao mesmo resultado.

**Estado derivado não vira campo.** `Mesa.ocupada`, `Comanda.subtotal` e `Comanda.total` são calculados. Duas fontes para a mesma informação acabam divergindo.

**Regras de negócio no model.** A máquina de estados do item (`mudar_status`), o lançamento de produtos (`lancar`), o fechamento, o cancelamento e a regra "só item pendente pode ser alterado" vivem nos models. Views da P1, API e Admin chamam os mesmos métodos.

**Integridade garantida pelo banco.** Dez `CheckConstraint` e cinco `UniqueConstraint`: item é prato *ou* combo, quantidades mínimas, preço maior que zero, descontos não negativos, capacidade mínima de mesa, coerência entre tipo de atendimento e mesa, item cancelado com motivo obrigatório, prato não repetido dentro de um combo e nomes únicos por restaurante ignorando maiúsculas. `on_delete=PROTECT` impede apagar o que está em uso.

**Cancelamento sem apagar.** Item cancelado muda de estado, registra motivo e horário, sai do total e continua visível, riscado, na comanda. Só um item ainda pendente pode ser removido sem rastro.

**Preço não é editável no lançamento.** O atendente não altera o valor de um item; o gerente altera o cardápio, e exceções viram desconto registrado no fechamento. É segregação de funções, e os papéis da P2 a tornaram uma regra do sistema.

**Desempenho medido.** A lista de comandas e o salão carregam itens e adicionais com `prefetch_related`, e `Prefetch(..., to_attr=...)` no caso das mesas. Um teste com `assertNumQueries` trava a correção: o número de consultas com 4 comandas tem de ser o mesmo com 20. Antes da correção eram 85 e 127 consultas; depois, 7 e 12.

## Modelo de dados

```
                       Restaurante ──< Perfil >── User
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
Categoria ──< Prato >──< ComboItem >── Combo   Mesa
                 │                       │      │
                 └───────────┬───────────┘      │
                             │                  │
                  ItemComanda >──── Comanda >───┘
                       │
                 ItemAdicional
```

- **core**: `Restaurante`, `Perfil` e a base abstrata `DoRestaurante`
- **cardapio**: `Categoria`, `Prato`, `Combo`, `ComboItem`
- **atendimento**: `Mesa`, `Comanda`, `ItemComanda`, `ItemAdicional`

Os apps de negócio são dois porque os ciclos de vida são diferentes: o cardápio muda raramente e é gerido pelo gerente; o atendimento muda a cada minuto e é operado pelo atendente. O `core` guarda o que é transversal ao sistema.

## Como rodar

```bash
git clone https://github.com/Oluisouza/restaurante_menu.git
cd restaurante_menu

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
```

Preencha o `.env` com as credenciais do PostgreSQL e use `DEBUG=True`. Sem essa variável o padrão é `False` e, com `ALLOWED_HOSTS` vazio, o `runserver` não inicia.

Gere uma `SECRET_KEY` e cole no `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Crie um banco PostgreSQL vazio, com encoding **UTF8**, usando o nome que você colocou em `DB_NAME`. Depois:

```bash
python manage.py migrate
python manage.py carregar_dados                                  # cardápio e mesas do "Restaurante padrão"
python manage.py carregar_dados --restaurante "Outro Restaurante" # opcional: um segundo restaurante
python manage.py createsuperuser
python manage.py runserver
```

O superusuário entra no Admin, mas as telas do sistema exigem um **perfil**. No Admin (`/admin/`), em **Perfis > Adicionar perfil**, ligue o usuário a um restaurante e escolha o papel **Gerente**. Para ver os papéis em ação, crie um segundo usuário com papel **Atendente**.

O `carregar_dados` é idempotente: recria o que tiver sido apagado sem duplicar o que já existe.

## Testes

```bash
python manage.py test
```

São **118 testes**: 9 no `core`, 34 no `cardapio` e 75 no `atendimento`. Cobrem as regras de negócio, as constraints do banco, as entradas forjadas, o isolamento entre restaurantes, os papéis, a API, as métricas do dashboard com números conferíveis à mão e o número de consultas das listagens. A base `TesteComRestaurante` (`core/para_testes.py`) cria um restaurante e um gerente logado para cada teste.

Cada teste foi validado por mutação: a regra que ele deveria proteger foi quebrada de propósito, e o teste só foi aceito quando falhou.

### Roteiro de isolamento

O roteiro da Aula 14, com dois usuários de restaurantes diferentes, foi transformado em testes automatizados. Resultado da última execução: **todos os cenários passaram**.

| Cenário | Esperado | Teste |
|---|---|---|
| Usuário A abre as listas (comandas, salão, cardápio, cozinha) | Vê só os registros do restaurante A | `IsolamentoComandasTest`, `IsolamentoItensTest`, `IsolamentoCardapioTest` |
| Usuário A abre, edita ou exclui um registro do B pela URL | 404, e o registro do B fica intacto | `test_prato_de_outro_restaurante_da_404`, `test_comanda_e_mesa_de_outro_restaurante_dao_404`, `test_item_de_outro_restaurante_da_404` |
| Usuário A cria um registro | Gravado com o restaurante A | `test_prato_novo_nasce_no_restaurante_do_usuario`, `test_comanda_nova_nasce_no_restaurante_e_so_aceita_mesa_dele` |
| Formulário do A recebe uma opção do B | Recusada com erro de validação | `test_categoria_de_outro_restaurante_e_recusada`, `test_editar_item_nao_aceita_prato_de_outro_restaurante` |
| PDV do A recebe um produto do B | Não aparece e não é lançado | `test_pdv_nao_mostra_nem_lanca_produto_de_outro_restaurante` |
| Usuário A usa um nome já usado pelo B | Permitido: a unicidade é por restaurante | `test_mesmo_nome_em_restaurantes_diferentes_e_permitido` |
| Resumo, dashboard e CSV do A | Só números do A | `test_resumo_conta_so_o_proprio_restaurante`, `test_padrao_ultimos_30_dias_so_do_proprio_restaurante`, `test_csv_tem_o_periodo_e_o_restaurante_certos` |
| API do A | Lista só os pratos do A; prato do B dá 404 | `IsolamentoApiTest` |
| Usuário sem perfil | 403 | `SemPerfilTest`, `test_usuario_sem_perfil_recebe_403` |
| Atendente abre a gestão, o CSV ou altera pela API | 403, e nada muda no banco | `PapelTest`, `test_atendente_le_mas_nao_altera` |

## Rotas

| Endereço | Tela |
|---|---|
| `/` | Salão com as mesas |
| `/comandas/` | Lista com filtro por status |
| `/comandas/nova/<tipo>/` | Abrir comanda (`mesa`, `viagem` ou `balcao`) |
| `/comandas/<id>/` | Detalhe e conta |
| `/comandas/<id>/itens/novo/` | Tela de PDV |
| `/comandas/<id>/fechar/` | Fechamento de conta |
| `/comandas/<id>/cancelar/` | Confirmação de cancelamento |
| `/itens/<id>/editar/` | Editar item |
| `/itens/<id>/excluir/` | Remover item pendente |
| `/itens/<id>/cancelar/` | Cancelar item com motivo |
| `/mesas/<id>/` | Histórico da mesa |
| `/cozinha/` | Fila de preparo |
| `/resumo/` | Resumo do dia (`?data=AAAA-MM-DD` para outros dias) |
| `/dashboard/` | Dashboard (`?inicio=AAAA-MM-DD&fim=AAAA-MM-DD`) |
| `/dashboard/exportar/` | CSV do período (só gerente) |
| `/cardapio/` | Cardápio |
| `/cardapio/pratos/` | Gerenciar cardápio (só gerente) |
| `/contas/login/` | Entrar |
| `/api/...` | API REST (ver acima) |
| `/admin/` | Django Admin |

## Limitações conhecidas

Documentadas como decisão consciente de escopo, não como omissão.

- **Sem controle de concorrência.** Incrementos de quantidade usam leitura e escrita em Python em vez de `F()`, e `fechar()` não usa `transaction.atomic()` com `select_for_update()`. Dois terminais simultâneos podem perder um incremento ou fechar a mesma comanda duas vezes. Está registrado no item 5 do `MELHORIAS_P1.md`.
- **O código da comanda é gerado depois do primeiro INSERT** (`CMD00001` a partir do `pk`). Duas criações simultâneas podem colidir no valor vazio temporário.
- **Sem tempo real.** A tela da cozinha exige recarga manual.
- **Sem paginação.** As listagens não crescem em número de consultas, mas crescem em tamanho. O histórico da mesa ainda calcula o total de cada comanda sem `prefetch_related`.
- **API só de pratos e do dashboard.** Comandas e mesas ainda são operadas só pelas telas.
- **Cadastro de restaurantes, usuários e perfis pelo Admin.** Não há tela própria de convite ou de gestão de equipe.
- **`ALLOWED_HOSTS` vazio** e mídia servida só com `DEBUG=True`. Configurações de implantação ficaram fora desta etapa.

## Origem

O domínio foi validado previamente no **Café Teria**, um PDV em FastAPI + React desenvolvido para a disciplina de Arquitetura e Projeto de Software.

Este projeto **não reaproveita aquele código**: foi reconstruído em Django. O que atravessou foi o entendimento do domínio e o desenho de interação da tela de PDV. O que foi deliberadamente corrigido:

| Dívida do sistema anterior | Correção aqui |
|---|---|
| Itens da comanda numa string concatenada | Tabela `ItemComanda`, uma linha por item |
| Mesa como texto livre em `nome_cliente` | Entidade `Mesa` com FK |
| Sem snapshot de preço | `preco_unitario` e `total_pago` congelados |
| Pedido nascia já pago | Ciclo aberta, fechada ou cancelada |
| Fila da cozinha em memória (Singleton, `--workers 1`) | Consulta com `ORDER BY` |
| `if/elif` escolhendo a estratégia de pagamento | `choices` no model |
| `print()` como log | `self.stdout.write` nos comandos |
| Schema SQL aplicado à mão | Migrations versionadas |
| Regra "sempre em minúsculo" documentada em comentário | `UniqueConstraint` com `Lower()` no banco |
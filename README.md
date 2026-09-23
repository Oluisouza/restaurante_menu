# Comanda Digital

Sistema de atendimento para restaurantes: abertura de comandas, lançamento de pedidos em tela de PDV e fechamento de conta. Validado num contexto de cafeteria, mas o domínio é modelado de forma genérica — nada no modelo de dados assume café.

**Disciplina:** Laboratório de Programação Full Stack
**Tema:** 09 — Cardápio Digital
**Stack:** Django 5.2 · PostgreSQL 17+ · Django Templates (MPA) · CSS próprio

---

## A decisão central do projeto

O sistema trata as três situações reais de um salão com **uma única abstração** — a comanda:

| Situação | Como é representado |
|---|---|
| Viagem / balcão | Comanda sem mesa (`mesa = NULL`) |
| Mesa compartilhada | Uma comanda vinculada à mesa |
| Contas individuais na mesma mesa | Várias comandas apontando para a mesma mesa |

A `ForeignKey` para `Mesa` é **opcional** e **não tem restrição de unicidade**. É essa escolha que faz os três casos caberem numa entidade só — e que resolve de graça o problema de dividir a conta, porque a conta nunca esteve junta.

## Decisões técnicas

**Preço congelado (snapshot).** `ItemComanda.preco_unitario` guarda uma cópia do preço no instante do lançamento, e `Comanda.total_pago` congela o valor no fechamento. Reajustar o cardápio não altera comandas passadas. Trocar o produto de um item, por outro lado, recaptura o preço — é uma operação diferente.

**`DecimalField` para dinheiro, com arredondamento explícito.** Ponto flutuante acumula erro de centavo. A taxa de serviço usa `ROUND_HALF_UP` (convenção de varejo), e não o `ROUND_HALF_EVEN` que o `Decimal` aplica por padrão. A prévia em JavaScript calcula em centavos inteiros para chegar ao mesmo resultado.

**Estado derivado não vira campo.** `Mesa.ocupada`, `Comanda.subtotal` e `Comanda.total` são calculados. Dado que pode ser derivado não é armazenado — duas fontes para a mesma informação acabam divergindo.

**Regras de negócio no model.** `Comanda.fechar()`, `Comanda.cancelar()` e `ItemComanda.cancelar()` vivem nos models e valem em qualquer contexto que use o ORM. As validações de `clean()`, por natureza, só rodam em formulário — por isso as regras que não podem falhar foram levadas para o banco.

**Integridade garantida pelo banco.** Dez `CheckConstraint` e quatro `UniqueConstraint` cobrem: item é prato *ou* combo, quantidades mínimas, preços e descontos não negativos, capacidade mínima de mesa, coerência entre tipo de atendimento e mesa, item cancelado com motivo obrigatório, prato não repetido dentro de um combo, e nomes únicos ignorando maiúsculas em categoria, prato e combo. `on_delete=PROTECT` impede apagar o que está em uso.

**Soft delete no cancelamento de item.** Item cancelado não é apagado: muda de estado, registra motivo e data, e sai do total. A constraint `item_cancelado_tem_motivo` garante que nenhum caminho — nem `update()`, nem shell, nem script — deixe um cancelamento sem justificativa.

**Máquina de estados explícita.** As transições de status do item são um dicionário na view da cozinha, não uma cadeia de `if`. Não é possível voltar de "entregue" para "pendente" nem alterar item de comanda fechada. O Admin não contorna a regra: `status` é somente leitura e comanda encerrada é imutável.

**Preço não é editável no lançamento.** O atendente não altera o valor de um item; o gerente altera o cardápio, e exceções viram desconto registrado no fechamento. É segregação de funções: quem define preço não é quem cobra.

**Entrada do cliente é validada antes do ORM.** Todo id vindo de `POST` ou de querystring passa por uma peneira: valor não numérico vira 404, nunca erro 500. O PDV também recusa lançar como item avulso um prato de categoria de adicionais.

## Modelo de dados

```
Categoria ──< Prato >──< ComboItem >── Combo
                 │                        │
                 └──────────┬─────────────┘
                            │
Mesa ──< Comanda ──< ItemComanda ──< ItemAdicional
```

- **cardapio**: `Categoria`, `Prato`, `Combo`, `ComboItem`
- **atendimento**: `Mesa`, `Comanda`, `ItemComanda`, `ItemAdicional`

Dois apps porque os ciclos de vida são diferentes: o cardápio muda raramente e é gerido pelo gerente; o atendimento muda a cada minuto e é operado pelo atendente.

## Funcionalidades

- Abertura de comanda por tipo de atendimento (mesa, viagem, balcão), com o tipo vindo da URL — o atendente não escolhe num select
- Múltiplas comandas simultâneas na mesma mesa
- **Tela de PDV**: grade de produtos por categoria, clique adiciona ao carrinho, e clicar de novo incrementa a linha existente em vez de duplicar
- **Personalização de item na própria tela do PDV**: quantidade, observação e adicionais, sem sair do carrinho
- Ajuste de quantidade e remoção direto no carrinho, apenas para item ainda pendente
- Edição de item (produto, quantidade, observação) pela tela da comanda
- Fechamento com forma de pagamento, taxa de serviço e desconto, com **prévia do total antes de confirmar**
- Cancelamento de comanda com tela de confirmação
- Painel da cozinha com fila FIFO e transições de status validadas
- **Resumo do dia**: faturamento, ticket médio, descontos concedidos, comandas canceladas, totais por forma de pagamento e itens mais vendidos, com navegação entre dias
- CRUD dos itens do cardápio pela tela (categorias e combos pelo Admin), com controle de disponibilidade
- Busca e filtros nas listagens

## Como rodar

```bash
git clone <url>
cd restaurante_menu

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
```

Preencha o `.env` com as credenciais do PostgreSQL. **Mantenha `DEBUG=True`** (já vem no `.env.example`). Sem essa variável o padrão é `False` e, com `ALLOWED_HOSTS = []`, o `runserver` não inicia.

Gere uma `SECRET_KEY` e cole no `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Crie um banco PostgreSQL vazio, com encoding **UTF8**, usando o nome que você colocou em `DB_NAME`. Depois:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py carregar_dados    # cardápio e mesas de exemplo
python manage.py runserver
```

O `carregar_dados` é idempotente: recria categorias, pratos, combos e mesas de exemplo que tenham sido apagados, sem duplicar o que já existe. Não desfaz alterações de preço, nome ou disponibilidade.

## Testes

```bash
python manage.py test
```

São 41 testes. Cobrem o GET das telas principais e as regras de negócio centrais: snapshot de preço, fechamento sem itens, desconto acima do total, arredondamento da taxa, congelamento do `total_pago`, ocupação da mesa, comandas individuais na mesma mesa, exclusão de prato vendido, transições da cozinha, personalização de item com adicionais, resumo do dia, cancelamento de item com motivo, as constraints do banco e as respostas a entradas forjadas.

Cada teste foi validado por mutação: a regra que ele deveria proteger foi quebrada de propósito, e o teste só foi aceito quando falhou.

## Rotas

| Endereço | Tela |
|---|---|
| `/` | Salão com as mesas |
| `/comandas/` | Lista com filtro por status |
| `/comandas/nova/<tipo>/` | Abrir comanda (`mesa`, `viagem` ou `balcao`) |
| `/comandas/<id>/` | Detalhe e totais |
| `/comandas/<id>/itens/novo/` | Tela de PDV |
| `/comandas/<id>/fechar/` | Fechamento de conta |
| `/comandas/<id>/cancelar/` | Confirmação de cancelamento |
| `/itens/<id>/editar/` | Editar item |
| `/itens/<id>/excluir/` | Remover item |
| `/mesas/<id>/` | Comandas da mesa |
| `/cozinha/` | Fila de preparo |
| `/resumo/` | Resumo do dia (`?data=AAAA-MM-DD` para outros dias) |
| `/cardapio/` | Cardápio |
| `/cardapio/pratos/` | Gerenciar cardápio |
| `/admin/` | Django Admin |

## Limitações conhecidas

Levantadas em revisões de código feitas antes da entrega. Estão documentadas como decisão consciente de escopo, não como omissão.

### Fora do escopo do P1, previstas para o P2

- **Não há autenticação.** Nenhuma tela exige login — apenas o `/admin/`. Qualquer pessoa com acesso à máquina pode operar o sistema. Autenticação e papéis (atendente, cozinha, gerente) são requisito do P2.
- **Sem tempo real.** A tela da cozinha exige recarga manual. O P2 prevê SSE.
- **Um restaurante por instalação.** Multi-restaurante é requisito do P2.
- **Sem API REST.** Prevista para o P2, com Django REST Framework.

### Em andamento

- **Cancelamento de item com motivo: modelo pronto, telas pendentes.** `ItemComanda.cancelar(motivo)` registra motivo e data, tira o item do total e é garantido por constraint no banco. As telas ainda usam exclusão física, então na prática o atendente continua conseguindo remover um item já enviado à cozinha sem deixar rastro. A tela de cancelamento é o próximo passo.
- **Itens cancelados não aparecem na tela da comanda.** Saem do total e da lista; hoje o registro só é visível no Admin.

### Decisões conscientes

- **Fechar a comanda tira os itens pendentes da fila da cozinha.** Em balcão e viagem, onde o cliente costuma pagar antes do preparo, o pedido some da fila ao ser pago. A correção depende de definir a regra de negócio: ou bloquear o fechamento com itens não entregues, ou manter na fila os itens pendentes de comandas já fechadas.
- **O Admin é ferramenta de manutenção, não de operação.** Comanda encerrada é somente leitura, `status` e `total_pago` nunca são editáveis, itens de comanda encerrada não podem ser alterados nem excluídos, e a exclusão em lote foi desativada — porque ela verifica permissão por tipo de objeto, nunca por registro. O que o Admin ainda permite é excluir uma comanda **aberta**, que é operação de limpeza de dados de teste.

### Limitações técnicas assumidas

- **Sem controle de concorrência.** Incrementos de quantidade usam leitura-e-escrita em Python (`quantidade += 1`) em vez de `F()`, e `fechar()` não usa `transaction.atomic()` nem `select_for_update()`. Dois terminais simultâneos podem perder um incremento ou fechar a mesma comanda duas vezes. Irrelevante com um operador; obrigatório antes de uso real.
- **`Comanda.save()` grava `codigo=''` no primeiro INSERT** antes de gerar o código a partir do `pk`. Como `codigo` é `unique`, duas criações simultâneas colidem.
- **Consultas N+1.** Os totais são propriedades que refazem a consulta a cada acesso, e as listagens não têm paginação nem filtro de data. O custo cresce com itens × comandas. Ferramentas: `prefetch_related`, `annotate` e `Paginator`.
- **Três FKs sem `related_name`** (`ItemComanda.prato`, `ItemComanda.combo` e `ItemAdicional.prato`), o que obriga o acesso reverso `prato.itemcomanda_set` e `combo.itemcomanda_set`.
- **Classes CSS de etiqueta reaproveitadas** com nomes semanticamente errados (`FECHADA` para "disponível"). Deveriam ser `.positivo` e `.negativo`.
- **`ALLOWED_HOSTS` vazio.** Em desenvolvimento o sistema só responde em `localhost`; o acesso por outro aparelho da rede recebe 400.
- **A mídia só é servida com `DEBUG=True`.** O `STATIC_ROOT` está configurado e o `collectstatic` funciona, mas servir arquivos em produção é papel do servidor web, não do Django.

## Origem

O domínio foi validado previamente no **Café Teria**, um PDV em FastAPI + React desenvolvido para a disciplina de Arquitetura e Projeto de Software.

Este projeto **não reaproveita aquele código** — foi reconstruído em Django. O que atravessou foi o entendimento do domínio e o desenho de interação da tela de PDV. O que foi deliberadamente corrigido:

| Dívida do sistema anterior | Correção aqui |
|---|---|
| Itens da comanda numa string concatenada | Tabela `ItemComanda`, uma linha por item |
| Mesa como texto livre em `nome_cliente` | Entidade `Mesa` com FK |
| Sem snapshot de preço | `preco_unitario` e `total_pago` congelados |
| Pedido nascia já pago | Ciclo aberta → fechada |
| Fila da cozinha em memória (Singleton, `--workers 1`) | Consulta com `ORDER BY` |
| `if/elif` escolhendo a estratégia de pagamento | `choices` no model |
| `print()` como log | `self.stdout.write` nos comandos |
| Schema SQL aplicado à mão | Migrations versionadas |
| Regra "sempre em minúsculo" documentada em comentário | `UniqueConstraint` com `Lower()` no banco |

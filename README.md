# Comanda Digital

Sistema de atendimento para restaurantes: abertura de comandas, lançamento de pedidos em tela de PDV e fechamento de conta. Validado num contexto de cafeteria, mas o domínio é modelado de forma genérica — nada no modelo de dados assume café.

**Disciplina:** Laboratório de Programação Full Stack
**Tema:** 09 — Cardápio Digital
**Stack:** Django 5.2 · PostgreSQL 17+ · Django Templates (MPA) · CSS Proprio

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

**Regras de negócio no model.** Validações, `fechar()` e `cancelar()` vivem nos models, não nas views. Assim fechar() e cancelar() valem em qualquer contexto;  as validações de clean() só rodam em formulário.

**Integridade garantida pelo banco.** Sete `CheckConstraint` e três `UniqueConstraint` cobrem: item é prato *ou* combo, quantidade mínima 1, preços e descontos não negativos, capacidade mínima de mesa, coerência entre tipo de atendimento e mesa, e nomes únicos ignorando maiúsculas em categoria, prato e combo. `on_delete=PROTECT` impede apagar o que está em uso.

**Máquina de estados explícita.** As transições de status do item são um dicionário na view da cozinha, não uma cadeia de `if`. Não é possível voltar de "entregue" para "pendente" nem cancelar item de comanda fechada.

**Preço não é editável no lançamento.** O atendente não altera o valor de um item; o gerente altera o cardápio, e exceções viram desconto registrado no fechamento. É segregação de funções: quem define preço não é quem cobra.

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

Dois apps porque os ciclos de vida são diferentes: o cardápio muda raramente e
é gerido pelo gerente; o atendimento muda a cada minuto e é operado pelo
atendente.

## Funcionalidades

- Abertura de comanda por tipo de atendimento (mesa, viagem, balcão), com o
  tipo vindo da URL — o atendente não escolhe num select
- Múltiplas comandas simultâneas na mesma mesa
- **Tela de PDV**: grade de produtos por categoria, clique adiciona ao
  carrinho, e clicar de novo incrementa a linha existente em vez de duplicar
- Ajuste de quantidade e remoção direto no carrinho
- Edição de item (produto, quantidade, observação) pela tela da comanda
- Fechamento com forma de pagamento, taxa de serviço e desconto, com **prévia
  do total antes de confirmar**
- Cancelamento com tela de confirmação
- Painel da cozinha com fila FIFO e transições de status validadas
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

Cobre GET das telas principais e as regras de negócio centrais: snapshot de preço, fechamento sem itens, desconto acima do total, arredondamento da taxa, congelamento do `total_pago`, ocupação da mesa, comandas individuais na mesma mesa, exclusão de prato vendido e transições da cozinha.

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
| `/mesas/<id>/` | Comandas da mesa |
| `/cozinha/` | Fila de preparo |
| `/cardapio/` | Cardápio |
| `/cardapio/pratos/` | Gerenciar cardápio |
| `/admin/` | Django Admin |

## Limitações conhecidas

Levantadas em revisão de código feita antes da entrega. Estão documentadas como decisão consciente de escopo, não como omissão.

### Fora do escopo do P1, previstas para o P2

- **Não há autenticação.** Nenhuma tela exige login — apenas o `/admin/`.  Qualquer pessoa com acesso à máquina pode operar o sistema. Autenticação e  papéis (atendente, cozinha, gerente) são requisito do P2.
- **Sem tempo real.** A tela da cozinha exige recarga manual. O P2 prevê SSE.
- **Um restaurante por instalação.** Multi-restaurante é requisito do P2.
- **Sem API REST.** Prevista para o P2, com Django REST Framework.

### Decisões conscientes

- **O Admin contorna as regras do model.** O `status` da comanda é editável,   então dá para marcá-la como fechada sem passar por `fechar()`, com  `total_pago` e `fechada_em` vazios. As ações "Marcar como…" alteram o status  dos itens com `update()`, ignorando a máquina de estados e o bloqueio de  comanda fechada. No inline, o preço digitado é recapturado se o produto for trocado.
- **Exclusão física de itens.** Remover um item apaga a linha, sem histórico  de quem removeu ou quando. Auditoria exigiria soft delete e registro de  usuário, o que depende da autenticação acima.
- **Fechar a comanda tira os itens pendentes da fila da cozinha.** Em balcão e  viagem, onde o cliente costuma pagar antes do preparo, o pedido some da fila ao ser pago. A correção depende de definir a regra de negócio: ou bloquear o fechamento com itens não entregues, ou manter na fila os itens pendentes de comandas já fechadas.
- **Adicionais existem no modelo, mas não têm tela.** `ItemAdicional` é gerenciável apenas pelo Admin.
- **Itens já enviados à cozinha podem ser removidos ou editados.** O atendente consegue remover um item em preparo, pronto ou entregue, trocar o produto ou alterar a quantidade pela tela de edição — o "+/−" do PDV só funciona em item pendente, mas a edição não tem essa trava. A cozinha não é avisada. Restringir isso exige papéis (quem pode estornar), o que depende da autenticação.
- **Itens cancelados não aparecem na tela da comanda.** Saem do total e da lista; o registro só é visível no Admin.

### Limitações técnicas assumidas

- **Sem controle de concorrência.** Incrementos de quantidade usam leitura-e-escrita em Python (`quantidade += 1`) em vez de `F()`, e`fechar()` não usa `transaction.atomic()` nem `select_for_update()`. Dois terminais simultâneos podem perder um incremento ou fechar a mesma comanda duas vezes. Irrelevante com um operador; obrigatório antes de uso real.
- **`Comanda.save()` grava `codigo=''` no primeiro INSERT** antes de gerar o código a partir do `pk`. Como `codigo` é `unique`, duas criações simultâneas colidem.
- **Consultas N+1.** Os totais são propriedades que refazem a consulta a cada acesso, e as listagens não têm paginação nem filtro de data. O custo cresce com itens × comandas. Ferramentas: `prefetch_related`, `annotate` e `Paginator`.
- **Três FKs sem `related_name`** (`ItemComanda.prato`, `ItemComanda.combo` e `ItemAdicional.prato`), o que obriga o acesso reverso `prato.itemcomanda_set` e `combo.itemcomanda_set`.
- **Classes CSS de etiqueta reaproveitadas** com nomes semanticamente errados (`FECHADA` para "disponível"). Deveriam ser `.positivo` e `.negativo`.
- **`ALLOWED_HOSTS` vazio.** Em desenvolvimento o sistema só responde em `localhost`; o acesso por outro aparelho da rede recebe 400.
- **Entradas forjadas não são validadas.** Um POST montado à mão com id não numérico gera 500, e o PDV aceita lançar um adicional como item avulso.

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
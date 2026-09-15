# Comanda Digital

Sistema de atendimento para restaurantes: abertura de comandas, lançamento de
pedidos em tela de PDV e fechamento de conta. Validado num contexto de
cafeteria, mas o domínio é modelado de forma genérica — nada no código assume
café.

**Disciplina:** Laboratório de Programação Full Stack
**Tema:** 09 — Cardápio Digital
**Stack:** Django 5.2 · PostgreSQL 17 · Django Templates (MPA)

---

## A decisão central do projeto

O sistema trata as três situações reais de um salão com **uma única
abstração** — a comanda:

| Situação | Como é representado |
|---|---|
| Viagem / balcão | Comanda sem mesa (`mesa = NULL`) |
| Mesa compartilhada | Uma comanda vinculada à mesa |
| Contas individuais na mesma mesa | Várias comandas apontando para a mesma mesa |

A `ForeignKey` para `Mesa` é **opcional** e **não tem restrição de
unicidade**. É essa escolha que faz os três casos caberem numa entidade só — e
que resolve de graça o problema de dividir a conta, porque a conta nunca
esteve junta.

## Decisões técnicas

**Preço congelado (snapshot).** `ItemComanda.preco_unitario` guarda uma cópia
do preço no instante do lançamento, e `Comanda.total_pago` congela o valor no
fechamento. Reajustar o cardápio não altera comandas passadas. Trocar o
produto de um item, por outro lado, recaptura o preço — é uma operação
diferente.

**`DecimalField` para dinheiro, com arredondamento explícito.** Ponto
flutuante acumula erro de centavo. A taxa de serviço usa `ROUND_HALF_UP`
(convenção de varejo), e não o `ROUND_HALF_EVEN` que o `Decimal` aplica por
padrão. A prévia em JavaScript calcula em centavos inteiros para chegar ao
mesmo resultado.

**Estado derivado não vira campo.** `Mesa.ocupada`, `Comanda.subtotal` e
`Comanda.total` são calculados. Dado que pode ser derivado não é armazenado —
duas fontes para a mesma informação acabam divergindo.

**Regras de negócio no model.** Validações, `fechar()` e `cancelar()` vivem
nos models, não nas views. Assim valem em qualquer contexto que use o ORM.

**Integridade garantida pelo banco.** `CheckConstraint` (item é prato *ou*
combo; quantidade mínima 1), `UniqueConstraint` com `Lower()` (nomes únicos
ignorando maiúsculas) e `on_delete=PROTECT` (não apaga o que está em uso).

**Máquina de estados explícita.** As transições de status do item são um
dicionário na view da cozinha, não uma cadeia de `if`. Não é possível voltar
de "entregue" para "pendente" nem cancelar item de comanda fechada.

**Preço não é editável no lançamento.** O atendente não altera o valor de um
item; o gerente altera o cardápio, e exceções viram desconto registrado no
fechamento. É segregação de funções: quem define preço não é quem cobra.

## Modelo de dados

```
Categoria ──< Prato >──< ComboItem >── Combo
                 │                        │
                 └──────────┬─────────────┘
                            │
Mesa ──< Comanda ──< ItemComanda >── ItemAdicional
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
- CRUD completo do cardápio, com controle de disponibilidade
- Busca e filtros nas listagens

## Como rodar

```bash
git clone <url>
cd comanda_digital

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
```

Preencha o `.env` com as credenciais do PostgreSQL. **Inclua
`DEBUG=True`** — sem essa variável o padrão é `False`, e com
`ALLOWED_HOSTS = []` todas as requisições voltam `400 Bad Request`.

Crie um banco PostgreSQL vazio, com encoding **UTF8**, usando o nome que você
colocou em `DB_NAME`. Depois:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py carregar_dados    # cardápio e mesas de exemplo
python manage.py runserver
```

O `carregar_dados` é idempotente: pode ser rodado quantas vezes quiser sem
duplicar registros. Útil para restaurar o cardápio depois de testes.

## Testes

```bash
python manage.py test
```

Cobre um smoke test de todas as rotas (que teria pegado dois erros 500
encontrados em revisão) e as regras de negócio principais: snapshot de preço,
fechamento sem itens, desconto maior que a conta, arredondamento da taxa,
congelamento do `total_pago`, ocupação da mesa e comandas individuais.

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

Levantadas em revisão de código feita antes da entrega. Estão documentadas
como decisão consciente de escopo, não como omissão.

### Fora do escopo do P1, previstas para o P2

- **Não há autenticação.** Nenhuma tela exige login — apenas o `/admin/`.
  Qualquer pessoa com acesso à rede pode operar o sistema. Autenticação e
  papéis (atendente, cozinha, gerente) são requisito do P2.
- **Sem tempo real.** A tela da cozinha exige recarga manual. O P2 prevê SSE.
- **Um restaurante por instalação.** Multi-restaurante é requisito do P2.
- **Sem API REST.** Prevista para o P2, com Django REST Framework.

### Decisões conscientes

- **O Admin contorna as regras do model.** `fechar()` e `cancelar()` não são
  acionados pelo Admin, onde `status` e `total_pago` são editáveis. É
  aceitável porque o Admin é ferramenta de manutenção, não de operação — mas
  significa que ele pode produzir estados que a aplicação recusaria.
- **Exclusão física de itens.** Remover um item apaga a linha, sem histórico
  de quem removeu ou quando. Auditoria exigiria soft delete e registro de
  usuário, o que depende da autenticação acima.
- **Fechar a comanda tira os itens pendentes da fila da cozinha.** Em balcão e
  viagem, onde o cliente costuma pagar antes do preparo, o pedido some da fila
  ao ser pago. A correção depende de definir a regra de negócio: ou bloquear o
  fechamento com itens não entregues, ou manter na fila os itens pendentes de
  comandas já fechadas.
- **Adicionais existem no modelo, mas não têm tela.** `ItemAdicional` é
  gerenciável apenas pelo Admin.

### Limitações técnicas assumidas

- **Sem controle de concorrência.** Incrementos de quantidade usam
  leitura-e-escrita em Python (`quantidade += 1`) em vez de `F()`, e
  `fechar()` não usa `transaction.atomic()` nem `select_for_update()`. Dois
  terminais simultâneos podem perder um incremento ou fechar a mesma comanda
  duas vezes. Irrelevante com um operador; obrigatório antes de uso real.
- **`Comanda.save()` grava `codigo=''` no primeiro INSERT** antes de gerar o
  código a partir do `pk`. Como `codigo` é `unique`, duas criações simultâneas
  colidem.
- **Consultas N+1.** Os totais são propriedades que refazem a consulta a cada
  acesso, e as listagens não têm paginação nem filtro de data. O custo cresce
  com itens × comandas. Ferramentas: `prefetch_related`, `annotate` e
  `Paginator`.
- **Duas FKs sem `related_name`** (`ItemComanda.prato` e
  `ItemAdicional.prato`), o que obriga o acesso reverso `prato.itemcomanda_set`.
- **Sem `STATIC_ROOT`**, e a mídia só é servida com `DEBUG=True`. Configuração
  de deploy é assunto da Aula 18.
- **Classes CSS de etiqueta reaproveitadas** com nomes semanticamente errados
  (`FECHADA` para "disponível"). Deveriam ser `.positivo` e `.negativo`.

## Origem

O domínio foi validado previamente no **Café Teria**, um PDV em FastAPI +
React desenvolvido para a disciplina de Arquitetura e Projeto de Software.

Este projeto **não reaproveita aquele código** — foi reconstruído em Django.
O que atravessou foi o entendimento do domínio e o desenho de interação da
tela de PDV. O que foi deliberadamente corrigido:

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
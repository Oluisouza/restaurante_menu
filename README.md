# Comanda Digital

Sistema de atendimento para restaurantes: abertura de comandas, lançamento de pedidos e fechamento de conta. Validado num contexto de cafeteria, mas o domínio é modelado de forma genérica.

**Disciplina:** Laboratório de Programação Full Stack
**Tema:** 09 — Cardápio Digital
**Stack:** Django 5.2 · PostgreSQL 17 · Django Templates (MPA)

---

## A decisão central do projeto

O sistema trata as três situações reais de um salão com **uma única abstração**:

| Situação | Como é representado |
|---|---|
| Viagem / balcão | Comanda sem mesa (`mesa = NULL`) |
| Mesa compartilhada | Uma comanda vinculada à mesa |
| Contas individuais na mesma mesa | Várias comandas apontando para a mesma mesa |

A `ForeignKey` para `Mesa` é opcional e **não** tem restrição de unicidade. É essa escolha que faz os três casos caberem numa entidade só — e que resolve de graça o problema de dividir a conta, porque a conta nunca esteve junta.

## Decisões técnicas

**Preço congelado (snapshot).** `ItemComanda.preco_unitario` guarda uma cópia do preço no instante do lançamento, e `Comanda.total_pago` congela o valor no fechamento. Reajustar o cardápio não altera comandas passadas.

**`DecimalField` para dinheiro.** Ponto flutuante acumula erro de centavo.

**Estado derivado não vira campo.** `Mesa.ocupada`, `Comanda.subtotal` e
`Comanda.total` são calculados. Dado que pode ser derivado não é armazenado — duas fontes para a mesma informação acabam divergindo.

**Regras de negócio no model.** Validações e o método `fechar()` vivem nos models, não nas views. Assim valem no Admin, nos formulários e em qualquer código futuro.

**Integridade garantida pelo banco.** `CheckConstraint` (item é prato *ou* combo), `UniqueConstraint` com `Lower()` (nomes únicos ignorando maiúsculas) e `on_delete=PROTECT` (não apaga o que está em uso).

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

## Funcionalidades

- Abertura de comanda para mesa, viagem ou balcão
- Múltiplas comandas simultâneas na mesma mesa
- Lançamento de itens com preço automático e observação
- Edição e remoção de itens em comanda aberta
- Fechamento com forma de pagamento, taxa de serviço e desconto
- Cancelamento com confirmação
- Painel da cozinha com fila FIFO e fluxo de status
- CRUD completo do cardápio, com upload de foto e controle de disponibilidade
- Busca e filtros

## Como rodar

```bash
git clone <url>
cd comanda_digital

python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

cp .env.example .env           # e preencha os valores
```

Crie um banco PostgreSQL vazio com encoding UTF8 e o nome que você colocou em
`DB_NAME`. Depois:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py carregar_dados    # cardápio e mesas de exemplo
python manage.py runserver
```

## Rotas

| Endereço | Tela |
|---|---|
| `/` | Salão com as mesas |
| `/comandas/` | Lista com filtro por status |
| `/comandas/nova/` | Abrir comanda |
| `/comandas/<id>/` | Detalhe e totais |
| `/comandas/<id>/fechar/` | Fechamento de conta |
| `/cozinha/` | Fila de preparo |
| `/cardapio/` | Cardápio |
| `/cardapio/pratos/` | Gerenciar cardápio |
| `/admin/` | Django Admin |

## Limitações conhecidas

- **Sem autenticação por papel.** O sistema não distingue atendente, cozinha e gerente. Previsto para o P2.
- **Sem tempo real.** A tela da cozinha exige recarga manual. O P2 prevê SSE.
- **Um restaurante por instalação.** Multi-restaurante é requisito do P2.
- **Sem otimização de consultas na tela de salão.** A propriedade
  `comandas_abertas` gera uma consulta por mesa. Irrelevante com 14 mesas;
  seria um problema em escala maior. A ferramenta é `prefetch_related`.
- **Duas FKs sem `related_name`** (`ItemComanda.prato` e `ItemAdicional.prato`),
  o que obriga o acesso reverso feio `prato.itemcomanda_set`. Dívida assumida para não gerar migration perto da entrega.
- **Classes CSS de etiqueta reaproveitadas** com nomes semanticamente errados (`FECHADA` para "disponível"). Deveriam ser `.positivo` e `.negativo`.

## Origem

O domínio foi validado previamente no **Café Teria**, um PDV em FastAPI + React desenvolvido para a disciplina de Arquitetura e Projeto de Software. Este projeto **não reaproveita aquele código** — foi reconstruído em Django, com modelagem normalizada e correção de dívidas identificadas no sistema anterior (itens desnormalizados em string, mesa como texto livre, ausência de snapshot de preço e estado de negócio em memória de processo).
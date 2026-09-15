# Revisão 2 — Comanda Digital

**Commit revisado:** `05b20b9` · **Data:** 15/09/2026
**Nenhum arquivo do projeto foi alterado.** Este relatório é o único arquivo criado. Os testes de
reprodução, as mutações e as simulações rodaram a partir de uma pasta temporária, fora do repositório
(`git status` limpo ao final).

## Como foi verificado

- **Ambiente:** Python 3.11.8, Django 5.2.17 (o `pip freeze` do venv é idêntico ao `requirements.txt`),
  PostgreSQL local. O banco de teste foi criado e destruído pelo test runner.
- **Reproduzido:** executado de fato, seja com testes Django num módulo fora do projeto, `runserver` + `curl`,
  Node para o JavaScript, ou `git archive` de um commit antigo para comparar antes e depois.
- **Lido:** conclusão tirada só da leitura do código.
- **Mutação:** a regra é quebrada de propósito, em memória e num processo separado, e o teste do projeto roda de
  novo. Se ele continua passando, não protege aquela regra.
- **Consertos sugeridos:** os de C1, H2, H3 e dos testes T1 a T3 foram aplicados em memória (monkeypatch) e
  validados contra a suíte original mais os cenários deste relatório. O de H1 foi validado em Node, com DOM
  simulado. H4 e C2 não foram executados: um é uma condição no template e o outro é texto do README.

**Classes:** **CRÍTICO** (quebra o sistema) · **CORRIGIR HOJE** (uma ou duas linhas, risco baixo) ·
**DOCUMENTAR** (real, mas o conserto muda o modelo ou exige autenticação) · **P2**.

---

## Resumo e ordem sugerida para hoje

| ID | Achado | Onde | Classe | Evidência |
|---|---|---|---|---|
| **C1** | `ItemComanda.__init__` entra em recursão infinita com campos adiados; **excluir prato já vendido e excluir comanda no Admin dão 500** (regressão) | `atendimento/models.py:225-227` | CRÍTICO | Reproduzido + comparado com o commit anterior |
| **C2** | `SECRET_KEY` vazia no `.env.example` e o README não manda preencher: **todas as telas dão 500** | `.env.example:1`, `README.md:112-114` | CRÍTICO (conserto no README) | Reproduzido |
| **H1** | Prévia do total no fechamento não funciona: `recalcular()` nunca é chamada (regressão do `11f9f71`) | `fechar_comanda.html:105-106` | CORRIGIR HOJE | Reproduzido |
| **H2** | Rota `comandas/nova/<tipo>` sem barra final; a URL do README dá 404 | `atendimento/urls.py:12` | CORRIGIR HOJE | Reproduzido |
| **H3** | "+" e "−" do PDV alteram item já pronto ou entregue; a unidade extra nunca chega à cozinha | `atendimento/views.py:91-100` | CORRIGIR HOJE | Reproduzido |
| **H4** | Botão "Cancelar" aparece para item PRONTO e é sempre recusado | `cozinha.html:38` | CORRIGIR HOJE | Reproduzido |
| **R2** | `refresh_from_db()` não atualiza a referência do produto carregado, e o snapshot pode ser sobrescrito | `atendimento/models.py:227,230` | CORRIGIR HOJE (sai com C1) | Reproduzido |
| **R3** | Admin: o preço digitado em item novo no inline é descartado (regressão) | `atendimento/models.py:230-232` | CORRIGIR HOJE (sai com C1) | Reproduzido + comparado |
| **T1** | `test_preco_e_snapshot` é falso positivo | `atendimento/tests.py:85-90` | CORRIGIR HOJE | Reproduzido (mutação) |
| **T2** | `test_total_pago_congela` não testa congelamento | `atendimento/tests.py:111-115` | CORRIGIR HOJE | Reproduzido (mutação) |
| **T3** | `assertRaises(Exception)` passa com qualquer erro | `atendimento/tests.py:94,100` | CORRIGIR HOJE | Reproduzido (mutação) |
| **D1** | Remover ou editar item já em preparo, pronto ou entregue | `atendimento/views.py:101-102,179-212` | DOCUMENTAR | Reproduzido |
| **D2** | Regras do `clean()` só valem em formulário; comanda MESA sem mesa dá 500 no fechamento | `atendimento/models.py:54,84-90,123-142` | DOCUMENTAR | Reproduzido |
| **D3** | Itens cancelados somem da tela da comanda, sem rastro | `atendimento/views.py:19` | DOCUMENTAR | Reproduzido |
| **D4** | `Combo.nome` não tem unicidade, ao contrário do que o README sugere | `cardapio/models.py:62` | DOCUMENTAR | Reproduzido |
| **D5** | `ALLOWED_HOSTS = []`: acesso por outro aparelho da rede recebe 400 | `comanda_digital/settings.py:32` | DOCUMENTAR | Reproduzido |
| **D6** | Admin: o README descreve errado o que é editável, e as ações de status furam a máquina de estados | `atendimento/admin.py:19,26,44-59` | DOCUMENTAR | Reproduzido |
| P2-1…11 | Ver anexo | — | P2 | — |

**Ordem para hoje:** C1 → C2 → H1 → H2 → H3 → H4 → T1/T2/T3 → atualizar o README (seção 5).
C1 e H1 são as duas que mais pesam numa apresentação. Uma derruba a tela que ilustra o `PROTECT` e a outra
desliga uma funcionalidade listada no README.

---

## 1. Verificação das correções

| # | Correção | Aplicada? | Correta? | Efeito colateral | Evidência |
|---|---|---|---|---|---|
| 1 | Rota `nova_comanda` com `<str:tipo>` | Sim (`urls.py:12`) | Sim: `reverse` monta, os 3 tipos respondem 200 e tipo inválido dá 404 | **Ficou sem barra final** → H2 | Reproduzido |
| 2 | Remoção do `preco_unitario` órfão em `ItemComandaForm` | Sim (`forms.py:53-72`) | Sim: o campo não existe no form; GET da edição dá 200 e POST dá 302 | Nenhum | Reproduzido |
| 3 | Recaptura do preço ao trocar produto (`_produto_carregado` no `__init__`) | Sim (`models.py:225-234`) | **Só no caminho feliz.** Pela tela: reajuste A→7,00 e edição só da quantidade mantêm 6,00; troca para B grava 8,00; troca para combo grava 20,00 | **Grave:** C1 (500 em exclusões), R2 (`refresh_from_db`), R3 (Admin) | Reproduzido |
| 4 | Queryset do form inclui o produto atual mesmo indisponível | Sim (`forms.py:56-70`) | Sim: prato atual indisponível aparece e salva; outro indisponível é recusado; prato de adicionais fica fora | `.distinct()` é desnecessário (o OR na mesma tabela não duplica linhas), mas inofensivo no PostgreSQL | Reproduzido |
| 5 | `ROUND_HALF_UP` na taxa + JS em centavos | Python: sim (`models.py:111-113`). JS: fórmula sim (`fechar_comanda.html:88-90`) | Python: sim. JS: **fórmula correta, mas nunca executa** | O mesmo commit apagou os listeners → H1 | Reproduzido |
| 6 | Máquina de transições na cozinha + bloqueio em comanda fechada | Sim (`views.py:215-240`) | Sim: pular etapa, voltar, status inexistente e item de comanda fechada são recusados; o fluxo PENDENTE→EM_PREPARO→PRONTO→ENTREGUE funciona | Botão "Cancelar" oferecido para PRONTO → H4. Ações do Admin furam a regra → D6 | Reproduzido |
| 7 | `taxa_servico` removida do `FechamentoForm` quando não é mesa | Sim (`forms.py:91-92`) | Sim: POST forjado com `taxa_servico=on` numa comanda de viagem é ignorado, e `total_pago` fica 8,00 sem taxa | Nenhum relevante | Reproduzido |
| 8 | `detalhe_comanda` usando `itens_validos` | Sim (`views.py:19`) | Sim: a lista agora bate com o total | Cancelados somem sem rastro → D3 | Reproduzido |
| 9 | `Comanda.save()` sem `kwargs.pop('force_insert')` | Sim (`models.py:92-97`) | Sim: `objects.create()` (que passa `force_insert=True`), `save(force_insert=True)`, save posterior e código manual funcionam | Não repassa `using` ao segundo save (P2-9) | Reproduzido |

### Arredondamento: Python × JavaScript

Fórmula do Python: `(subtotal * 0.10).quantize(0.01, ROUND_HALF_UP)`.
Fórmula do JS: `Math.round(Math.round(subtotal*100) / 10)` centavos.

| Subtotal | Python `HALF_UP` (atual) | Python `HALF_EVEN` (antes) | JS | Batem? |
|---|---|---|---|---|
| 12,25 | **1,23** | 1,22 | **1,23** (`12.25*100 = 1225`) | Sim |
| 0,05 | **0,01** | 0,00 | **0,01** (`0.05*100 = 5`) | Sim |
| 100,45 | **10,05** | 10,04 | **10,05** (`100.45*100 = 10045`) | Sim |

A varredura de todos os subtotais de R$ 0,00 a R$ 9.999,99 (1.000.000 de valores) deu **0 divergências**.
O `data-subtotal` é renderizado como `6.00`, com ponto (via `unlocalize`), então o `parseFloat` lê certo.
**Ressalva:** hoje o JS não roda (H1). Os números batem no papel, mas o usuário não vê a prévia.

---

## 2. Regressões

### Interações do novo `ItemComanda.__init__`

| Cenário | Resultado | Evidência |
|---|---|---|
| `ItemComanda.objects.create(...)` | OK: captura o preço; preço passado explicitamente é respeitado | Reproduzido |
| `ItemComanda(comanda=..., combo=...)` + `save()` | OK | Reproduzido |
| Construtor vazio e produto atribuído depois (é o que o inline do Admin faz) | **Descarta o preço digitado** → R3 | Reproduzido |
| Inline do Admin: GET da comanda, alterar item existente | OK (39 URLs do Admin com GET 200) | Reproduzido |
| Admin: excluir comanda com itens (tela e ação em lote) | **500** → C1 | Reproduzido |
| `refresh_from_db()` sem troca de produto | OK | Reproduzido |
| `refresh_from_db()` depois de troca de produto feita por outra instância | **Snapshot sobrescrito** → R2 | Reproduzido |
| `only()` / `defer()` que deixam de fora `prato` ou `combo` | **`RecursionError`** → C1 | Reproduzido |
| `only('prato','combo',...)`, `defer('observacao')` | OK, 1 query | Reproduzido |
| `values()`, `select_related`, `prefetch_related('itens__adicionais')` | OK | Reproduzido |
| `save(update_fields=['quantidade'])` após reajuste do cardápio | OK, mantém o snapshot | Reproduzido |

### C1 — Recursão infinita com campos adiados · **CRÍTICO** · Reproduzido

**Onde:** `atendimento/models.py:225-227`

**Mecanismo.** O `__init__` lê `self.prato_id` e `self.combo_id`. Se um deles está adiado, o Django chama
`refresh_from_db(fields=[campo])`. Isso cria outro `ItemComanda` com `.only(campo)`, cujo `__init__` lê o
*outro* campo adiado, e assim sem fim.

O projeto não usa `only()`/`defer()`, mas o **coletor de exclusão do Django usa**
(`django/db/models/deletion.py:342`) para carregar objetos ligados por `PROTECT` ou por um `CASCADE` que não
dá para apagar em lote. As telas de confirmação do Admin não são afetadas, porque usam `select_related`.

**Antes × depois**, com o mesmo teste rodado sobre `git archive 5d5d639` (commit anterior à correção) e sobre o HEAD:

| Ação | `5d5d639` | HEAD |
|---|---|---|
| POST em `/cardapio/pratos/<id>/excluir/` de prato já vendido | 200 + "não pode ser excluído…" | **500** |
| Admin → excluir comanda com itens (confirmar) | 302 | **500** |
| Admin → "Remover selecionados" em comandas | — | **500** |
| `Combo.delete()` de combo vendido (ORM) | `ProtectedError` | **`RecursionError`** |
| Preço digitado em item novo no inline do Admin | grava 1,00 | grava 6,00 (R3) |

Continuam funcionando: excluir item (tela e "×" no PDV), excluir prato sem uso ou usado só em combo, e as
telas de confirmação do Admin (em que o prato protegido é recusado corretamente).

**Conserto:** trocar `__init__` por `from_db`, o padrão documentado pelo Django para rastrear valores
carregados. Não precisa de migração. Validado em memória: os 11 testes originais e os 9 cenários (exclusões, `only`/`defer`,
recaptura pela tela, R2, R3, `create`) passaram. Resolve também **R2** e o caso de item novo de **R3**.

```python
    # apagar o __init__ e usar:
    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if 'prato_id' in field_names and 'combo_id' in field_names:
            instance._produto_carregado = (instance.prato_id, instance.combo_id)
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using, fields, from_queryset)
        self._produto_carregado = (self.prato_id, self.combo_id)

    def save(self, *args, **kwargs):
        carregado = getattr(self, '_produto_carregado', None)
        produto_mudou = carregado is not None and (self.prato_id, self.combo_id) != carregado
        if self.produto and (self.preco_unitario is None or produto_mudou):
            self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)
        self._produto_carregado = (self.prato_id, self.combo_id)
```

### R2 — `refresh_from_db()` deixa a referência desatualizada · **CORRIGIR HOJE (sai com C1)** · Reproduzido

**Onde:** `atendimento/models.py:227,230`

**Cenário:**
1. O item é carregado com o prato A.
2. Outra instância troca para B (8,00) e salva.
3. O cardápio reajusta B para 99,00.
4. `item.refresh_from_db()` → `prato_id` passa a ser B, mas a referência continua sendo A.
5. `item.observacao = 'x'; item.save()` → `preco_unitario` vira **99,00**.

Hoje nenhuma view chama `refresh_from_db` em item, então isso não aparece na tela. Aparece em shell, em
testes e em código futuro.

### R3 — Admin descarta o preço digitado · **CORRIGIR HOJE (item novo, sai com C1)** / **DOCUMENTAR (troca de produto)** · Reproduzido

**Onde:** `atendimento/models.py:230-232`, `atendimento/admin.py:19`

A instância nova nasce com referência `(None, None)`. O form do inline atribui o prato, o `save` conclui que o
produto mudou e recaptura o preço. Em `5d5d639` o valor digitado era gravado. Com o conserto de C1, o caso
de item novo volta a respeitar o valor digitado (validado).

Trocar o produto de um item *existente* no Admin continua recapturando o preço, o que é coerente com
`README.md:34-36`. Só que o campo `preco_unitario` segue editável no inline, sem aviso de que será ignorado.

### H1 — Prévia do total morta · **CORRIGIR HOJE** · Reproduzido

**Onde:** `atendimento/templates/atendimento/fechar_comanda.html:105-106`

- **Causa:** o commit `11f9f71` ("alinha prévia do total") apagou os dois `addEventListener` e a chamada
  inicial `recalcular()`. No HTML servido, `recalcular` aparece só na definição.
- **Simulação em Node do script servido** (DOM simulado): marcar a taxa e digitar desconto não muda nada.
  Com as 3 linhas de volta:

  | Cenário | Taxa | Total |
  |---|---|---|
  | 12,25 com taxa | R$ 1,23 | R$ 13,48 |
  | 100,45 com taxa e desconto 5,45 | R$ 10,05 | R$ 105,05 |
  | Viagem (sem campo de taxa), desconto 1 | R$ 0,00 | R$ 7,00 |

- **Sintomas visíveis hoje:**
  - **(a)** Comanda de mesa aberta com taxa: "Total a cobrar" já soma a taxa, mas a linha da taxa fica
    `display:none`. Reproduzido: total R$ 6,60 sem a linha da taxa.
  - **(b)** Desconto recusado (ex.: 999): a página volta mostrando **"Total a cobrar R$ -993,00"**, porque o
    form já aplicou o desconto na instância em memória (`views.py:142-144`).
- **Impacto:** `README.md:89-90` anuncia a "prévia do total antes de confirmar".
- **Conserto:** colar antes de `})();`. Com isso, (b) passa a mostrar R$ 0,00 junto da mensagem de erro.

```js
    if (campoTaxa) campoTaxa.addEventListener('change', recalcular);
    if (campoDesconto) campoDesconto.addEventListener('input', recalcular);
    recalcular();
```

Confira no navegador antes de apresentar. Nenhum teste Django cobre JavaScript.

---

## 3. Erros que impedem o uso

**Comandos:**
- `manage.py check` → *System check identified no issues*.
- `manage.py makemigrations --check --dry-run` → *No changes detected* (exit 0).
- `check --deploy` → 7 avisos esperados em desenvolvimento (HSTS, SSL, `DEBUG`, `ALLOWED_HOSTS`, chave
  `django-insecure-`). Não bloqueiam o P1.

**Smoke test (Reproduzido):**
- **Aplicação:** 44 GETs. Inclui as 3 aberturas por tipo, `?mesa=` válido e inválido, comandas aberta,
  fechada, cancelada e sem itens (detalhe, PDV, fechar e cancelar de cada uma), editar e excluir item de
  comanda aberta e fechada, mesa com e sem comandas, cardápio com busca, e novo, editar e excluir prato.
  **Nenhum status ≥ 400 e nenhum `NoReverseMatch`.** IDs inexistentes dão 404.
- **Admin:** 39 GETs, logado como superusuário (índice, listagens, adicionar, editar, excluir e histórico de
  todos os models, mais o filtro de data). **Todos 200.**

**Erros encontrados:**

| Tela / ação | Status | Causa | ID | Evidência |
|---|---|---|---|---|
| Qualquer tela, com `SECRET_KEY` vazia como no `.env.example` | **500** | `ImproperlyConfigured: The SECRET_KEY setting must not be empty`, disparado pelo storage de mensagens em toda requisição | C2 | Reproduzido |
| POST "Sim, excluir" em prato já vendido | **500** | `RecursionError` | C1 | Reproduzido |
| Admin: excluir comanda com itens (individual ou em lote) | **500** | `RecursionError` | C1 | Reproduzido |
| `/comandas/nova/mesa/` (URL do README) | **404** | rota sem `/` final | H2 | Reproduzido (`runserver` + `curl`) |
| Qualquer tela acessada por IP da rede (ex.: `Host: 192.168.0.10`) | **400** | `ALLOWED_HOSTS = []` (com `DEBUG=True` só `localhost`/`127.0.0.1`) | D5 | Reproduzido (`runserver` + `curl`) |
| Fechar comanda tipo MESA sem mesa (estado criado via ORM) | **500** | `ValueError: 'FechamentoForm' has no field named 'mesa'` | D2 | Reproduzido |
| POST forjado com id não numérico (cozinha, PDV) | **500** | `ValueError` no `get_object_or_404` | P2-1 | Reproduzido |

### C2 — `SECRET_KEY` vazia · **CRÍTICO** (conserto no README, sem risco) · Reproduzido

**Onde:** `.env.example:1`, `README.md:112-114`, `comanda_digital/settings.py:27`

O `.env.example` traz `SECRET_KEY =` vazio, e o README só manda preencher as credenciais do PostgreSQL e o
`DEBUG`. Quem seguir o README ao pé da letra passa no `check` e no `migrate`, mas recebe 500 em todas as telas.

**Conserto:** acrescentar ao passo do `.env`:
`python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`
e colar a saída em `SECRET_KEY`.

### H2 — Rota sem barra final · **CORRIGIR HOJE** · Reproduzido

**Onde:** `atendimento/urls.py:12`

Trocar para `'comandas/nova/<str:tipo>/'`. Os links usam `{% url %}` e se ajustam sozinhos.

Validado com urlconf corrigida: `/comandas/nova/mesa/` → 200, sem barra → 301 (`APPEND_SLASH`), salão → 200.

### H3 — "+" e "−" do PDV em item fora da fila · **CORRIGIR HOJE** · Reproduzido

**Onde:** `atendimento/views.py:91-100` (botões em `pdv.html:62-64`)

**Cenário:** item ENTREGUE + clique em "+" → quantidade 2, status continua ENTREGUE, o item não aparece na
cozinha. A unidade extra é cobrada e nunca preparada. Em PRONTO, a cozinha vê "Pronto" com a quantidade
maior. Em CANCELADO (POST forjado), a quantidade muda num item invisível.

A regra já existe no clique do cardápio (`views.py:81` só mescla em PENDENTE), mas não no "+".

**Conserto** (validado): logo após o `get_object_or_404` de `_ajustar_item`:

```python
    if acao != 'remover' and item.status != ItemComanda.Status.PENDENTE:
        messages.error(request, 'Este item já foi para a cozinha. Lance o produto de novo.')
        return
```

A remoção ficou de fora de propósito (ver D1).

### H4 — "Cancelar" para item PRONTO · **CORRIGIR HOJE** · Reproduzido

**Onde:** `atendimento/templates/atendimento/cozinha.html:38`

O HTML mostra `value="CANCELADO"` para item PRONTO, e o POST responde "Essa mudança de status não é
permitida" (`views.py:218`). Envolver o botão em `{% if item.status != 'PRONTO' %}…{% endif %}`.

---

## 4. Cobertura dos testes

**Resultado:** `manage.py test` → **11 testes, OK** (PostgreSQL).

| Teste | Nome promete | O que verifica de fato | Mutação | Veredito |
|---|---|---|---|---|
| `RotasTest.test_telas_sem_parametro` | telas sem parâmetro | GET 200 em 6 rotas | — | Válido |
| `RotasTest.test_abertura_por_tipo` | abertura por tipo | GET 200 nos 3 tipos | — | Válido (só GET) |
| `RotasTest.test_telas_da_comanda` | telas da comanda | GET 200, só com comanda aberta | — | Válido, estreito |
| `RotasTest.test_telas_do_item` | telas do item | GET 200 | — | Válido |
| **`RegrasTest.test_preco_e_snapshot`** | snapshot de preço | Reajusta `self.prato` ("Espresso"), mas `_comanda_com_item` cria o item com **outro** prato ("Item 6.00-1"). O item nunca é salvo de novo | snapshot desligado → **passa**; total calculado com `prato.preco` → **passa** | **FALSO POSITIVO** (T1) |
| **`RegrasTest.test_nao_fecha_sem_itens`** | não fecha sem itens | `assertRaises(Exception)` | `fechar()` lançando `AttributeError` qualquer → **passa** | **Passa pelo motivo errado** (T3) |
| **`RegrasTest.test_desconto_maior_que_conta`** | desconto > conta | idem | sem a checagem → falha ✔; `AttributeError` → **passa** | Pega a regra, mas também passa por motivo errado (T3) |
| `RegrasTest.test_taxa_arredonda_para_cima` | "para cima" | 3 casos que separam HALF_UP de HALF_EVEN ✔ | `ROUND_CEILING` → **passa** | Válido para o nome, mas não prova *HALF_UP* como diz o README. Falta um caso abaixo da metade (12,24 → 1,22) |
| **`RegrasTest.test_total_pago_congela`** | congelamento do `total_pago` | Só confere o objeto em memória logo após `fechar()` | `fechar()` sem `save()` → **passa** | **FALSO POSITIVO** para "congela" (T2) |
| `RegrasTest.test_mesa_ocupada_enquanto_houver_comanda` | ocupação | ✔ | `ocupada` ignorando status → falha ✔ | Válido |
| `RegrasTest.test_comandas_individuais_na_mesma_mesa` | várias comandas por mesa | ✔ (via ORM) | bloquear a 2ª comanda → falha ✔ | Válido |

`README.md:135` diz "smoke test de todas as rotas". **Não é verdade:** faltam `detalhe_mesa`, `editar_prato`
e `excluir_prato`, e nenhum teste faz POST. Por isso C1 passou.

### T1 / T2 / T3 — Testes substitutos · **CORRIGIR HOJE** · Reproduzido

Estas versões passam no HEAD e **falham** com cada mutação acima. `test_preco_e_snapshot` foi validado contra
"save sempre recaptura" e "total usa `prato.preco`". `test_total_pago_congela` foi validado contra "fechar sem
save". `test_nao_fecha_sem_itens` foi validado contra "AttributeError".

```python
from django.core.exceptions import ValidationError   # no topo

    def test_preco_e_snapshot(self):
        comanda = self._comanda_com_item('6.00')
        item = comanda.itens.get()
        item.prato.preco = Decimal('99.00')
        item.prato.save()
        item.quantidade = 2
        item.save()                      # é aqui que o snapshot poderia quebrar
        item.refresh_from_db()
        self.assertEqual(item.preco_unitario, Decimal('6.00'))
        self.assertEqual(comanda.subtotal, Decimal('12.00'))

    def test_total_pago_congela(self):
        comanda = self._comanda_com_item('10.00')
        comanda.fechar(Comanda.FormaPagamento.PIX)
        item = comanda.itens.get()
        item.prato.preco = Decimal('50.00')
        item.prato.save()
        ItemComanda.objects.create(comanda=comanda, prato=item.prato)
        comanda.refresh_from_db()
        self.assertEqual(comanda.status, Comanda.Status.FECHADA)
        self.assertEqual(comanda.total_pago, Decimal('10.00'))

    # e nos dois testes de exceção: self.assertRaises(ValidationError)
```

### Regras importantes sem teste, por prioridade

1. **POST de exclusão de prato já vendido mostra a mensagem.** Teria pegado C1.
2. **Transições da cozinha:** permitidas, proibidas e item de comanda fechada. A correção 6 não tem teste.
3. **Recaptura ao trocar produto pela tela de edição** e manutenção do preço ao editar só a quantidade. A
   correção 3 não tem teste.
4. **Bloqueios em comanda encerrada:** lançar, editar e excluir item, fechar de novo, cancelar comanda fechada.
5. **PDV:** clicar de novo incrementa a linha PENDENTE; não mescla com item em preparo nem com observação;
   "+" em item fora da fila (H3).
6. **Totais:** item cancelado fora do subtotal; adicionais somados ao total.
7. **Abertura pela tela (POST):** mesa obrigatória no tipo mesa, mesa inativa recusada, mesa ignorada em
   viagem, código `CMDxxxxx` gerado.
8. **`FechamentoForm` sem taxa em viagem/balcão.** A correção 7 não tem teste.
9. **Smoke:** incluir `detalhe_mesa`, `editar_prato`, `excluir_prato` e as telas com comanda fechada ou cancelada.
10. **Prévia em JS:** não dá para testar com `TestCase`. Verificação manual no navegador.

---

## 5. Lacunas na documentação

### 5.1 Problemas reais que não estão em "Limitações conhecidas"

C1, C2, H1 a H4 e T1 a T3 **não são defensáveis como limitação**: o conserto é curto e já está validado.
Se algum ficar para depois, precisa entrar na lista. Os abaixo são os que cabem como limitação:

**D1 — Item já preparado pode ser removido ou editado** · Reproduzido
`views.py:101-102` ("×" no PDV), `179-196` (`editar_item`), `198-212` (`excluir_item`).
- "×" apaga item EM_PREPARO.
- Editar item ENTREGUE troca o produto e recaptura o preço, mas o status continua ENTREGUE e a cozinha
  nunca preparou o novo produto.
- `/itens/<id>/editar/` aceita item CANCELADO (302).
- O item "Exclusão física" do README fala só de histórico. Quem pode estornar item entregue é regra de papel,
  e depende da autenticação.

**D2 — Regras do `clean()` não valem fora de formulário** · Reproduzido
`models.py:84-90` (`clean`), `123-142` (`fechar` não chama `full_clean`), `54` (tipo padrão = MESA).
- `comanda.desconto = -5; comanda.fechar('PIX')` fecha com `total_pago` 13,00 sobre um subtotal de 8,00.
- `Comanda.objects.create(responsavel='x')` cria comanda MESA sem mesa. Fechar pela tela dá 500
  (`ValueError: 'FechamentoForm' has no field named 'mesa'`).
- Nenhuma tela produz esses estados, só ORM, shell ou script de carga. Conserto: `CheckConstraint`, que
  exige migração.

**D3 — Itens cancelados somem da tela da comanda** · Reproduzido
`views.py:19`, `detalhe_comanda.html:30-52`.
- É efeito colateral da correção 8. Não há onde ver o que a cozinha cancelou, exceto no Admin.
- Com todos os itens cancelados, a tela diz "Nenhum item lançado ainda".

**D4 — `Combo.nome` sem unicidade** · Reproduzido
`cardapio/models.py:62`. "Combo X" e "combo x" coexistem. Categoria e Prato têm a constraint.

**D5 — Acesso pela rede dá 400** · Reproduzido
`settings.py:32`. Se a apresentação usar celular ou tablet, é preciso `ALLOWED_HOSTS` + `runserver 0.0.0.0:8000`.
Nesse caso vira *corrigir hoje*.

**D6 — Admin fura a máquina de estados** · Reproduzido
`admin.py:19,26,44-59`.
- Mudar o status da comanda para FECHADA pelo Admin grava com `total_pago`, `fechada_em` e forma de pagamento
  vazios.
- A ação "Marcar como em preparo" levou um item ENTREGUE de comanda FECHADA de volta para EM_PREPARO.

**R3 (troca de produto) — Admin mostra preço editável que é ignorado** · Reproduzido
`models.py:230-232`, `admin.py:19`.

**P2-1 / P2-2 — Entrada forjada não é validada** · Reproduzido
`views.py:72,75,92,224`. Id não numérico dá 500. O PDV aceita prato da categoria de adicionais por POST
direto.

### 5.2 Afirmações do README que hoje não se sustentam

Estas são as que mais podem ser questionadas na apresentação:

| Linha | O README diz | Realidade |
|---|---|---|
| `README.md:48-49` | Regras no model "valem em qualquer contexto que use o ORM" | Vale para `fechar()`/`cancelar()`. As validações do `clean()` só rodam em formulário (D2) |
| `README.md:51-53` | `UniqueConstraint` com `Lower()`: "nomes únicos ignorando maiúsculas" | Só em Categoria e Prato; Combo não tem (D4). Tipo × mesa e desconto ≥ 0 não estão no banco (D2) |
| `README.md:55-57` | "Não é possível voltar de entregue para pendente nem cancelar item de comanda fechada" | Verdade na tela da cozinha; as ações do Admin fazem as duas coisas (D6) |
| `README.md:89-90` | "prévia do total antes de confirmar" | Não funciona hoje (H1) |
| `README.md:112-114` | Preencher credenciais e `DEBUG` basta | Sem `SECRET_KEY`, tudo dá 500 (C2) |
| `README.md:135-138` | "smoke test de todas as rotas"; cobre "snapshot de preço" e "congelamento do `total_pago`" | Faltam 3 rotas e nenhum POST; os testes de snapshot e congelamento são falsos positivos (T1, T2) |
| `README.md:146` | `/comandas/nova/<tipo>/` | Com barra final dá 404 (H2) |
| `README.md:165-166` | "Qualquer pessoa com acesso à rede pode operar o sistema" | Com `ALLOWED_HOSTS = []`, só `localhost` (D5). O ponto (sem autenticação) continua válido; o exemplo não |
| `README.md:174-177` | No Admin "`status` e `total_pago` são editáveis" | `total_pago` é **somente leitura** (`admin.py:26`). O problema real é `status` editável gerar comanda FECHADA sem `total_pago` (D6) |

### 5.3 Texto sugerido para acrescentar em "Limitações conhecidas"

Pressupõe C1, C2, H1 a H4 e T1 a T3 corrigidos.

**Em "Decisões conscientes":**

- **Itens já enviados à cozinha podem ser removidos ou editados.** O atendente consegue remover um item em
  preparo ou entregue, ou trocar o produto dele, sem que a cozinha seja avisada. Restringir isso exige
  papéis (quem pode estornar), o que depende da autenticação.
- **Itens cancelados não aparecem na tela da comanda.** Saem do total e da lista; o registro só é visível no
  Admin.

**Em "Limitações técnicas assumidas":**

- **Validações de `clean()` só rodam em formulários.** Desconto negativo e comanda de mesa sem mesa são
  recusados pelas telas, mas não pelo ORM nem pelo banco. Via shell é possível criar esses estados, e uma
  comanda de mesa sem mesa quebra a tela de fechamento. A garantia real exige `CheckConstraint`.
- **Nome de combo não é único.** A unicidade ignorando maiúsculas existe só em categoria e prato.
- **`ALLOWED_HOSTS` vazio.** Em desenvolvimento o sistema só responde em `localhost`; o acesso por outro
  aparelho da rede recebe 400.
- **Entradas forjadas não são validadas.** Um POST montado à mão com id não numérico gera 500, e o PDV
  aceita lançar um adicional como item avulso.

**Substituir o texto atual do Admin por:**

- **O Admin contorna as regras do model.** O `status` da comanda é editável, então dá para marcá-la como
  fechada sem passar por `fechar()`, com `total_pago` e `fechada_em` vazios. As ações "Marcar como…" alteram
  o status dos itens com `update()`, ignorando a máquina de estados e o bloqueio de comanda fechada. O preço
  digitado no inline é recapturado se o produto for trocado.

---

## Anexo — P2

| ID | Achado | Onde | Evidência |
|---|---|---|---|
| P2-1 | POST forjado com id não numérico dá 500 (`item=abc` na cozinha, `prato=abc` e `item=abc` no PDV) | `atendimento/views.py:72,75,92,224` | Reproduzido |
| P2-2 | PDV aceita prato de categoria de adicionais via POST forjado (o form de edição filtra; o PDV não) | `atendimento/views.py:72` | Reproduzido |
| P2-3 | Erro duplicado ao escolher prato e combo juntos na edição: "Informe exatamente um…" + "Restrição "item_prato_ou_combo" foi violada." | `atendimento/models.py:189-195,221-223` | Reproduzido |
| P2-4 | Tela de cancelamento abre (GET 200) para comanda já fechada ou cancelada e diz "Esta ação não pode ser desfeita"; só o POST recusa | `atendimento/views.py:165-177` | Reproduzido |
| P2-5 | Mesa desativada com comanda aberta some do salão (mesas filtram `ativa=True`, e as avulsas são só as sem mesa) | `atendimento/views.py:12-13` | Lido |
| P2-6 | Busca do cardápio mantém títulos de categorias sem resultado | `cardapio/templates/cardapio/lista_cardapio.html:13-28` | Lido |
| P2-7 | Mensagens: "…combos. marque como indisponível. " (minúscula e espaço sobrando); "fechada - R$ 12.25" com ponto decimal, destoando da vírgula no resto da interface | `cardapio/views.py:54-55`, `atendimento/views.py:150` | Lido |
| P2-8 | Combo continua à venda se um prato componente ficar indisponível | `atendimento/views.py:75`, `cardapio/models.py:61-82` | Lido |
| P2-9 | `Comanda.save()` não repassa `using` ao segundo save (só importa com vários bancos) | `atendimento/models.py:97` | Lido |
| P2-10 | Comanda criada com `pk` explícito fica com `codigo=''`; a segunda colide no `unique` (variante do item já documentado) | `atendimento/models.py:93-95` | Reproduzido (`IntegrityError`) |
| P2-11 | `.distinct()` desnecessário nos querysets do form de item | `atendimento/forms.py:61,70` | Lido |

# Melhorias da P1

Revisão do MVP entregue na P1, feita antes de iniciar a P2.

O critério de escolha foi o da Aula 13: **tudo que a API expuser é o que o model já faz**. Na P1, várias regras de negócio vivem nas views. A API do DRF fala com o model por meio do serializer, sem passar por essas views, então cada regra que só a view garante é uma regra que a API vai ignorar. Por isso os itens abaixo priorizam o que a P2 herdaria de frágil.

Um agravante: o `ModelSerializer` do DRF não chama o `clean()` do model. Para a API, a última linha de defesa são as constraints do banco, que protegem o dado mas respondem com erro 500 em vez de um 400 com mensagem.

---

## 1. Cancelar item pela cozinha gera erro 500

**Tipo:** bug

**Situação atual.** A view `cozinha` cancela um item gravando `status = CANCELADO` diretamente. Desde a migration `0008`, a constraint `item_cancelado_tem_motivo` exige motivo para todo item cancelado, então o banco recusa a gravação e a tela devolve erro 500.

**Por que os testes não pegaram.** O único teste que envia `CANCELADO` para a cozinha usa um item de comanda já fechada, que é barrado antes de chegar ao `save()`. O caminho normal, cancelar item de comanda aberta, nunca foi exercitado.

**Correção.**
- A cozinha passa a cancelar por `item.cancelar('Cancelado pela cozinha')`.
- Concluir as telas de cancelamento de item com motivo, cujo model já estava pronto:
  - tela de cancelamento com campo de motivo;
  - item cancelado aparece riscado na comanda, com o motivo.
- Teste novo cancelando pela cozinha um item de comanda aberta.

---

## 2. Regras de negócio que só existem nas views

**Tipo:** dívida técnica (pré-requisito da API)

**Situação atual.**

| Regra | Onde está hoje |
|---|---|
| Transições de status do item (máquina de estados) | Dicionário `TRANSICOES` dentro da view `cozinha` |
| Só item pendente pode ser editado ou removido | Repetida em `_ajustar_item`, `editar_item` e `excluir_item`, e furada na ação `remover` do PDV, que apaga item em qualquer status |
| Adicional não pode ser lançado como item avulso | Filtro em `_adicionar_produto` |
| Produto indisponível não pode ser lançado | Verificação em `_adicionar_produto` |

Na prática, hoje o atendente consegue apagar sem deixar rastro um item que já foi entregue. Na P2, qualquer endpoint da API contornaria todas essas regras.

**Correção.**
- Levar as regras para o model, em métodos como `ItemComanda.mudar_status(novo_status)` e `ItemComanda.remover()`.
- As views da P1 e as views da API passam a chamar esses métodos, e cada regra fica com um lugar só.
- O item 1 é resolvido como consequência: cancelar vira uma transição da máquina de estados, que exige motivo.

---

## 3. A regra "preço maior que zero" só existe no formulário

**Tipo:** dívida técnica (regra duplicada e divergente)

**Situação atual.**
- A regra entrou na P1 (validação customizada do sorteio) e está apenas no `PratoForm.clean_preco`.
- O banco tem a constraint `prato_preco_nao_negativo`, que aceita `preco >= 0`.
- Hoje a tela recusa preço zero, mas Admin, shell e a futura API aceitam.

**Correção.**
- Ajustar a constraint para `preco > 0`, tornando o banco o lugar principal da regra.
- O formulário continua exibindo a mensagem amigável.
- Avaliar se a mesma regra vale para `Combo`.

---

## 4. Unicidade global incompatível com várias organizações

**Tipo:** modelagem

**Situação atual.** São únicos no sistema inteiro:
- `Mesa.identificacao`;
- os nomes de `Categoria`, `Prato` e `Combo` (constraints `*_nome_unico_ci`);
- `Comanda.codigo`.

Com duas organizações na mesma base, só uma delas poderia ter a "Mesa 01" ou o "Café expresso".

**Correção** (junto com o model `Organizacao`, na Aula 14).
- As regras de unicidade passam a valer **dentro da organização**, com `UniqueConstraint` incluindo o campo `organizacao`.
- Definir se o código da comanda reinicia por organização.

---

## 5. Sem controle de concorrência

**Tipo:** dívida técnica

**Situação atual.**
- Incrementos de quantidade usam leitura e escrita em Python (`quantidade += 1`): dois acessos simultâneos perdem um incremento.
- `Comanda.fechar()` não usa transação nem trava de registro: a mesma comanda pode ser fechada duas vezes.
- `Comanda.save()` grava `codigo = ''` no primeiro INSERT, antes de gerar o código a partir do `pk`. Como o campo é único, duas criações simultâneas colidem.

Com um único operador isso era teórico. Com uma API aberta a vários clientes, passa a ser real.

**Correção.**
- Incrementos com `F('quantidade') + 1`.
- `fechar()` dentro de `transaction.atomic()`, com `select_for_update()` na comanda.
- Geração do código sem passar por um valor vazio repetido.

---

## Fora desta lista, com momento definido

| Ponto | Quando será tratado |
|---|---|
| Consultas N+1 e falta de paginação | Aulas 16 e 17: paginação do DRF e agregações do dashboard |
| FKs sem `related_name` e classes CSS com nome semanticamente errado | De passagem, ao alterar esses arquivos |
| `ALLOWED_HOSTS` vazio | Aula 19, implantação |
| Ausência de autenticação e papéis | É um dos pilares da própria P2 (Aula 15) |


---

## Situação na entrega da P2

| Item | Situação | Commits |
|---|---|---|
| 1. Cancelar item pela cozinha gera erro 500 | Resolvido. A cozinha cancela pela máquina de estados do model, que exige motivo. Tela de cancelamento com motivo, e o item cancelado aparece riscado na comanda. | `15fd5a2`, `f2b49f5` |
| 2. Regras de negócio que só existem nas views | Resolvido. `mudar_status`, `exigir_alteravel`, `remover` e `lancar` vivem no model e são usados pelas views, pela API e pelo Admin. | `15fd5a2`, `b8d43c5`, `7d12ac1` |
| 3. Preço maior que zero só no formulário | Resolvido. A constraint do banco passou a exigir `preco > 0`. | `7a44d09` |
| 4. Unicidade global | Resolvido. Nomes únicos por restaurante, ignorando maiúsculas. | `766a30b` |
| 5. Sem controle de concorrência | Em aberto. Registrado nas limitações do README. | |

| Ponto fora da lista | Situação |
|---|---|
| Consultas N+1 | Resolvido na lista de comandas e no salão, e travado com `assertNumQueries` (`cf8931e`). A paginação continua em aberto. |
| Classes CSS com nome errado | Resolvido no novo visual (`8ffc1f3`): as etiquetas usam o próprio status como classe. |
| FKs sem `related_name` | Em aberto. |
| `ALLOWED_HOSTS` vazio | Em aberto, fica para a implantação. |
| Ausência de autenticação e papéis | Resolvido: login obrigatório (`85547ae`) e papéis de gerente e atendente (`eab6543`, `b504bfb`, `9be1ff6`). |
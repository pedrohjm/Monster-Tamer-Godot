# Monster Tamer

RPG 2D top-down de criaturas em mundo aberto contínuo: o jogador explora como treinador e assume o controle direto da criatura para lutar em tempo real no próprio mapa.

**Fonte da verdade do design: [docs/GAME_DESIGN.md](docs/GAME_DESIGN.md).** Ler a seção relevante antes de implementar qualquer sistema. Se uma decisão de design mudar, atualizar o documento **antes** do código.

**Engine: Godot 4.7 (versão padrão, sem .NET), renderer Compatibility, GDScript.** O design original foi escrito para Unity e foi portado em 2026-11-04 (GAME_DESIGN §8 e §9). Quando um termo antigo aparecer, a equivalência é: ScriptableObject → `Resource` (.tres); MonoBehaviour → nó-componente; C# puro → `RefCounted`; Input System → Input Map; Cinemachine → `CameraRig` (Camera2D); Pixel Perfect Camera → stretch `viewport` + escala inteira; asmdef → regra de dependência entre pastas; testes EditMode → `tests/unit` no runner headless.

## Regras inegociáveis (resumo do GAME_DESIGN)

- **Propriedade intelectual:** nada de nomes, sprites, sons, tipos ou criaturas da franquia Pokémon. Tudo original. Asset de terceiros só com licença compatível (CC0, CC-BY, comprado), registrado em `art/CREDITS.md`.
- **Arquitetura:** dados em `Resource` (`class_name ... extends Resource`, arquivos `.tres` em `data/`); lógica pura (dano, captura, XP, elementos) em classes `extends RefCounted`, sem `Node`, testáveis em `tests/unit`. Composição sobre herança (nós-componente filhos; herança no máximo um nível). Criatura do jogador e selvagem usam a mesma cena e trocam só o `Brain` (`PlayerBrain`, `WildAIBrain`, `FollowBrain`, `DefensiveBrain`) via `BrainController`. UI/áudio/câmera escutam sinais. Autoloads permitidos: só `EventBus` (sinais, sem estado) e, quando precisar, `GameServices`.
- **Dependência entre pastas** (no lugar de asmdefs): `core` ← `data` ← `combat` ← `creatures` ← `trainer`/`world`; `ui` pode ler tudo e ninguém lê `ui`. Detalhe em GAME_DESIGN §9.3.
- **GDScript tipado:** tipar variáveis, parâmetros e retornos.
- **Input:** só ações do Input Map (`Input.get_vector`, `is_action_*`, `event.is_action(...)`). Nunca `Input.is_key_pressed`, `is_physical_key_pressed` ou keycodes no código. PC (teclado + mouse).
- **Pixel art:** tile 32×32; 1 tile = 32 px, sempre via `Units.TILE` / `Units.tiles(n)` (nunca o número 32 solto). Filtro Nearest, importação Lossless, pivô nos pés (tiles: centro). Resolução 640×360, stretch `viewport` com escala inteira, snap 2D em pixel. Ordenação por Y com `y_sort_enabled`.
- **Roadmap:** milestones M0 a M9 (GAME_DESIGN §10). Cada uma termina jogável; não avançar sem fechar a anterior.

## Status do roadmap

> **Projeto reiniciado do zero, agora em Godot.** As "decisões herdadas" abaixo vieram da versão anterior (Unity) e continuam valendo como direção; reavaliar no playtest de cada milestone.

- [x] **M0 Setup** (2026-11-04): Godot 4.7 Compatibility, resolução 640×360 com stretch `viewport` + escala inteira e snap em pixel, filtro Nearest, Input Map, `CameraRig`, autoload `EventBus`, `Units`, pastas, runner de testes headless, CLAUDE.md, git + LFS, graphify.
  - Decisão herdada: renderização em baixa resolução ampliada em múltiplos inteiros (equivalente ao "Upscale Render Texture" da Unity). Sem isso apareciam linhas finas entre os tiles.
- [ ] **M1 Treinador no mundo**: mapa de teste com `TileMapLayer`, colisão (água e props), ordenação por Y, treinador em camadas com animação em 8 direções, limites do mapa e limites da `CameraRig`.
- [ ] **M2 Criatura seguindo**: `Brain`/`BrainController`, `FollowBrain`, soltar (toque em Q) e recolher (segurar Q).
  - Decisão herdada: no M2 o toque em Q só solta a criatura e o controle continua no treinador; no M3 o toque passa a transferir o controle (GAME_DESIGN §4.2).
- [ ] **M3 Troca de controle**: `PlayerBrain` no treinador e na criatura, Q alterna o controle, câmera troca de alvo, coleira de 10 tiles com linha.
  - Decisões herdadas: com o controle de volta no treinador, fora de combate a criatura volta a segui-lo (`FollowBrain`); a IA "só defensiva" do §4.3 entra junto com o combate (M4). Durante a canalização do recolhimento, treinador e criatura ficam parados.
- [ ] **M4 Combate mínimo**: `Health` + `DamageCalculator` (§5.4), `MoveCaster` com cooldown e telegrafo, 2 golpes (um projétil e um cone), `WildAIBrain` por temperamento, `DefensiveBrain`, desmaio e barra de HP.
  - Decisões herdadas: sem elemento ainda (multiplicador 1; `ElementChart` no M6); a selvagem só mira a criatura do jogador (corações do treinador no M5); criatura do jogador desmaiada volta à esfera e revive em 10 s (placeholder até o centro de cura do M8); `WildRespawnPoint` recria a selvagem 6 s depois (placeholder até `SpawnZone` no M7).
  - Fora do M4: música de combate, área de combate dinâmica (§5.1), hotbar na tela, números de dano, drops e XP.
- [ ] **M5 Captura**: esfera arremessável em arco (segurar botão direito mira, soltar arremessa), fórmula de captura com 3 balanços (§6), criatura capturada vai para a equipe (HUD com 6 espaços), 3 corações do treinador com invulnerabilidade, regeneração e aggro de captura (§4.3).
  - Decisões herdadas: esferas infinitas com cooldown de 1 s (inventário no M8); a ativa é sempre a primeira da equipe; escapar da esfera deixa a selvagem provocada contra o treinador; desmaio do treinador é placeholder (2 s caído, volta ao ponto de partida) até o M8; sem texto flutuante até o M7.
- [ ] **Troca de criatura** (GAME_DESIGN §4.3): segurar Tab abre o menu radial da equipe, o mouse escolhe e soltar confirma. Guardada, só muda a ativa; em campo, troca na hora no mesmo lugar, mantendo o controle, com recarga global de 3 s. Desmaiadas não podem ser escolhidas; o HP fica guardado por criatura.
- [ ] **Andares (planaltos e escadas)** (GAME_DESIGN §7.1.1): golpes, projéteis e IA só interagem no mesmo andar; selvagens não usam escadas.
- [ ] **Mapa com biomas** (GAME_DESIGN §7.1.2): grama, praia, trilha, deserto com oásis, neve com lago meio congelado, pântano e vulcão com lago de lava, cada um com planalto.
- [ ] **M6 Conteúdo base**: 6 espécies e 12 golpes, elementos e XP/nível.
  - Decisões herdadas: 6 elementos, um por espécie (nomes herdados Planta, Fogo, Terrestre, Elétrico, Lutador, Gelo; renomear está pendente em GAME_DESIGN §12); golpes sem elemento são neutros; bônus de mesmo elemento existe e começa desligado. XP para o próximo = `10 × nível^1,5`; selvagem dá `xpBase × nível / 5`, dividido entre quem a acertou; atributos +8% da base por nível; nível máximo 30; inicial no nível 5; selvagens 3–6; capturada mantém o nível.
  - Fora do M6: learnset, evolução, drops, aviso visual de subida de nível e nível das selvagens na tela.
- [ ] M7 a M9 (ver GAME_DESIGN §10). O M7 inclui o sistema de encontros híbridos (seção abaixo).

## Projeto atual (manter em dia)

### Configuração (`project.godot`)
- Cena principal: `res://scenes/main.tscn`.
- Viewport 640×360, janela 1280×720, stretch `viewport`, aspect `keep`, scale mode `integer`.
- `default_texture_filter = Nearest`; `snap_2d_transforms_to_pixel` e `snap_2d_vertices_to_pixel` ligados.
- Autoload: `EventBus` → `res://scripts/core/event_bus.gd`.
- Input Map:

| Ação | Tecla | Uso |
|---|---|---|
| `move_up` / `move_down` / `move_left` / `move_right` | W S A D (e setas) | movimento em 8 direções |
| `interact` | E | interagir |
| `switch_control` | Q | toque solta/alterna; segurar recolhe |
| `aim_throw` | botão direito | segurar mira, soltar arremessa |
| `attack_aim` | botão esquerdo | reservado (mira de golpes) |
| `move_1` … `move_4` | 1 2 3 4 | golpes da hotbar |
| `dash` | Espaço | esquiva |
| `team_menu` | Tab | segurar abre o menu radial |

### Scripts e sistemas
- `scripts/core/event_bus.gd` (autoload `EventBus`): sinais globais. Vazio no M0; cada sinal entra junto com o sistema que o emite.
- `scripts/core/units.gd` (`Units`): `TILE = 32`, `tiles(n)`, `to_tiles(px)`.
- `scripts/core/camera_rig.gd` (`CameraRig`, Camera2D): `set_target(node, blend_time)`, `set_bounds(rect)`; segue o alvo em `_physics_process`.
- `scenes/main.tscn`: bootstrap com `World` (Node2D, y-sort ligado), `CameraRig` e `HUD` (CanvasLayer).

### Pastas
`art/` (com `CREDITS.md`), `audio/`, `data/`, `docs/`, `scenes/` (`world/`, `actors/`, `ui/`), `scripts/` (`core/`, `data/`, `combat/`, `creatures/`, `trainer/`, `world/`, `ui/`, `save/`), `tests/` (`run_tests.gd`, `test_case.gd`, `unit/`).

### Comandos
O executável do Godot 4.7.2 fica em `C:\Users\pedro\Desktop\Godot.exe` (no Git Bash: `/c/Users/pedro/Desktop/Godot.exe`). Ele imprime no terminal normalmente com `--headless`.

```bash
# Registrar classes/importar assets (rodar após criar class_name novo ou adicionar asset)
/c/Users/pedro/Desktop/Godot.exe --headless --path . --import
# Testes de lógica pura
/c/Users/pedro/Desktop/Godot.exe --headless --path . -s res://tests/run_tests.gd
```

Testes: cada arquivo `tests/unit/test_*.gd` estende `res://tests/test_case.gd`; métodos que começam com `test_` são executados. Asserções: `assert_true`, `assert_eq`, `assert_almost_eq`. O runner sai com código 1 se algum teste falhar.

## Sistema de encontros híbridos (M7): regras de implementação

Design completo em GAME_DESIGN §7.5. Criaturas **visíveis no mundo** como base, mais criaturas **escondidas no mato alto**. **Não existe encontro aleatório por passo.** **Não implementar antes do M7.**

- **Comportamento:**
  - Em área aberta, spawn visível com `WildAIBrain` normal.
  - No mato alto, parte spawna `Hidden`: fica invisível, sem colisão com o jogador e sem percepção, e o tile onde está balança periodicamente sem revelar a espécie.
  - É revelada quando o treinador ou a criatura do jogador entra no mesmo tile ou num raio curto, ou quando uma pedrinha arremessada pelo treinador cai no mato.
  - Reação ao ser revelada: `Passiva` foge, `Neutra` fica alerta, `Agressiva` faz emboscada (salta no alvo mais próximo e inicia combate).
  - Espécies raras podem ser "só escondidas".
  - Eventos de encontro e combate ("Apareceu!", "Desmaiou!", "Errou!") usam texto flutuante no mapa, **nunca** janela modal.
- **Arquitetura:**
  1. `Hidden` é **um estado a mais no `WildAIBrain`** (Hidden → Revealed → fluxo normal). Não criar classe separada de criatura escondida.
  2. Mato alto = nó `TallGrassArea` (`Area2D`, em `scripts/world/`). Ele detecta entradas e impactos de pedrinha e **emite um sinal**; quem reage é a criatura. O mato **não** referencia o `WildAIBrain`.
  3. O balanço do mato é visual puro (`AnimationPlayer` ou shader) e escuta o sinal `hidden_creature_rustle`. Nada de lógica de gameplay no shader ou na animação.
  4. Cada entrada de espécie em `SpawnZone`/`SpawnTable` ganha `spawn_mode` (`VISIBLE`, `HIDDEN_IN_GRASS` ou `BOTH`) e `hidden_weight` (peso quando o spawn cai em mato alto). Os valores vêm do Resource (.tres), nunca do código.
  5. A pedrinha reutiliza o **projétil em arco** da esfera de captura: mesma cena/script, dados diferentes via `ItemData`/`ThrowableData`. Não duplicar código de arremesso.
  6. Criaturas `Hidden` contam no limite de população da zona e usam o mesmo pooling/despawn das visíveis.
  7. **Testes em `tests/unit` obrigatórios:** escolha de espécie por `spawn_mode`/peso e transição Hidden → Revealed por temperamento.
- **Fora de escopo:** encontro aleatório por passos, item do tipo "repelente" e tela de transição de batalha.

## Fluxo obrigatório

1. **Antes de responder perguntas sobre o código ou alterar código:** consultar o grafo do graphify primeiro (`graphify query`, `graphify explain`, `graphify path`; ver a seção graphify abaixo). Ler arquivos só nas linhas que o grafo apontou.
2. **Depois de qualquer alteração de código:** o grafo é atualizado automaticamente (hook `PostToolUse` em `.claude/settings.json` roda `graphify update .`; hooks de git o atualizam em commit/checkout/merge). Se a alteração foi feita fora do Claude Code (pelo editor do Godot, IDE) e não houve commit, rodar `graphify update .` manualmente.
3. **Depois de qualquer alteração de código, atualizar este CLAUDE.md** quando ela mudar algo descrito aqui: novos scripts/sistemas, pastas, cenas, autoloads, ações do Input Map, convenções ou comandos. Manter a seção "Projeto atual" em dia.
4. **Depois de mexer em lógica pura:** rodar os testes headless.

## Manutenção do grafo

> **Limitação atual (2026-11-04):** o graphify instalado não reconhece arquivos `.gd` (GDScript) e pula todos eles, então `graphify-out/graph.json` não é gerado para este projeto. Enquanto isso, o passo 1 do fluxo obrigatório cai para busca normal (Grep/Glob, lendo só os trechos necessários). Os hooks continuam instalados e passam a funcionar sozinhos quando o graphify ganhar suporte a GDScript; conferir com `graphify extract . --code-only --force`.

- Saída em `graphify-out/` (`graph.json`, `GRAPH_REPORT.md`, `graph.html`). A pasta **não vai para o git** (está no `.gitignore`): cada máquina gera o grafo localmente pelos hooks ou com o rebuild completo abaixo.
- `.graphifyignore` exclui configs e gerados (`.godot/`, `.claude/`, `*.import`, `*.uid`) para o grafo focar no código.
- Rebuild completo: `graphify extract . --code-only --force` seguido de `graphify cluster-only . --no-label`.
- Após refatorações que removem muito código, `graphify update . --force`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

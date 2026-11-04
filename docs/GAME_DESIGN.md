# Monster Tamer 2D — Documento de Design e Direcionamento

> Documento vivo. Serve de referência para humanos **e** para o Claude Code. Toda decisão de design que mudar deve ser atualizada aqui antes de virar código.

---

## 1. Visão em uma frase

Um RPG 2D top-down de criaturas em que você **explora um mundo aberto contínuo como treinador**, encontra criaturas selvagens espalhadas pelo mapa e **assume o controle direto da sua criatura** para lutar em tempo real ali mesmo, sem trocar de tela.

### Referências e o que pegar de cada uma

| Referência | O que aproveitar | O que NÃO copiar |
|---|---|---|
| **Poke2DArena** (e arenas de ação estilo "Pokémon em tempo real") | Combate em tempo real, baseado em habilidade: movimentação livre, ataques com hitbox, telegrafia, cooldowns, esquiva | A arena fechada e separada do mundo |
| **Monster Tamer** (gênero) | O jogador **controla a criatura** diretamente durante o combate | — |
| **PokeTibia** (PXG, OTPokémon etc.) | Mundo único e contínuo, criaturas selvagens visíveis andando pelo mapa, batalha acontece no próprio mapa, hotbar de golpes, treinador acompanhando a criatura | Estrutura MMO, grind excessivo, UI poluída de servidor de Tibia |
| **Imagem de referência** | Pixel art top-down 3/4, paleta saturada e quente, vegetação densa, água com ondulação e vitórias-régias, contorno escuro suave nos sprites | — |

### ⚠️ Regra de propriedade intelectual (inegociável)

- **Nada** de nomes, sprites, sons, tipos com nomes idênticos à marca, logotipos ou criaturas da franquia Pokémon. A Nintendo/The Pokémon Company derruba fangames com frequência.
- Criaturas, golpes, itens e o nome do jogo são **originais**. "Pokémon" só aparece neste documento como referência de gênero.
- Assets de terceiros apenas com licença compatível (CC0, CC-BY com crédito, ou comprados). Registrar a origem de cada asset em `art/CREDITS.md`.

---

## 2. Pilares de design

1. **Mundo sem costuras** — explorar, encontrar e lutar acontece no mesmo espaço, sem tela de transição. A câmera e a UI se adaptam; a cena não muda.
2. **Habilidade acima de números** — posicionamento, esquiva e leitura de telegrafia importam mais que nível. Nível ajuda, mas não substitui jogar bem.
3. **Dois corpos, um jogador** — o treinador e a criatura são personagens distintos com papéis distintos. Alternar entre eles é a mecânica central, não um detalhe.
4. **Legibilidade em pixel art** — todo ataque perigoso precisa ser lido em menos de 0,5 s apenas pela forma e cor do telegrafo.

---

## 3. Loop principal

```
Explorar (treinador) ──► Avistar criatura selvagem
        ▲                        │
        │                        ▼
  Curar / organizar       Soltar criatura (assume o controle dela)
  equipe / evoluir               │
        ▲                        ▼
        │                 Combate em tempo real no mapa
        │                        │
        │            ┌───────────┴───────────┐
        │            ▼                       ▼
        │     Enfraquecer alvo         Derrotar alvo (XP, drops)
        │            │
        │            ▼
        │   Voltar ao treinador e lançar a "esfera" (captura)
        │            │
        └────────────┴── Recompensa ──► progressão
```

---

## 4. Sistema de controle (dois modos)

### 4.1 Modo Treinador (padrão fora de combate)
- Movimento livre em 8 direções (não em grade) com WASD.
- Interagir com NPCs, baús, placas, plantas, água (pescar) — tecla **E**.
- Lançar item de captura — mira com o **mouse**, arremesso com trajetória em arco.
- Plataforma alvo: **PC com teclado e mouse**. Suporte a controle fica para avaliação futura (não projetar para ele agora, mas manter o input via ações do Input Map para não fechar a porta).
- Usar itens de cura na criatura (precisa estar a uma distância mínima dela).
- A criatura ativa, se estiver fora da esfera, segue o treinador via IA de "follow".

### 4.2 Modo Criatura (combate)
- Tecla **Q** solta a criatura e **transfere o controle** para ela. A câmera passa a seguir a criatura.
- Movimento próprio em 8 direções (cada espécie tem velocidade e aceleração diferentes).
- **4 golpes** em hotbar (teclas 1-4) + **esquiva/dash** com cooldown. Golpes direcionais são **mirados com o mouse** (sem mira automática).
- O treinador vira NPC controlado por IA: fica parado em posição segura ou se afasta de perigo de forma simples.

### 4.3 Regras de alternância
- **Coleira (leash):** raio máximo que a criatura pode se afastar do treinador enquanto é controlada. Padrão: **10 tiles**, valor configurável. Ao atingir o limite, o movimento **trava naquela direção** (a criatura pode andar para os lados ou voltar). Feedback visual: uma linha sutil entre treinador e criatura que fica vermelha a partir de 80% do raio.
- Voltar ao treinador (tecla **Q** de novo) é instantâneo, mas a criatura **continua no campo** sob IA **apenas defensiva**: esquiva e se reposiciona, mas **não ataca**. Dano só acontece quando o jogador a controla. Isso permite: enfraquecer → trocar → lançar esfera.
- **Vida do treinador (proposta, validar em playtest):** o treinador tem **3 corações**. Cada golpe que o acerta tira 1 coração, independente do dano do golpe.
  - **Aggro de captura:** criaturas selvagens priorizam a criatura do jogador, mas **mudam o alvo para o treinador** enquanto ele mira ou lança a esfera. É isso que torna a captura arriscada.
  - Ser atingido **interrompe a mira/arremesso** e aplica knockback curto.
  - **~1 s de invulnerabilidade** após levar um hit (evita perder tudo num ataque em área).
  - Corações **regeneram fora de combate**.
  - Zerar os corações = desmaio = derrota (ver 5.6).
- Recolher a criatura (segurar **Q**) a guarda na esfera, com um pequeno tempo de canalização interrompível.
- **Trocar de criatura:** segurar **Tab** abre o menu radial da equipe; o mouse escolhe e soltar confirma. Com a criatura guardada, só muda qual é a ativa; com ela em campo, a troca é na hora, no mesmo lugar, mantendo o controle, com **recarga global de 3 s** (evita "troca infinita"). Desmaiadas não podem ser escolhidas; o HP fica guardado por criatura.
- **Equipe:** o treinador carrega até **6 criaturas**, mas apenas **1 fica em campo** por vez.

> **Decidido:** o jogador controla **apenas um personagem por vez** (treinador **ou** criatura). Não haverá controle simultâneo.

---

## 5. Combate no mundo (sem arena separada)

### 5.1 Início de combate
- Criaturas selvagens têm **raio de percepção** e **temperamento**: `Passiva` (foge), `Neutra` (só reage se atacada), `Agressiva` (ataca ao ver).
- O combate começa quando: o jogador ataca, uma agressiva detecta o treinador/criatura, ou o jogador entra em zona de "chefe".
- **Não há transição de cena.** Ao iniciar:
  - a música faz crossfade para a trilha de combate;
  - aparece a barra de HP do alvo e a hotbar;
  - forma-se uma **área de combate dinâmica** (círculo suave no chão, raio ~12 tiles) centrada no ponto do encontro. Sair dela por X segundos encerra o combate (fuga).

### 5.2 Durante o combate
- Outras criaturas selvagens próximas **podem entrar** na luta se forem agressivas ou do mesmo bando. Isso é intencional e cria situações emergentes, mas deve ser limitado (máx. 3 inimigos simultâneos no começo).
- O terreno importa: água, grama alta, rochas e árvores bloqueiam projéteis e movimento conforme sua camada de colisão. Algumas espécies podem nadar/voar e ignorar certos obstáculos.
- NPCs neutros, objetos interativos e o resto do mundo continuam funcionando normalmente.

### 5.3 Golpes
Cada golpe é um `Resource` (`MoveData`, arquivo `.tres`) com:
- **Forma:** projétil, cone, linha, círculo no alvo, dash com dano, aura, invocação.
- **Telegrafo:** duração e forma (vermelho = interrompível, amarelo = não interrompível).
- **Dano base, elemento, categoria** (física/especial), cooldown, knockback, efeito de status, chance de efeito.
- **Sem energia/PP no MVP:** o único limitador de uso é o cooldown. Reavaliar após playtest do M6.
- **Animação e VFX** referenciados por ID.

### 5.4 Atributos (versão enxuta)
Começar com poucos atributos e só expandir se o playtest pedir:

`HP`, `Ataque`, `Defesa`, `Velocidade` (movimento + recarga), `Poder Especial`.

Fórmula de dano inicial (ajustar depois, centralizar em uma única classe `DamageCalculator`):

```
dano = (base × (atk / def) × multiplicadorElemental × multiplicadorStatus × variação[0.9..1.1]) + 1
```

### 5.5 Elementos
Tabela própria e original, com **6 a 8 elementos** no lançamento (ex.: Brasa, Maré, Broto, Pedra, Vento, Faísca, Sombra, Luz). Matriz em um único Resource `ElementChart` (`.tres`) editável no Inspector. Valores: 2.0 / 1.0 / 0.5 / 0.

### 5.6 Fim de combate
- Vitória: XP dividida entre as criaturas que participaram, drops espalhados no chão (coletados pelo treinador).
- Fuga: sair da área de combate.
- Derrota: criatura ativa desmaia → forçar troca; sem criaturas ou treinador desmaiado → derrota.
- **Penalidade de derrota:** o jogador **perde uma porcentagem do dinheiro** carregado (sugestão inicial: 10%, configurável) e volta ao último ponto de cura com a equipe restaurada.

---

## 6. Captura

- Só o **treinador** pode capturar (reforça o pilar "dois corpos").
- Fluxo: enfraquecer o alvo com a criatura → voltar ao treinador → mirar e lançar a esfera.
- A esfera é um projétil físico: pode errar, bater em árvore, cair na água.
- Chance de captura:

```
chance = baseEspécie × (1 - HPatual/HPmáx)^1.5 × bônusEsfera × bônusStatus
```

- Feedback: a esfera balança até 3 vezes (cada balanço é uma rolagem), com som e partícula distintos para sucesso/falha.
- Enquanto o treinador mira, a criatura selvagem passa a atacá-lo (aggro de captura, ver 4.3) — risco/recompensa.

---

## 7. Mundo

### 7.1 Estrutura
- Mundo contínuo, dividido internamente em **regiões** (ex.: Praia, Floresta, Pântano, Montanha) e cada região em **chunks** de cenas carregadas aditivamente conforme o jogador se aproxima.
- Transições entre regiões são **contínuas** (sem fade), exceto entradas de cavernas/casas, que podem usar um fade curto.


### 7.1.1 Andares (planaltos e escadas)
- O mapa tem **andares**: o chão e planaltos elevados ligados por escadas.
- Golpes, projéteis e IA **só interagem no mesmo andar**. Implementação: cada andar usa seu próprio conjunto de camadas/máscaras de colisão; a escada troca o andar do corpo.
- Selvagens **não usam escadas**: ficam no andar onde nasceram.

### 7.1.2 Biomas do mapa
Grama, praia, trilha, deserto com oásis, neve com lago meio congelado, pântano e vulcão com lago de lava, cada um com pelo menos um planalto.

### 7.2 Spawns
- `SpawnZone` = área (polígono ou retângulo) + tabela de espécies com peso + faixa de nível + horário do dia + limite de população + tempo de respawn.
- Spawns só acontecem **fora da câmera**; criaturas longe demais do jogador são despawnadas (pooling).
- Algumas espécies raras só aparecem em condições (noite, chuva, perto de água).

### 7.3 Interação com o mundo
- Objetos interativos implementam uma interface `IInteractable`.
- Obstáculos que exigem criaturas específicas (cortar arbusto, quebrar pedra, atravessar água) — gancho de progressão estilo metroidvania leve.

### 7.4 Ciclo dia/noite e clima (pós-MVP)
- Usar `CanvasModulate` + `PointLight2D`/`DirectionalLight2D`. Clima afeta spawns e alguns golpes.

---

### 7.5 Encontros híbridos (M7)
Criaturas **visíveis no mundo** como base, mais criaturas **escondidas no mato alto**. **Não existe encontro aleatório por passo** (sem rolagem de chance a cada tile andado). Entra no **M7**; não implementar antes.

- **Áreas abertas:** criaturas selvagens spawnam visíveis e andam pelo mapa (`WildAIBrain` normal).
- **Mato alto:** parte das criaturas spawna no estado `Hidden`. Enquanto escondidas:
  - ficam invisíveis, sem colisão com o jogador e sem perceber ninguém;
  - o tile de mato onde estão **balança** periodicamente (dica visual, sem revelar a espécie).
- **Revelar uma criatura escondida:**
  - o treinador ou a criatura do jogador entra no mesmo tile ou num raio curto; ou
  - o treinador **arremessa uma pedrinha** (mira pelo mouse, mesmo sistema de arremesso da esfera) e ela cai no mato.
- **Ao ser revelada**, a reação segue o temperamento: `Passiva` foge, `Neutra` fica alerta, `Agressiva` faz **emboscada** (salta em direção ao alvo mais próximo e inicia combate).
- **Espécies raras** podem ser configuradas como "só escondidas".
- **Texto flutuante no mapa** para eventos de encontro e combate ("Apareceu!", "Desmaiou!", "Errou!"), nunca janela modal.
- **Fora de escopo:** encontro aleatório por passos, item do tipo "repelente" e tela de transição de batalha.

Regras de arquitetura: seção "Sistema de encontros híbridos" do `CLAUDE.md`.

---

## 8. Direção de arte (baseada na imagem de referência)

- **Perspectiva:** top-down 3/4 (vemos o topo e a frente dos objetos).
- **Resolução de tile:** **32×32 px** (decidido). Nunca misturar com outros tamanhos. `TileSet.tile_size = (32, 32)`.
- **Unidade de mundo:** no Godot 2D a unidade é o pixel. **1 tile = 32 px**; distâncias de design em tiles são convertidas com `Units.TILE` (ex.: coleira de 10 tiles = `Units.tiles(10)` = 320 px). Nunca espalhar o número 32 pelo código.
- **Resolução de referência:** **640×360** (20×11 tiles visíveis). Pixel perfect com `display/window/stretch/mode = "viewport"` + `stretch/scale_mode = "integer"`: o jogo renderiza em 640×360 e é ampliado em múltiplos inteiros (1280×720, 1920×1080, 2560×1440). É o equivalente do "Upscale Render Texture" e evita as linhas finas entre tiles.
- **Snap:** `rendering/2d/snap/snap_2d_transforms_to_pixel = true` e `snap_2d_vertices_to_pixel = true`.
- **Sprites:** filtro **Nearest** (padrão do projeto em `rendering/textures/canvas_textures/default_texture_filter`), importação **Lossless/sem compressão**, sem mipmaps. Pivô nos pés: a origem do nó fica na base do sprite (`Sprite2D` com `centered = true` e `offset.y = -altura/2`). Tiles usam o centro.
- **Ordenação por Y:** `y_sort_enabled = true` no nó-pai das entidades do mundo e nas `TileMapLayer` de props; objetos mais abaixo na tela ficam na frente. Árvores com origem no tronco (`y_sort_origin` do tile).
- **Origem da arte:** feita à mão + assets gratuitos. Para os dois combinarem:
  - priorizar packs **CC0** (sem exigência de crédito) e registrar todos em `art/CREDITS.md`;
  - recolorir assets externos para a paleta fixa do projeto antes de importar;
  - manter o mesmo estilo de contorno e direção de luz (luz vindo de cima-esquerda) em tudo;
  - ferramenta sugerida: Aseprite (pago) ou LibreSprite/Pixelorama (gratuitos).
- **Paleta:** verdes profundos, marrons quentes de terra, areia clara, água turquesa saturada. Manter uma paleta fixa (ex.: 32–48 cores) em `art/palette/`.
- **Contorno:** sprites com contorno escuro (não preto puro) para destacar do fundo.
- **Água:** tile animado + shader simples de ondulação (`canvas_item`); vitórias-régias e espuma na borda como tiles decorativos.
- **Personagens:** treinador ~32×48 px, criaturas de 32×32 a 96×96 conforme porte.
- **Animações em 8 direções** (decidido) para treinador e criaturas. Para reduzir trabalho, as direções da esquerda podem ser o espelhamento horizontal das da direita (5 desenhadas: N, NE, E, SE, S + 3 espelhadas com `flip_h`).

---

## 9. Arquitetura técnica (Godot)

### 9.1 Stack
- **Godot 4.7** (versão padrão, sem .NET), renderer **Compatibility** (leve e suficiente para 2D pixel art).
- Linguagem: **GDScript** com tipagem estática em tudo (`var hp: int`, `func f(x: float) -> int`).
- **Input Map** (`project.godot`) com ações nomeadas. O código lê só ações (`Input.get_vector`, `Input.is_action_pressed`, `event.is_action(...)`); **nunca** `Input.is_key_pressed`, `Input.is_physical_key_pressed` nem códigos de tecla no código.
- **Camera2D** própria (`CameraRig`) no lugar do Cinemachine: segue um alvo, troca de alvo com transição suave, e os limites do mapa ficam em `limit_left/top/right/bottom` (confiner).
- **TileMapLayer** + **TileSet** com terrains (autotile) para o mundo; colisão e camadas físicas definidas no TileSet.
- UI com nós `Control` e `Theme` próprio, fonte pixel.
- Testes: runner próprio em `tests/` rodando headless (`godot --headless -s res://tests/run_tests.gd`). Pode migrar para GUT ou GdUnit4 se precisar de recursos a mais.

### 9.2 Princípios
1. **Dados em Resources, lógica em GDScript puro sempre que possível.** Definições estáticas (espécies, golpes, elementos, itens, tabelas de spawn) são classes `extends Resource` com `class_name`, salvas como `.tres` em `data/`. Cálculo de dano, captura, XP e tabela de elementos são classes `extends RefCounted` (sem `Node`), testáveis sem cena.
2. **Composição sobre herança.** Uma criatura é uma cena (`CharacterBody2D`) com nós-componente filhos (`Health`, `Mover`, `MoveCaster`, `StatusController`, `BrainController`), não uma hierarquia profunda de scripts. Herança no máximo um nível (ex.: `Brain` → `PlayerBrain`).
3. **Mesmo corpo, cérebros diferentes.** A criatura do jogador e a selvagem usam a mesma cena; muda só a fonte de comandos. GDScript não tem interface, então o contrato `IBrain` é a classe base `Brain` (`extends RefCounted`), que devolve um comando por frame:
   - `PlayerBrain` (lê o Input Map)
   - `WildAIBrain` (máquina de estados: Vagar → Perceber → Perseguir → Atacar → Fugir)
   - `FollowBrain` (segue o treinador fora de combate)
   - `DefensiveBrain` (só esquiva/reposiciona, não ataca)
   - Trocar de modo = `BrainController.set_brain(novo)`. **Esta é a decisão de arquitetura mais importante do projeto.**
4. **Sinais para desacoplar.** UI, áudio e câmera escutam sinais (`damaged`, `combat_started`, `control_switched`), nunca são chamados diretamente pela lógica de combate. Sinais locais do componente quando o ouvinte já tem a referência; eventos globais passam pelo autoload `EventBus`.
5. **Sem singletons espalhados.** No máximo dois autoloads: `EventBus` (só sinais, sem estado) e, quando precisar, `GameServices`. Criar outro autoload exige atualizar este documento antes.

### 9.3 Estrutura de pastas

```
res://
  art/              (sprites/, tiles/, palette/, vfx/, CREDITS.md)
  audio/
  data/             (.tres: species/, moves/, elements/, items/, spawn_tables/)
  scenes/
    main.tscn       (bootstrap)
    world/          (region_beach_00.tscn, ...)
    actors/         (trainer.tscn, creature.tscn)
    ui/
  scripts/
    core/           (EventBus, Units, utilidades)       não depende de ninguém
    data/           (classes Resource)                  depende de core
    combat/         (dano, golpes, hitbox, status)      core, data
    creatures/      (componentes, brains, IA)           core, data, combat
    trainer/        (controle, interação, captura)      core, data, combat, creatures
    world/          (spawns, chunks, interagíveis)      core, data, creatures
    ui/             (HUD, menus)                        pode ler tudo; ninguém lê ui
    save/
  tests/
    run_tests.gd    (runner headless)
    unit/           (lógica pura: test_*.gd)
```

Godot não tem assembly definitions, então a direção das dependências é **regra de revisão**: um script só referencia `class_name` das pastas permitidas na tabela acima (UI depende de Combat, nunca o contrário). Quebrar a regra exige atualizar este documento.

### 9.4 Modelos de dados principais

```gdscript
# Definição estática (Resource, salva em .tres)
class_name CreatureSpecies extends Resource
  id, display_name, elements[1..2], base_stats, learnset, catch_rate,
  move_speed, size, temperament, sprite_frames, evolutions

class_name MoveData extends Resource
  id, element, category, power, cooldown, shape, telegraph_time,
  interruptible, knockback, status_effect, status_chance, vfx_id, sfx_id

# Instância em runtime (serializável no save)
class_name CreatureInstance extends RefCounted
  species_id, nickname, level, xp, current_hp, ivs/variação,
  known_move_ids[4], status, unique_id
```

### 9.5 Save
- JSON em `user://save.json`, com campo `save_version` para migrações.
- Salvar apenas IDs, nunca caminhos ou referências diretas; um registro (`DataRegistry`) resolve ID → Resource.

---

## 10. Roadmap (milestones)

Cada milestone termina com algo **jogável**. Não avançar sem fechar o anterior.

| # | Milestone | Entregável jogável |
|---|---|---|
| M0 | Setup | Projeto Godot 4.7 (Compatibility), Input Map, `CameraRig` (Camera2D), pixel perfect (viewport + escala inteira), pastas, `EventBus`, runner de testes, CLAUDE.md, git + LFS |
| M1 | Treinador no mundo | Um mapa de praia com tilemap, colisão, ordenação por Y, treinador andando com animação |
| M2 | Criatura seguindo | Criatura com `FollowBrain` seguindo o treinador; soltar/recolher com Q |
| M3 | Troca de controle | `PlayerBrain` na criatura, câmera troca de alvo, leash funcionando |
| M4 | Combate mínimo | 1 criatura selvagem com IA simples, 2 golpes (projétil e cone), HP, dano, morte |
| M5 | Captura | Esfera arremessável, fórmula de captura, criatura vai para a equipe |
| M6 | Conteúdo base | 6 espécies, 12 golpes, tabela de elementos, XP e level up |
| M7 | Mundo vivo | SpawnZones, despawn/pooling, encontros híbridos (§7.5), 2 regiões conectadas, chunks carregados por proximidade |
| M8 | Meta | Equipe (6), centro de cura, inventário, save/load |
| M9 | Polimento | Juice (hitstop, screenshake, partículas), áudio, menus |

**Vertical slice = M0 a M6.** Só pensar em evolução, chefes, multiplayer ou dia/noite depois disso.

---

## 11. Fora de escopo (por enquanto)

- Multiplayer / MMO (apesar da inspiração em PokeTibia). Se um dia entrar, a arquitetura de `IBrain` + comandos facilita, mas não projetar para isso agora.
- Mundo procedural.
- Mais de 30 espécies antes do vertical slice estar divertido.
- Sistema de breeding, habilidades passivas complexas, natures.

---

## 12. Decisões em aberto

### Decididas
- [x] Engine: **Godot 4.7 + GDScript** (o plano original era Unity; migrado em 2026-11-04).
- [x] Tile: **32 px** (1 tile = 32 px no Godot, via `Units.TILE`).
- [x] Leash: **trava o movimento** no limite, raio padrão 10 tiles (ajustável em playtest).
- [x] Golpes: **só cooldown** no MVP.
- [x] Criatura sob IA quando o jogador volta ao treinador: **só se defende**.
- [x] Mira: **mouse**, PC apenas por enquanto. Controle será avaliado no futuro.
- [x] Controle: **um personagem por vez**.
- [x] Animação: **8 direções**.
- [x] Elementos no lançamento: **6 a 8**.
- [x] Penalidade de derrota: **perde % do dinheiro**.
- [x] Equipe: **6 criaturas**, **1 em campo** por vez.
- [x] Arte: **feita à mão + assets gratuitos**, unificados pela paleta.
- [~] Vida do treinador: proposta de **3 corações + aggro de captura** (validar no M5).

### Pendentes
- [ ] Nome do jogo e nome das "esferas" de captura (originais, sem referência à franquia).
- [ ] Nomes dos elementos: os herdados (Planta, Fogo, Terrestre, Elétrico, Lutador, Gelo) coincidem com a tradução oficial dos tipos da franquia. Avaliar nomes próprios (ex.: Broto, Brasa, Pedra, Faísca, Punho, Geada) antes do M6.

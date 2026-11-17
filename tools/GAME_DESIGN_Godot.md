# Monster Tamer 2D — Documento de Design (versão Godot)

> Documento vivo. Serve de referência para humanos **e** para o Claude Code. Toda decisão de design que mudar deve ser atualizada aqui **antes** de virar código.
>
> Esta versão junta o documento original com tudo o que foi decidido durante o protótipo em Unity (M0–M6 e extras) e troca a parte técnica para **Godot 4**. As regras de jogo, os números e as fórmulas já foram testados em playtest no protótipo, salvo onde estiver marcado "validar".

---

## 1. Visão em uma frase

Um RPG 2D top-down de criaturas em que você **explora um mundo aberto contínuo como treinador**, encontra criaturas selvagens espalhadas pelo mapa e **assume o controle direto da sua criatura** para lutar em tempo real ali mesmo, sem trocar de tela.

### Referências e o que pegar de cada uma

| Referência | O que aproveitar | O que NÃO copiar |
|---|---|---|
| **Poke2DArena** (e arenas de ação no estilo "monstros em tempo real") | Combate em tempo real baseado em habilidade: movimentação livre, ataques com hitbox, telegrafia, cooldowns, esquiva | A arena fechada e separada do mundo |
| **Monster Tamer** (gênero) | O jogador **controla a criatura** diretamente durante o combate | — |
| **PokeTibia** (PXG, OTPokémon etc.) | Mundo único e contínuo, criaturas selvagens visíveis andando pelo mapa, batalha no próprio mapa, hotbar de golpes, treinador acompanhando a criatura, construções no mesmo mundo | Estrutura MMO, grind excessivo, UI poluída de servidor |
| **Imagem de referência** | Pixel art top-down 3/4, paleta saturada e quente, vegetação densa, água com ondulação e vitórias-régias, contorno escuro suave nos sprites | — |

### ⚠️ Regra de propriedade intelectual (inegociável)

- **Nada** de nomes, sprites, sons, tipos com nomes idênticos à marca, logotipos ou criaturas da franquia Pokémon. A empresa dona da marca derruba fangames com frequência.
- Criaturas, golpes, itens e o nome do jogo são **originais**. "Pokémon" só aparece neste documento como referência de gênero.
- Assets de terceiros apenas com licença compatível (CC0, CC-BY com crédito, ou comprados). Registrar a origem de cada asset em `res://art/CREDITS.md`.
- **Arte gerada por IA passa por revisão** antes de entrar: itens com símbolos de outra franquia (ex.: uma esfera vermelha e branca, desenho de criatura conhecida) são descartados e refeitos com o emblema do próprio jogo.
- **Atenção:** os nomes e as relações dos elementos escolhidos (§5.5: Fogo > Planta e Gelo, Terrestre > Elétrico, Elétrico sem efeito em Terrestre) ficam bem perto da tabela da franquia. Palavras comuns não são exclusivas de ninguém, mas vale considerar nomes próprios do jogo antes do lançamento.

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

> **Decidido:** o jogador controla **apenas um personagem por vez** (treinador **ou** criatura). Não há controle simultâneo.

### 4.1 Modo Treinador (padrão fora de combate)

- **Andar:** movimento livre em 8 direções (não em grade) com WASD (setas também funcionam). A diagonal é normalizada.
  - **4 tiles/s**, aceleração de 40 tiles/s², desaceleração de 60 tiles/s². Resposta quase instantânea, sem "patinar".
  - Os valores ficam num `MovementProfile` (Resource), o mesmo tipo das criaturas.
  - Contra uma parede o corpo fica parado (animação `idle`) virado para o input; deslizando rente à parede, continua andando. A animação usa o deslocamento real, não o input (anda só com deslocamento ≥ 15% da velocidade máxima).
- **Correr:** segurar **Shift**. **6,5 tiles/s**, sem estamina. A animação de corrida só toca acima de 105% da velocidade de andar.
- **Rolar (dash):** tecla **Espaço**, na direção do input (sem input, para onde está virado).
  - Dura **0,4 s** e percorre ~3 tiles (7,5 tiles/s). Input ignorado durante a rolagem.
  - **Sem invulnerabilidade. Recarga de 5 s** a partir do início.
  - Não rola caído, atordoado ou sem o controle do treinador. Paredes param a rolagem.
  - No `MovementProfile`: `run_speed`, `dash_speed`, `dash_duration`, `dash_cooldown` (zero = o corpo não corre ou não rola). As criaturas podem usar a mesma rolagem como esquiva só mudando os dados.
- **Interagir** (NPCs, baús, placas, plantas, água) — tecla **E**.
- **Lançar item de captura:** **segurar o botão direito** mira (arco pontilhado + marcador no ponto de queda, alcance 6 tiles); **soltar** arremessa em arco.
- Usar itens de cura na criatura (precisa estar a uma distância mínima dela).
- A criatura ativa, fora da esfera, segue o treinador (IA de "follow": para a 1,5 tile, retoma acima de 2, desacelera no último 1,5; reaparece ao lado se passar de 10 tiles).
- **Plataforma:** PC com teclado e mouse. Controle fica para o futuro (o InputMap já não fecha a porta).

### 4.2 Modo Criatura (combate)

- **Q** (toque) solta a criatura na frente do treinador e **transfere o controle** para ela. A câmera passa a segui-la (com suavização).
  - O ponto de soltar procura um lugar livre (frente, diagonais, lados, trás), com um círculo livre no ponto e uma **linha fina** livre desde o treinador (não um círculo arrastado: ele nasceria encostado no obstáculo ao lado e bloquearia tudo). Sem ponto livre, não solta.
- Movimento próprio em 8 direções (cada espécie tem velocidade e aceleração).
- **4 golpes** nas teclas **1–4**, mirados com o **mouse** (sem mira automática).
- O treinador fica parado enquanto o jogador controla a criatura.

### 4.3 Regras de alternância

- **Q de novo (toque)** com a criatura fora alterna o controle (treinador ↔ criatura).
- **Segurar Q** canaliza **0,5 s** e recolhe a criatura (soltar a tecla cancela). Treinador e criatura ficam parados durante a canalização. Golpe no treinador interrompe, e é preciso soltar a tecla antes de tentar de novo.
- **Coleira:** a criatura controlada não passa de **10 tiles** do treinador. No limite o movimento **trava naquela direção** (dá para andar de lado ou voltar). Uma linha sutil liga os dois e fica vermelha a partir de 80% do raio.
- **Criatura com o controle no treinador:** IA **apenas defensiva**: sai de dentro de telegrafos inimigos (de lado), recua de inimigos a menos de 2,5 tiles e, sem ameaça, segue o treinador. **Nunca ataca.** Isso permite: enfraquecer → trocar → lançar esfera.
- **Vida do treinador:** **3 corações**. Cada golpe tira **1 coração**, independente do dano.
  - **Aggro de captura:** selvagens priorizam a criatura do jogador, mas **trocam o alvo para o treinador** enquanto ele mira, com a esfera no ar e por 0,5 s depois.
  - Ser atingido **cancela a mira** (precisa soltar o botão) e empurra.
  - **1 s de invulnerabilidade** depois de um golpe (o treinador pisca).
  - **Regenera 1 coração a cada 3 s depois de 6 s sem apanhar** (até existir estado de combate).
  - Zerar = desmaio = derrota (§5.6). *Placeholder até o M8:* fica caído 2 s e volta ao ponto de partida com a equipe curada.
- **Troca de criatura (menu radial):**
  - Segurar **Tab** abre o menu com os 6 espaços da equipe (espaço 1 no topo, sentido horário). O mouse aponta a partir do centro da tela; soltar o Tab confirma. Mouse no centro (zona morta, 6% da altura da tela) cancela. **O jogo não pausa.**
  - Criatura **guardada**: só muda qual sai no próximo Q, sem recarga.
  - Criatura **em campo**: a atual volta na hora e a nova sai no mesmo lugar e direção, mantendo quem está no controle. Depois disso, **recarga global de 3 s** (desenhada no centro do menu).
  - Desmaiada aparece apagada e não pode ser escolhida. Se a ativa desmaia, a troca seguinte não tem recarga.
  - O HP de cada criatura fica guardado na equipe: trocar não cura.
  - Não abre com o treinador caído nem durante o recolhimento.
- **Equipe:** até **6 criaturas**, **1 em campo** por vez. Só existe um corpo de criatura do jogador por vez.
- **Criatura desmaiada:** volta para a esfera na hora e não pode sair. *Placeholder até o centro de cura (M8):* revive com HP cheio em 10 s.

---

## 5. Combate no mundo (sem arena separada)

### 5.1 Início de combate

- Selvagens têm **raio de percepção** e **temperamento**:
  - `Passiva`: foge ao ver ou ao ser atacada;
  - `Neutra`: fica alerta e só revida se provocada;
  - `Agressiva`: ataca ao ver.
- Raios (tiles): percepção 5, perde o interesse a 8, distância máxima de casa 8 (volta até a metade), vagar 2,5.
- Ser atacada provoca a selvagem e faz quem atacou virar o alvo.
- O combate começa quando o jogador ataca, uma agressiva detecta o treinador/criatura ou o jogador entra em zona de chefe.
- **Sem transição de cena.** Ao iniciar *(ainda não feito)*:
  - a música faz crossfade para a trilha de combate;
  - aparece a barra de HP do alvo e a hotbar;
  - forma-se uma **área de combate dinâmica** (círculo suave no chão, raio ~12 tiles). Sair dela por X segundos encerra o combate (fuga).

### 5.2 Durante o combate

- Outras selvagens próximas **podem entrar** na luta se forem agressivas ou do mesmo bando (máx. 3 inimigos simultâneos no começo).
- O terreno importa: árvores, rochas e props bloqueiam projéteis e movimento; **a água bloqueia movimento, mas não projéteis**. Algumas espécies poderão nadar/voar.
- NPCs, objetos interativos e o resto do mundo continuam funcionando.
- Golpe do mesmo lado não dá dano (criatura do jogador não acerta o treinador).
- Selvagem derrotada perde a colisão e some em 0,6 s.

### 5.3 Golpes

Cada golpe é um Resource (`MoveData`) com:

- **Forma:** projétil, cone, postura, salto, investida, parede (e depois: linha, círculo no alvo, aura, invocação).
- **Telegrafo:** desenhado no chão com a forma do golpe, enchendo até o golpe sair. **Vermelho = interrompível, amarelo = não interrompível.** Fica acima do chão e abaixo dos personagens.
- **Dano base, elemento (ou neutro), categoria** (física usa Ataque, especial usa Poder Especial; ambas contra Defesa), cooldown, alcance, knockback, efeito de status e chance.
- **Cooldown conta a partir do início**, incluindo o telegrafo. **Sem energia/PP:** o único limitador é o cooldown.
- **Dano recebido (> 0) cancela golpe interrompível.** Durante o telegrafo o corpo fica parado.
- **Animação e efeitos:** clipe do corpo durante o golpe (`animation_clip`), efeito na frente do atacante quando sai (`cast_effect`, distância, altura, se gira), projétil animado em voo e efeito de impacto.
- **Mecânicas:**
  - **Atordoar** (`stun_duration`): o alvo não anda nem usa golpes, e o golpe que ele avisava é cancelado (mesmo não interrompível). Toca `hurt` parado no último frame e mostra estrelas sobre a cabeça. O treinador não é atordoado.
  - **Lançar:** o alvo sobe e cai (só visual, ~0,6 tile por 0,5 s).
  - **Puxar:** em vez de empurrar, puxa o alvo até ~0,9 tile do atacante (10 tiles/s).
  - **Dois toques (combo):** golpe com continuação (`follow_up`) e janela (`follow_up_window`). A mesma tecla dentro da janela solta a continuação; a recarga começa quando o combo termina. A selvagem emenda sempre que o alvo está no alcance.
  - **Postura (`Guard`):** guarda por um tempo (círculo azul em volta do corpo). O primeiro golpe recebido é **anulado** e dispara o contra-ataque na direção de quem atacou. A IA só usa quando o alvo está avisando um golpe que pega nela.
  - **Salto (`Leap`):** mira um **ponto** até o alcance; círculo amarelo no ponto de queda; o corpo voa até lá no aviso (não leva golpes no ar) e acerta todos no raio ao cair. Não cai em água, lava, obstáculo ou outro andar: o ponto recua até o primeiro lugar livre.
  - **Investida (`Charge`):** aviso parado com uma faixa até o ponto final; depois dispara em linha reta e acerta **uma vez** cada um no caminho, empurrando para o lado. Recua antes de obstáculos. Sem invulnerabilidade; atordoar ou desmaiar corta.
  - **Parede (`Wall`):** faixa até o ponto mirado (mín. 1,2 tile, máx. o alcance). Acerta uma vez cada um na faixa e sobe um pilar que bloqueia movimento de todos e projéteis dos dois lados, empurra para fora quem estiver no ponto e desmorona depois do tempo do golpe.
  - **Empurrão contra a parede (`wall_slam`):** um golpe marcado assim que empurra o alvo contra um pilar em até 0,6 s faz o pilar **explodir** (dano + atordoa 1 s quem estiver colado do lado do alvo, raio 1,2) e desmoronar.
- **Teclas:** 1–4 = os 4 golpes equipados. Depois, cada criatura aprende vários golpes (learnset) e o jogador escolhe 4.

### 5.4 Atributos e dano

`HP`, `Ataque`, `Defesa`, `Velocidade` (movimento + recarga), `Poder Especial`.

```
dano = floor(base × fatorNível × (atk / def) × multElemental × multStatus × variação) + 1
variação  = 0,9 .. 1,1
fatorNível = 1 + 0,08 × (nívelDoAtacante − 1)
```

- Multiplicador elemental 0 = **0 de dano**, sem empurrão e sem interromper, mas o golpe ainda conta como recebido (provoca a selvagem).
- O `fatorNível` acompanha o crescimento dos atributos: **duas criaturas do mesmo nível levam o mesmo número de golpes em qualquer nível**, e a diferença de nível pesa nos dois sentidos (nível 50 contra 20 derruba ~3,8× mais rápido).
- Tudo numa única classe pura (`DamageCalculator`), com testes.

### 5.5 Elementos

Tabela num único Resource `ElementChart`: lista de regras **atacante → defensor** com multiplicador (2,0 / 1,0 / 0,5 / 0). Par sem regra = 1,0; golpe ou defensor sem elemento = 1,0; **cada regra vale só num sentido**. Cada elemento é um Resource `ElementData` (id, nome, cor), então dá para criar elementos novos sem código.

- **Tipagem dupla:** a espécie pode ter um segundo elemento; o multiplicador é o produto dos dois (Fogo contra Gelo/Metal = ×4). O mesmo elemento duas vezes não conta dobrado.
- **Bônus de mesmo elemento** (golpe do elemento do atacante): existe no `ElementChart`, **desligado (1,0)** até decidir em playtest.

| Elemento | Espécie |
|---|---|
| Planta | Brotim |
| Fogo | Brasco |
| Terrestre | Cavatu |
| Elétrico | Javolt |
| Lutador | Tamandô |
| Gelo + Metal | Pingelo |

Regras atuais (todo o resto = 1,0):

- Fogo → Gelo, Fogo → Planta: **2,0**
- Terrestre → Elétrico: **2,0**
- Elétrico → Terrestre: **0**
- Metal → Gelo: **2,0**; Metal → Fogo, Elétrico, Metal: **0,5**
- Fogo, Lutador, Terrestre → Metal: **2,0**; Planta, Gelo → Metal: **0,5**

**Pendente:** elemento Água (Praia) e um elemento para o Algodão Doce; mais elementos depois.

### 5.6 Fim de combate, XP e nível

- **Vitória:** XP dividida entre as criaturas que participaram; drops espalhados no chão *(drops ainda não feitos)*.
  - A selvagem dá `xpBase × nível dela / 5` (mínimo 1).
  - "Participou" = acertou pelo menos um golpe nela. Divisão igual, arredondando para cima, mesmo que já tenha voltado para a esfera ou sido trocada. **Capturar não dá XP.**
  - `xpBase` por estágio: 1 ≈ 25, 2 ≈ 40, 3 ≈ 60.
- **Curva:** `XP para o próximo = 10 × nível^1,5 × (1 + max(0, nível − 30) / 60)` (nível 1 → 10, nível 5 → 112). **Nível máximo 100.** Sobe vários níveis de uma vez se der.

  | Nível | XP para o próximo | Vitórias por nível (xpBase 25 / 40 / 60) |
  |---|---|---|
  | 10 | 316 | 6 / 4 / 3 |
  | 30 | 1.643 | 11 / 7 / 5 |
  | 50 | 4.714 | 19 / 12 / 8 |
  | 70 | 9.761 | 28 / 17 / 12 |
  | 99 | 21.178 | 43 / 27 / 18 |

  ~455 vitórias até o nível 60 (fim da história) e ~1.000 até o 100 (pós-jogo).
- **Atributos:** a base da espécie vale no nível 1 e cada nível soma 8% dela (nível 5 = ×1,32; nível 100 = ×8,92). Ao subir de nível, **o dano já sofrido continua o mesmo** (o HP guardado sobe junto com o máximo; cheio continua cheio, desmaiada continua desmaiada).
- A inicial começa no **nível 5**; a capturada mantém o nível que tinha; selvagens têm faixa de nível fixa pela zona (§7.6).
- **HUD:** nível ("Nv 5") e barra de XP embaixo de cada espaço da equipe. *Falta:* aviso visual de subida de nível e o nível das selvagens na tela.
- **Fuga:** sair da área de combate.
- **Derrota:** criatura ativa desmaia → troca forçada; sem criaturas ou treinador desmaiado → derrota. **Penalidade:** perde **10%** do dinheiro (configurável) e volta ao último ponto de cura com a equipe restaurada.

### 5.7 Estágios e evolução

- Cada espécie tem um **estágio** (1, 2 ou 3). Evoluir leva ao seguinte e a criatura **cresce**. Algumas espécies são "estágio único" e já nascem num estágio alto.
- **Tamanho por estágio:** estágio 1 ≈ 28–32 px de altura (célula 48×48, menor que o treinador); estágio 2 ≈ 40 px (célula 64×64, da altura do treinador); estágio 3 ≈ 54 px (célula 64×64, bem maior). Colisor dos pés e barra de HP acompanham.
- **Níveis de evolução (referência):** 1 → 2 por volta do nível **16–20**; 2 → 3 por volta do **36–45**. Espécies de estágio único aparecem nos anéis que combinam com o estágio delas.
- A evolução em si (quando, para qual espécie, animação) entra junto com o learnset.

#### Espécies atuais

| Espécie | Estágio | Elemento | HP / Atk / Def / Vel / PE | Temperamento | Captura | Velocidade (tiles/s) |
|---|---|---|---|---|---|---|
| Brotim | 1 | Planta | 40 / 10 / 8 / 10 / 12 | Agressiva | 0,8 | 4,5 |
| Brasco | 1 | Fogo | 44 / 13 / 9 / 9 / 8 | Neutra | 0,6 | 4,25 |
| Pingelo | 1 | Gelo + Metal | 42 / 9 / 11 / 12 / 11 | Passiva | 0,7 | 4,0 |
| Cavatu | 2 | Terrestre | 55 / 12 / 15 / 6 / 5 | Neutra | 0,45 | 3,75 |
| Javolt | 2 | Elétrico | 50 / 14 / 10 / 13 / 10 | Agressiva | 0,5 | 4,6 |
| Tamandô | 3 (único) | Lutador | 70 / 19 / 14 / 10 / 7 | Agressiva | 0,3 | 4,75 |

- **Brotim:** bípede verde, barriga creme, cauda de cipó e **três folhas redondas flutuando sobre a cabeça**. Golpes: **Semente Disparada** (projétil especial, poder 6, cd 0,8 s, alcance 6, aviso 0,25 s interrompível) e **Folhada** (cone 80°, poder 9, cd 1,6 s, alcance 1,6, aviso 0,45 s não interrompível, empurrão 5).
- **Brasco:** lagartinho bípede preto com focinho, barriga e marcas vermelhas. **Fagulha** (projétil especial, poder 7, cd 1 s, alcance 5, aviso 0,3 s interrompível) e **Arranhão** (neutro, cone 70°, poder 10, cd 1,4 s, alcance 1,4, aviso 0,4 s não interrompível).
- **Pingelo:** pinguim com capacete de aço e crista de gelo, bico com ponta de aço. Linha: Pingelo → pinguim de visor e armadura → cavaleiro-imperador de aço e gelo. **Bolha Gelada** (projétil especial, poder 7, cd 1 s, alcance 5,5) e **Bico de Aço** (Metal, cone 35°, poder 9, cd 1 s, alcance 1,6, aviso 0,3 s interrompível).
- **Cavatu:** tatu escavador em pé, casco em faixas, lenço vermelho e pá de ferro. Linha: filhote com pazinha → Cavatu → tatu blindado com placas de pedra e pá-picareta. **Torrão** (projétil físico, poder 8, cd 1,2 s, alcance 5), **Pazada** (cone 90°, poder 12, cd 1,6 s, alcance 1,8, aviso 0,5 s não interrompível, empurrão 6, `wall_slam`) e **Pilar de Terra** (parede: aviso 0,45 s, até 4 tiles, poder 6, pilar de 4 s, cd 7 s). **Combo:** Pazada contra o pilar = explosão (poder 10, atordoa 1 s).
- **Javolt:** javali de pelo escuro eriçado com crina amarela e raios. Linha: leitão listrado → Javolt → javali de juba dourada com raios em volta. **Centelha** (projétil especial rápido, poder 8, cd 1 s, alcance 5,5, aviso 0,25 s), **Presada** (neutro, cone 50°, poder 11, cd 1,3 s, alcance 1,7, aviso 0,4 s não interrompível) e **Investida Elétrica** (aviso 0,35 s, até 4 tiles em 0,25 s, poder 10, físico, cd 4 s; a IA usa para fechar distância).
- **Tamandô:** tamanduá lutador de quimono branco, faixa na cabeça e cauda listrada. **Soco** (cone 20°, poder 7, alcance 1,5, aviso 0,2 s, cd 0,6 s), **Chute Duplo** (50°, poder 8, janela 1,2 s → **Chute Lançador**: poder 10, lança e atordoa 1 s; cd 2,5 s depois do combo), **Chicote de Língua** (25°, alcance 2,6, poder 8, **puxa**, cd 3 s), **Postura** (0,8 s, anula e contra-ataca com o **Contragolpe**: cone 90°, poder 12, empurrão 5; cd 4 s) e **Salto** (até 4 tiles, aviso/voo 0,6 s, raio 1,3, poder 12, cd 6 s).

> No protótipo o Tamandô tinha 5 golpes e uma tecla 5 temporária para teste. Na versão final, 4 equipados.

---

## 6. Captura

- Só o **treinador** captura (reforça o pilar "dois corpos").
- Fluxo: enfraquecer com a criatura → voltar ao treinador → mirar e lançar a esfera.
- A esfera é um **projétil físico em arco** (alcance 6, velocidade 9 tiles/s, altura do arco 1,25, raio de acerto 0,35): a posição anda no chão e o visual sobe numa parábola, com sombra no chão. Para em props (tronco, arbusto), **cai na água** (perdida) ou acerta a **primeira selvagem** no caminho.

```
chance = baseEspécie × (1 − HPatual/HPmáx)^1,5 × bônusEsfera × bônusStatus × fatorNível
fatorNível = clamp(1 − (nívelDaSelvagem − maiorNívelDaEquipe) / 20, 0,1, 1)
```

- **HP cheio = chance 0** (é preciso enfraquecer).
- **Fator de nível:** até o nível da equipe ×1; 10 acima ×0,5; 18 ou mais acima ×0,1. Usa o **maior nível da equipe** (trocar a ativa não burla).
- **Três balanços:** a criatura some dentro da esfera e ela balança até 3 vezes (0,6 s cada). Cada balanço passa com chance `chance^(1/3)`, então passar nos três tem exatamente a chance total.
  - **Capturou:** brilha verde, a criatura vai para a equipe (com o HP e o nível que tinha) e o corpo some.
  - **Escapou:** estoura vermelha e a criatura sai no mesmo lugar, **provocada contra o treinador**.
  - **Errou** (chão ou prop): a esfera some. **Água:** afunda.
- **Equipe cheia:** a captura vai para o armazenamento (o Rancho, §7.1.3).
- *Provisório:* esferas infinitas com cooldown de 1 s (quantidade com o inventário no M8); nome "Esfera" ainda provisório; som e partícula de verdade depois.
- Enquanto o treinador mira, a selvagem passa a atacá-lo (aggro de captura, §4.3).

---

## 7. Mundo

### 7.1 Estrutura

- Mundo contínuo, dividido em **regiões** e cada região em **chunks** carregados conforme o jogador se aproxima (§7.6).
- Transições entre regiões **contínuas** (sem fade). Cavernas podem usar um fade curto; **casas não trocam de cena** (§7.1.2).
- **Biomas:** Campo/Floresta, Praia, **Neve** (lago meio congelado: o gelo é chão caminhável, a água aberta bloqueia; deslizar fica para depois), **Deserto** (oásis, cânions, arcos, ruínas), **Vulcânico** (lava que bloqueia como a água), **Pântano** (água turva, palafitas), **Fábrica** e **Algodão Doce** (ainda sem arte). Cada bioma tem chão próprio, um líquido que bloqueia, props altos e objetos menores.
- **Tiles de bioma:** o chão do bioma é uma camada com bordas transparentes por cima da grama (ou do líquido do próprio bioma); o autotile escolhe a peça pelos vizinhos. A região não pode ter faixas de 1 tile de largura. Chão por cima de chão: a borda de quem está por cima mostra o chão do vizinho embaixo (sem buraco).
- **Estilo (decidido):** **só o estilo "realista"**: pintura em alta resolução gerada como referência e reduzida para pixel art com paleta limitada. Todo bioma novo entra a partir da sua referência nesse estilo.

### 7.1.1 Andares (planaltos e escadas)

> **Decidido:** áreas elevadas são **planaltos no mesmo mapa**, visíveis junto com o chão (vemos o topo e o paredão de frente). Não são camadas que escondem o andar de baixo.

- Cada personagem tem um **andar** (0 = chão, 1 = planalto, 2 = segundo planalto; o sistema aceita mais).
- O planalto é um chão elevado com aba e, abaixo da borda sul, um **paredão de pedra**. As bordas norte, leste e oeste mostram só a aba. Um andar superior precisa estar apoiado no inferior.
- **Colisão por andar:** no chão, o planalto inteiro (topo + paredão) bloqueia; em cima, a borda bloqueia (não dá para pular). Cada andar tem a sua camada de física e o personagem só colide com a do andar dele. A borda do andar de cima é recolhida para dentro da aba desenhada (0,55 tile no norte, 0,35 nos lados, 0,15 no paredão), senão os pés param em cima da aba e o personagem parece estar no chão.
- **Escadas** (2 tiles de largura) e **rampas naturais** (subida de grama entre laterais de pedra) são o único caminho entre andares. O andar muda pela posição: passou da metade, está no de cima (avaliado o tempo todo: dar meia-volta no meio não deixa no andar errado).
- **Selvagens não usam escadas** e **perdem o alvo na hora** quando ele muda de andar (subir é uma fuga segura).
- **Nada atravessa andares:** golpes, projéteis, a esfera e o aggro só valem no mesmo andar. Projéteis param na borda e no paredão.
- **Criatura do jogador:** seguindo (IA), muda de andar junto (reaparece ao lado). Controlada, usa as escadas. Soltar a coloca no andar do treinador.
- **Pontes** sobre água liberam a passagem embaixo do tablado e têm corrimões com colisão.
- Spawns têm um andar.

### 7.1.2 Cidades e construções

> **Decidido:** as construções ficam **no mesmo mundo** (estilo Tibia/PXG). Entrar numa casa **não troca de cena**: ao passar pela porta, **o telhado e a fachada somem** (fade de 0,25 s) e o interior aparece no mesmo lugar.

- **Vista de frente (3/4):** fachada embaixo com a **porta** na fileira de baixo; o telhado sobe acima da área ocupada. A porta não precisa cair no meio de um tile (o capacho fica centrado nela). Ao sul de uma rua, a porta dá para o sul.
- **Duas camadas por construção:**
  - **Exterior** (fachada + telhado): ordena por Y com os personagens; some com o jogador dentro.
  - **Interior** (piso, parede do fundo, paredes laterais finas e móveis): some do lado de fora, para nada aparecer pelas bordas do telhado.
- **Quem faz sumir:** o treinador ou a criatura do jogador dentro da área interna. Selvagens não. Corpo desativado lá dentro deixa de contar.
- **Colisão:** paredes bloqueiam (fundo 0,8 tile, laterais 0,34, frente 0,5 com a abertura da porta). Móveis são props com colisor na base.
- **Móveis em 4 direções:** frente, costas e os dois lados, para encostar em qualquer parede.
- Lojas, cura e NPCs seguem os sistemas normais do mundo; combate dentro de casa fica para decidir em playtest.
- **Borda da cidade:** a grama aparada vira uma faixa de grama mista e depois a grama do mundo, com bordas onduladas; arbustos e árvores começam esparsos e vão fechando. As saídas das ruas ficam livres.

### 7.1.3 Capital (cidade central)

> **Decidido:** a cidade do centro é a **capital** da ilha, o ponto de encontro do jogo inteiro. Plantas de referência: `Docs/capital_layout_v1.webp` (distribuição) e `Docs/capital_layout_v2.webp` (visual final).

- **~120 × 130 tiles**, muralha baixa com **4 portões** alinhados com as trilhas em estrela. Todo portão tem rua até a cidade (pedra no oeste e leste, asfalto no norte, **passarela de madeira sobre o lago** no sul) e uma trilha de terra para fora.
- **Bairros:**
  - **Norte:** campus do laboratório (observatório e estufa). **O tutorial acontece aqui e na praça**; o resto abre depois.
  - **Noroeste:** **Rancho das criaturas**.
  - **Nordeste:** oficina e **estação de trem** (ferrovia até a Fábrica).
  - **Centro:** praça com a **torre do relógio**, **centro de cura** e **mercado**.
  - **Oeste:** residencial com jardins, cercas e coreto.
  - **Leste:** rua do comércio com barracas e bazar coberto.
  - **Centro-sul:** **coliseu** a céu aberto (46 × 25 tiles) com **2 campos de batalha** lado a lado (~18 × 9,5 tiles cada, com mureta e entradas), o desafio da capital. Sem telhado: o interior aparece sempre.
  - **Sudeste:** **Guilda dos treinadores**.
  - **Sul:** **porto** no **lago do santuário** (a muralha sul encosta no lago); barcos para a ilhota do santuário e, com o transporte, um atalho para o Pântano.
- **Chão:** quarteirões de cima em tijolo, campus e bairro do mercado calçados, cais de pedra na margem do lago com vitórias-régias, cerejeiras misturadas às árvores, postes em volta das praças.
- **Rancho das criaturas:** as criaturas do armazenamento (7ª captura em diante) aparecem **andando no rancho**, cercadas, sem combate. Falar com o rancheiro troca uma do rancho por uma da equipe. Se houver muitas, só algumas ficam visíveis. Entra com o save (M8).
- **Guilda:** **quadro de missões** (capturar uma espécie, derrotar uma alfa, explorar um ponto, entregar um item), **ranking** que sobe com as missões e recompensas; NPCs de cada bioma com dicas e trocas. Depois do M8.
- **Escala humana:** porta com ~2 tiles de altura (o treinador tem ~1,3); o prédio cresce em largura e andares, não em porta. Casas 7 × 4, sobrados 10 × 7, centro de cura e mercado 18 × 7, laboratório 21 × 7, guilda 18 × 8, estação 22 × 6, torre do relógio 4 × 3 (~19 de altura).

### 7.2 Spawns

- `SpawnZone` = área (polígono ou retângulo) + tabela de espécies com peso + faixa de nível + horário do dia + limite de população + tempo de respawn.
- A faixa de nível segue o **anel** da zona (§7.6) e é fixa: as selvagens não escalam com o jogador.
- Spawns só acontecem **fora da câmera**; criaturas longe demais do jogador são despawnadas (pooling).
- Raras só em condições (noite, chuva, perto de água).
- Cada entrada da tabela tem `spawn_mode` (`Visible`, `HiddenInGrass`, `Both`) e `hidden_weight` (§7.5).
- *Placeholder do protótipo:* um ponto fixo que recria a selvagem 6 s depois de sumir, com nível sorteado numa faixa (padrão 3–6).

### 7.3 Interação com o mundo

- Objetos interativos implementam uma interface comum de interação (tecla E).
- Obstáculos que exigem criaturas específicas (cortar arbusto, quebrar pedra, atravessar água): gancho de progressão estilo metroidvania leve. Abrem atalhos e áreas secretas, **nunca** a entrada principal de um bioma.

### 7.4 Ciclo dia/noite e clima (pós-MVP)

- Luzes 2D (`PointLight2D`, `CanvasModulate`). Clima afeta spawns e alguns golpes.

### 7.5 Encontros híbridos (visíveis + escondidas no mato alto) — M7

> **Decidido:** criaturas **visíveis no mundo** são a base, mais criaturas **escondidas no mato alto**. **Não existe encontro aleatório por passo.**

- **Áreas abertas:** spawn visível com a IA normal.
- **Mato alto:** parte das criaturas spawna `Hidden`: invisível, sem colisão com o jogador, sem perceber ninguém; o tile onde está **balança** periodicamente (não revela a espécie).
- **Revelar:** o treinador ou a criatura do jogador entra no mesmo tile ou num raio curto, ou uma **pedrinha** arremessada pelo treinador (mesmo arremesso em arco da esfera, outros dados) cai no mato.
- **Reação:** `Passiva` foge, `Neutra` fica alerta, `Agressiva` faz **emboscada** (salta no alvo mais próximo e inicia o combate).
- **Espécies raras** podem ser "só escondidas".
- **Feedback:** texto flutuante no mapa ("Apareceu!", "Desmaiou!", "Errou!", "Capturou!", "Super efetivo!", "Subiu de nível!"). **Nunca** janela modal.
- **Arquitetura:**
  1. `Hidden` é **um estado a mais na IA da selvagem** (Hidden → Revealed → fluxo normal), não uma classe separada.
  2. O mato alto é uma área com detecção (`Area2D`) que **emite um sinal** (entrada, impacto de pedrinha); quem reage é a criatura. O mato não conhece a IA.
  3. O balanço é visual puro e escuta o sinal de "farfalhar". Nada de gameplay na animação ou no shader.
  4. `spawn_mode` e `hidden_weight` vêm dos dados, nunca do código.
  5. A pedrinha reutiliza o projétil em arco da esfera.
  6. Escondidas contam no limite de população e usam o mesmo pooling.
  7. **Testes obrigatórios:** escolha de espécie por `spawn_mode`/peso e transição Hidden → Revealed por temperamento.
- **Fora de escopo:** encontro aleatório por passos, repelente, tela de transição de batalha.

### 7.6 Mapa do mundo e progressão

> **Decidido:** uma ilha contínua com a **capital no centro** e os biomas em volta (referências: `Docs/world_map_reference_v3.webp` e o rascunho em blocos `Docs/world_map_blockout_v4.png`). A capital é o **tutorial**; depois dele o jogador anda livremente. A dificuldade cresce com a **distância da capital**, não com a direção.

- **Disposição:**
  - **Sul:** lago grande com ilhota e **santuário** (arco de pedra), encostado na muralha sul da capital (porto).
  - **Noroeste:** **Neve** (picos, cachoeiras, lagos congelados); os rios nascem nela e descem pela Floresta até o mar.
  - **Norte:** **Vulcânico** (rios de lava; faixa de cinza e árvores mortas antes dos campos).
  - **Nordeste:** **Fábrica** (galpões, chaminés, ferrovia até as minas do deserto, lagos de óleo, rio tóxico verde até a costa leste).
  - **Oeste:** **Floresta** (mais clara perto da cidade; árvore gigante e ruínas no fundo).
  - **Costa oeste:** **Praia** (farol, vila de pescadores, cais, passarela até o Pântano).
  - **Leste:** **Deserto** (cânions em terraços, arcos, oásis, pirâmide), descendo até o mar.
  - **Sudoeste:** **Pântano** (palafitas, mangue, rios).
  - **Canto sudeste:** **Algodão Doce** (fim de jogo, atrás de um portão de cristal de açúcar; castelo no fundo).
  - Cada bioma tem uma **cidade própria** (cidade de gelo com termas, cidade na copa de uma árvore, cidade-oásis, vila de palafitas, cidade-forja na cratera; nomes em aberto). Pontes ou passagens marcam a entrada de cada bioma.
- **Anéis de nível** (cada bioma é uma fatia que atravessa todos):

| Anel | Onde | Nível | Papel |
|---|---|---|---|
| 0 | Capital e campos em volta (até 105 tiles; 110 no norte-sul) | 2–8 | Tutorial: primeira captura, troca de controle, combate |
| 1 | Logo depois da ponte de cada bioma (105–180) | 8–20 | Escolha livre do primeiro bioma |
| 2 | Interior do bioma, com a cidade dele (160–280) | 20–40 | Base segura e primeiro desafio |
| 3 | Fundo do bioma: masmorras e torres (280–420) | 40–65 | Exploração pesada |
| 4 | Núcleo: cratera, picos, cânion, copa da árvore, abismo (420–550; até ~650 no norte-sul) | 65–90 | Meio e fim de jogo |
| — | Raras, lendárias, eventos | 85–100 | Pós-jogo |

- As faixas **se encostam** (não há parede de nível).
- **Campos da capital:** criaturas fracas de cada bioma vizinho, para montar um time variado antes de escolher a direção.
- **Cidade-forja do vulcão** mais funda (anel 3/4): destino natural do fim do jogo.
- **Ligações entre biomas vizinhos** nos anéis 2–3, para circular sem voltar à capital.
- **Habitat:** Floresta = Planta, Neve = Gelo, Vulcânico = Fogo, Deserto = Terrestre, Fábrica = Metal e Elétrico; os outros com elementos que ainda vão entrar.
- **Tamanho:** ~**900 × 1.300 tiles** (retrato), medido em tempo de caminhada:

| Trajeto | Distância | Andando | Correndo |
|---|---|---|---|
| Capital → entrada de um bioma | ~120 tiles | 30 s | 18 s |
| Capital → cidade do bioma | ~220 tiles | 55 s | 35 s |
| Capital → núcleo do bioma | ~450 tiles | ~2 min | ~70 s |
| Atravessar o mapa | ~1.300 tiles | ~5,5 min | ~3,5 min |

- **Densidade:** um ponto de interesse a cada 20–30 s de caminhada (80–120 tiles).
- **Transporte** (depois): montaria, nadar e voar com criaturas.
- **Construção por anéis:** primeiro os anéis 0–1 (~320 × 320 tiles) jogáveis, depois para fora.
- **Chunks:** blocos de **128 × 128 tiles**, cada um numa cena, carregados em volta do jogador.

**Regras de liberdade:**

1. Selvagens com **nível fixo por zona**.
2. **Desafios das cidades escalam pela ordem** em que são vencidos (~15, ~25, ~35...). Só os chefes escalam.
3. **Perigo visível, não parede:** criaturas **alfa** (maiores, bem acima do nível da zona) aparecem visíveis, também nos anéis baixos. Placas e NPCs avisam.
4. **Captura difícil acima do seu nível** (§6).
5. **Habilidades do mundo** abrem atalhos, nunca a entrada principal de um bioma.

---

## 8. Direção de arte

- **Perspectiva:** top-down 3/4 (topo e frente dos objetos).
- **Tile:** **32×32 px** (decidido). Nunca misturar tamanhos de tile.
- **Resolução de referência:** **640×360** (20×11 tiles visíveis), escalando só em múltiplos inteiros (1280×720, 1920×1080, 2560×1440). O jogo renderiza exatamente em 640×360 e depois amplia: sem isso aparecem linhas finas entre as fileiras de tiles com a câmera entre pixels.
- **Sprites:** filtro **Nearest**, sem compressão com perda, origem nos pés (base no meio) para a ordenação.
- **Ordenação por Y:** quem está mais abaixo na tela fica na frente. Árvores com origem no tronco. Props com colisor só na base (tronco ~10–14 px, arbusto ~24×10 px); objeto que o personagem contorna ou passa por trás vira cena com origem na base, nunca tile.
- **Estilo:** **realista** (referência pintada reduzida a pixel art com paleta limitada, sem pontilhado). Contorno escuro (não preto puro), luz de cima à esquerda em tudo.
- **Paleta:** verdes profundos, marrons quentes de terra, areia clara, água turquesa saturada. Paleta fixa de 32–48 cores por conjunto.
- **Chão base:** grama baixa e uniforme (lê bem os telegrafos e repete sem padrão visível), com variações de trevo e florzinhas espalhadas em ~10–15% das células. Gerar base e variações **juntas**, no mesmo tom, para não aparecer borda entre tiles. Mato alto (§7.5) bem diferente da base. Por bioma: grama de floresta mais escura, seca na transição do deserto, com musgo no pântano.
- **Água:** tile animado + ondulação simples; vitórias-régias e espuma na borda como decoração.
- **Origem da arte:** à mão + assets gratuitos + referências geradas por IA. Recolorir externos para a paleta; registrar tudo em `CREDITS.md`. Ferramenta: Aseprite, LibreSprite ou Pixelorama.
- **Personagens:** treinador com corpo de ~32×44 px numa célula de **48×48** (a folga cabe a jaqueta na corrida e a bola da rolagem); criaturas em células de 48×48 (estágio 1) ou 64×64 (estágios 2 e 3).
- **8 direções** (decidido). Desenha-se 5 (S, SE, E, NE, N) e as da esquerda saem espelhadas.
- **Layout das sheets:** **linhas = direções** (S, SE, E, NE, N); **colunas = frames**, com clipes definidos por coluna inicial, número de frames, fps e loop. Pés 2 px acima da base da célula.
  - **Treinador** (22 colunas): `idle` 4 (2,5 fps), `walk` 6 (4 fps), `run` 6 (12 fps), `roll` 6 (15 fps, sem loop, 0,4 s).
  - **Criaturas:** `idle` 4 (2,5 fps), `walk` 6 (8 fps) e os clipes de ação: um por golpe, `hurt` 3 (10 fps) e `faint` 5 (10 fps, segura o último frame).
  - O fps do clipe de golpe é escolhido para o frame do "disparo" cair no fim do telegrafo.
- **Treinador em camadas (customização):** `Body`, `Shoes`, `Pants`, `Shirt`, `Jacket`, `Backpack`, `Hair`, `Accessory`, todas com o mesmo layout de sheet. Um script aplica **o mesmo frame** (linha = direção, coluna = frame) a todas as camadas e liga o espelho para W/SW/NW, então elas ficam sincronizadas por construção. Customizar = trocar a sheet de uma camada. Hoje o treinador é uma peça só no `Body`; para customizar de verdade será preciso um corpo base sem roupa nas mesmas poses.
- **Animações de ação:** enquanto um clipe de ação toca, andar/parar não troca a animação; ao terminar, volta ao idle. Golpe interrompido corta o clipe. Dano toca `hurt` (menos durante um golpe ou desmaiado), mais um piscar vermelho. Quem não tem `faint` encolhe ao desmaiar.
- **Efeitos de golpe:** sequências de sprites (loop ou uma vez, que se destroem ao acabar), desenhadas **apontando para a direita** (o jogo gira). Efeito de golpe sem elemento em tons neutros.
- **Selvagens sem tom de cor:** cada espécie tem a própria arte; a do jogador se distingue pela coleira e por estar perto do treinador.

---

## 9. Arquitetura técnica (Godot)

### 9.1 Stack

- **Godot 4.4+**, renderizador **Compatibility** ou **Forward+** (2D).
- **GDScript** com tipagem estática (`class_name`, tipos nas variáveis e funções). C# é opção, mas GDScript é o padrão do projeto.
- **InputMap** do projeto com ações nomeadas (nunca teclas no código).
- **Camera2D** com suavização de posição para seguir o corpo controlado.
- **TileMapLayer** (uma camada por nó) + **TileSet com terrain sets** (autotile "corners and sides" = 47 formas) para chão, grama, água e bordas.
- **Testes:** **GUT** ou **gdUnit4** (testes de lógica pura e de integração em cena).
- **Save:** JSON em `user://`.
- **Git + LFS** para binários (imagens, áudio, `.aseprite`).

### 9.2 Configuração do projeto (pixel perfect)

- `display/window/size/viewport_width = 640`, `viewport_height = 360`.
- `display/window/stretch/mode = viewport`, `aspect = keep`, `scale_mode = integer`.
- `rendering/textures/canvas_textures/default_texture_filter = Nearest`.
- `rendering/2d/snap/snap_2d_transforms_to_pixel = true` e `snap_2d_vertices_to_pixel = true`.
- Importar sprites sem mipmaps e sem compressão com perda.
- **Unidades:** 1 tile = 32 px. As velocidades do documento estão em tiles/s; no código, multiplicar por 32.

### 9.3 Princípios

1. **Dados em Resources, lógica pura em classes sem nó.** Dano, captura, XP, elementos, corações, troca de equipe, estados da IA, coleira, follow, rolagem: classes `RefCounted` (ou funções estáticas) testáveis sem cena.
2. **Composição sobre herança.** Uma criatura é um `CharacterBody2D` com nós-componente filhos (`Health`, `Mover`, `MoveCaster`, `BrainController`, `HitFeedback`...), não uma hierarquia profunda.
3. **Mesmo corpo, cérebros diferentes.** A criatura do jogador e a selvagem usam a mesma cena e trocam só a fonte de comandos:
   - `PlayerBrain` (lê o InputMap; também é o cérebro do treinador),
   - `WildAIBrain` (Vagar → Alerta → Perseguir → Atacar → Fugir → Voltar para casa; `Hidden` no M7),
   - `FollowBrain` (segue o treinador),
   - `DefensiveBrain` (criatura do jogador com o controle no treinador: só esquiva).
   - Interface comum: `on_activated()`, `on_deactivated()`, `tick_move(delta) -> Vector2`, `tick_actions(delta)`. O `BrainController` guarda o ativo (null = parado) e passa o input ao `Mover`; zera o movimento durante o telegrafo e com o corpo desmaiado. **Trocar de modo = trocar o cérebro. É a decisão de arquitetura mais importante do projeto.**
4. **Sinais para desacoplar.** UI, áudio, câmera e animação escutam sinais (`damaged`, `fainted`, `control_switched`, `creature_released`, `captured`...); a lógica de combate nunca os chama.
5. **Tudo que golpes acertam implementa a mesma interface** (`faction`, `is_defeated`, `receive_hit(hit, attacker_faction)`): `Health` das criaturas e os corações do treinador. Quem puxa o aggro expõe `draws_aggro`.
6. **Sem singletons espalhados.** No máximo **um autoload** (`Services`), se precisar.

### 9.4 Física e camadas

| Camada | Uso |
|---|---|
| 1 `world` | Props, paredes, pilares (bloqueia movimento e projéteis) |
| 2 `water` | Água e lava (bloqueia movimento, **não** projéteis; é onde a esfera "cai na água") |
| 3 `trainer` | Corpo do treinador |
| 4 `creature` | Corpos das criaturas |
| 5–7 `elevation_0..2` | Bloqueio de cada andar; o corpo só tem na máscara a do seu andar |
| 8 `trigger` | Escadas, mato alto, interior de casas |

- Treinador × criatura não colidem (a criatura não empurra o treinador).
- Colisores dos personagens só nos pés (cápsula horizontal: treinador 16×8 px, criaturas 14×6 a 32×10).
- Consultas de golpe, projétil e IA usam `PhysicsDirectSpaceState2D` (`intersect_shape`, `intersect_ray`) filtrando pelo andar.
- Ponto livre para soltar ou reaparecer: círculo livre no ponto + raio fino desde a origem (§4.2), com máscara sem `trainer` e `creature`.

### 9.5 Estrutura de pastas

```
res://
  art/            (sprites, tiles, palettes, vfx, CREDITS.md)
  audio/
  data/           (Resources .tres: species, moves, elements, items, spawn_tables, movement)
  scenes/
    world/        (chunks: chunk_000_000.tscn, ...)
    characters/   (trainer.tscn, creature.tscn)
    combat/       (projéteis, efeitos, pilar)
    ui/
  scripts/
    core/         (math puro: movimento, follow, coleira, direções, menu radial, rolagem)
    data/         (classes de Resource)
    combat/       (dano, golpes, projéteis, captura, elementos)
    creatures/    (componentes, brains, IA)
    trainer/      (controle, troca, arremesso, corações, equipe)
    world/        (spawns, chunks, andares, construções, mato alto)
    ui/
    save/
  tests/
    unit/         (lógica pura)
    integration/  (cenas)
```

Dependências só "para baixo": UI conhece combate e treinador, nunca o contrário; combate não conhece animação nem UI.

### 9.6 Modelos de dados principais

```gdscript
# Definição estática (Resource .tres)
class_name SpeciesData extends Resource
  id, display_name, scene, base_stats, temperament, element, secondary_element,
  moves[1..4], capture_rate, icon, xp_yield, stage, movement, sheet_layout,
  learnset (depois), evolutions (depois)

class_name MoveData extends Resource
  id, display_name, category, element, power, cooldown, shape, range,
  cone_angle, projectile_scene, projectile_speed, projectile_radius,
  telegraph_time, interruptible, knockback, pull, stun_duration, launch,
  follow_up, follow_up_window, area_radius, dash_duration,
  summon_scene, summon_duration, summon_min_distance, wall_slam, wall_slam_window,
  animation_clip, cast_effect, cast_effect_distance, cast_effect_height, cast_effect_rotates

class_name ElementData extends Resource      # id, display_name, color
class_name ElementChart extends Resource     # rules[attacker, defender, multiplier], same_element_bonus
class_name ThrowableData extends Resource    # scene, max_range, speed, arc_height, hit_radius, cooldown, capture_bonus
class_name MovementProfile extends Resource  # max_speed, acceleration, deceleration, run_speed, dash_*

# Instância em runtime (serializável no save)
class_name CreatureInstance extends RefCounted
  species_id, nickname, level, xp, current_hp (-1 = cheio, 0 = desmaiada),
  known_move_ids[4], status, unique_id
```

### 9.7 Save

- JSON em `user://`, com `save_version` para migrações.
- Salvar **apenas IDs** (de espécie, golpe, item), nunca referências a recursos.

---

## 10. Roadmap (milestones)

Cada milestone termina com algo **jogável**. Não avançar sem fechar o anterior. As milestones M0–M6 já foram feitas e testadas no protótipo em Unity; na migração, o objetivo é refazê-las com as regras deste documento.

| # | Milestone | Entregável jogável | No protótipo Unity |
|---|---|---|---|
| M0 | Setup | Projeto Godot 2D, InputMap, câmera, pixel perfect 640×360, pastas, testes, CLAUDE.md, git + LFS | Feito |
| M1 | Treinador no mundo | Mapa de teste com tiles, colisão (água e props), ordenação por Y, treinador andando/correndo/rolando com animação em 8 direções, limites do mapa e câmera presa neles | Feito (limites e câmera presa ficaram pendentes) |
| M2 | Criatura seguindo | `FollowBrain`, soltar (toque em Q) e recolher (segurar Q) | Feito |
| M3 | Troca de controle | `PlayerBrain` na criatura, câmera troca de alvo, coleira com linha | Feito |
| M4 | Combate mínimo | Selvagem com IA por temperamento, 2 golpes (projétil e cone), telegrafo, HP, dano, desmaio, IA defensiva | Feito |
| M5 | Captura | Esfera em arco, fórmula com 3 balanços, equipe com HUD, corações do treinador, aggro de captura, troca de criatura (menu radial) | Feito |
| M6 | Conteúdo base | 6 espécies, golpes com mecânicas (§5.3), elementos com tipagem dupla, XP e nível até 100 | Feito |
| M7 | Mundo vivo | `SpawnZone` por anel, despawn/pooling, texto flutuante, encontros híbridos (mato alto, pedrinha), andares com escadas, construções no mesmo mundo, 2 regiões conectadas, chunks | Andares, construções e capital feitos à parte; o resto não |
| M8 | Meta | Centro de cura, inventário, derrota de verdade, Rancho, save/load | — |
| M9 | Polimento | Juice (hitstop, screenshake, partículas), áudio, menus | — |

**Vertical slice = M0 a M6.** Evolução, chefes, multiplayer e dia/noite só depois.

---

## 11. Fora de escopo (por enquanto)

- Multiplayer / MMO. A arquitetura de cérebros facilita no futuro, mas não projetar para isso agora.
- Mundo procedural.
- Mais de 30 espécies antes do vertical slice estar divertido.
- Breeding, habilidades passivas complexas, natures.
- Encontro aleatório por passos, repelente e tela de transição de batalha.

---

## 12. Decisões

### Decididas

- [x] Tile **32 px**; resolução 640×360 em escala inteira.
- [x] Estilo **realista** (referência pintada reduzida a pixel art).
- [x] **8 direções**, treinador em camadas com o mesmo layout de sheet.
- [x] Controle: **um personagem por vez**; mira com o **mouse**, PC primeiro.
- [x] Treinador: andar 4, correr 6,5 (Shift), rolar 0,4 s com recarga de 5 s (Espaço), sem invulnerabilidade.
- [x] Coleira de **10 tiles** que trava o movimento.
- [x] Criatura sob IA com o controle no treinador: **só se defende**.
- [x] Golpes: **só cooldown**; vermelho = interrompível, amarelo = não.
- [x] Dano com **fator de nível**; nível máximo **100**; curva de XP mais íngreme depois do 30.
- [x] Elementos como dados, regras de um sentido, **tipagem dupla**; bônus de mesmo elemento desligado.
- [x] Captura com **3 balanços**, HP cheio = 0, **fator de nível**; só o treinador captura.
- [x] Treinador com **3 corações** e aggro de captura (validar em playtest).
- [x] Equipe de **6**, **1 em campo**, troca por menu radial com recarga global de 3 s.
- [x] Penalidade de derrota: **perde 10% do dinheiro**.
- [x] Mundo: **planaltos com escadas** no mesmo mapa; nada atravessa andares; selvagens não trocam de andar.
- [x] Construções **no mesmo mundo** (telhado some ao entrar).
- [x] **Capital** no centro (~120 × 130, muralha, 4 portões, coliseu, Rancho, Guilda, porto).
- [x] Encontros **híbridos**, sem encontro por passo.
- [x] Mapa **~900 × 1.300 tiles**, anéis de nível pela distância, chunks de 128 × 128.

### Pendentes

- [ ] Nome do jogo e nome das "esferas" de captura (originais).
- [ ] Nomes próprios para os elementos (ver o aviso do §1).
- [ ] Elemento Água (Praia) e elemento do Algodão Doce.
- [ ] Nomes das cidades de cada bioma.
- [ ] Combate dentro de casas.
- [ ] Área de combate dinâmica e música de combate (§5.1).
- [ ] Deslizar no gelo (se o playtest pedir).

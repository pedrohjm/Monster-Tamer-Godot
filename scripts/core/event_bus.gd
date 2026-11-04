extends Node
## Autoload `EventBus`: só sinais globais, sem estado (GAME_DESIGN §9.2, princípio 4).
##
## Use sinais locais do componente quando o ouvinte já tem a referência ao emissor.
## Aqui entram só eventos que atravessam sistemas (ex.: câmera e HUD reagindo à troca
## de controle). Cada sinal é declarado junto com o sistema que o emite, não antes.

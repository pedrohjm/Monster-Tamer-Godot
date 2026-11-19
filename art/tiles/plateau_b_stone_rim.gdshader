shader_type canvas_item;
render_mode unshaded;

// Usa a propria pedra frontal do estilo B nas margens norte e laterais.
// O topo de grama e o paredao frontal continuam nas suas camadas originais.
uniform sampler2D grass_atlas : filter_nearest, repeat_disable;
const float TILE = 32.0;
const int WIDTH = 7;
// Na quina com o paredao sul, a faixa lateral afina nesses ultimos px ate encontrar o
// paredao (senao sobra um toco de pedra ao lado dele).
const float TAPER = 6.0;

bool grass_at(vec2 p, vec2 origin) {
	if (p.x < 0.0 || p.y < 0.0 || p.x >= TILE || p.y >= TILE) {
		return false;
	}
	vec4 c = texture(grass_atlas, (origin + p + vec2(0.5)) / vec2(128.0));
	return c.a > 0.5 && c.r <= c.g + 5.0 / 255.0;
}

// Largura da faixa lateral na linha y, junto a coluna de grama gx.
float side_width(float gx, float y, vec2 origin) {
	float bottom = -1.0;
	for (int k = 31; k >= 0; k--) {
		if (grass_at(vec2(gx, float(k)), origin)) {
			bottom = float(k);
			break;
		}
	}
	if (bottom < 0.0 || bottom >= TILE - 2.0) {
		return float(WIDTH);
	}
	return float(WIDTH) * clamp((bottom - y + 1.0) / TAPER, 0.0, 1.0);
}

void fragment() {
	vec2 pixel = floor(UV * vec2(128.0));
	vec2 origin = floor(pixel / TILE) * TILE;
	vec2 p = pixel - origin;
	vec4 base = texture(grass_atlas, (pixel + vec2(0.5)) / vec2(128.0));
	vec4 rock = vec4(0.0);
	if (base.a < 0.01) {
		float distance_to_grass = 99.0;
		int direction = -1;
		for (int k = 1; k <= WIDTH; k++) {
			float d = float(k);
			if (d < distance_to_grass && grass_at(p + vec2(0.0, d), origin)) {
				distance_to_grass = d;
				direction = 0;
			}
			if (d < distance_to_grass && grass_at(p + vec2(d, 0.0), origin)
					&& d <= side_width(p.x + d, p.y, origin)) {
				distance_to_grass = d;
				direction = 1;
			}
			if (d < distance_to_grass && grass_at(p - vec2(d, 0.0), origin)
					&& d <= side_width(p.x - d, p.y, origin)) {
				distance_to_grass = d;
				direction = 2;
			}
		}
		if (direction >= 0) {
			// Tile frontal reto (1,2): as linhas 22..28 sao integralmente pedra.
			// Gira a mesma faixa nas laterais para manter as facetas e as frestas.
			float along = direction == 0 ? p.x : p.y;
			vec2 source_pixel = vec2(TILE + along, 2.0 * TILE + 29.0 - distance_to_grass);
			rock = texture(grass_atlas, (source_pixel + vec2(0.5)) / vec2(128.0));
			if (direction == 2) {
				rock.rgb *= 0.88;
			}
		}
	}
	COLOR = rock;
}

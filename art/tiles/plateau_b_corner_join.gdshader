shader_type canvas_item;
render_mode unshaded;

// Liga a margem de pedra ao paredao usando a textura original da propria montanha.
uniform sampler2D grass_atlas : filter_nearest, repeat_disable;

bool stone(vec4 c) {
	return c.a > 0.5 && c.r > c.g + 5.0 / 255.0;
}

vec4 surface_at(vec2 p, vec2 face_origin, vec2 top_origin, sampler2D face_texture) {
	if (p.x < 0.0 || p.x >= 32.0 || p.y < 0.0 || p.y >= 64.0) {
		return vec4(0.0);
	}
	vec4 c = texture(face_texture, (face_origin + p + vec2(0.5)) / vec2(128.0, 256.0));
	if (p.y < 32.0 && c.a < 0.01) {
		c = texture(grass_atlas, (top_origin + p + vec2(0.5)) / vec2(128.0));
	}
	return c;
}

void fragment() {
	vec2 pixel = floor(UV * vec2(128.0, 256.0));
	vec2 face_origin = floor(pixel / vec2(32.0, 64.0)) * vec2(32.0, 64.0);
	vec2 top_origin = face_origin / vec2(1.0, 2.0);
	vec2 p = pixel - face_origin;
	vec4 original = texture(TEXTURE, UV);
	vec4 result = original;
	vec4 surface = surface_at(p, face_origin, top_origin, TEXTURE);
	if (surface.a < 0.01) {
		// A lateral abre na borda, abraça o canto e afina ate encontrar a base.
		float width = 7.0 * (1.0 - smoothstep(23.0, 49.0, p.y));
		float nearest = 99.0;
		int side = 0;
		for (int k = 1; k <= 7; k++) {
			float d = float(k);
			vec4 west = surface_at(p - vec2(d, 0.0), face_origin, top_origin, TEXTURE);
			vec4 east = surface_at(p + vec2(d, 0.0), face_origin, top_origin, TEXTURE);
			if (d <= width && d < nearest && stone(west)) {
				nearest = d;
				side = 1;
			}
			if (d <= width && d < nearest && stone(east)) {
				nearest = d;
				side = -1;
			}
		}
		if (side != 0) {
			float along = mod(p.y, 32.0);
			vec2 source_pixel = vec2(32.0 + along, 64.0 + 29.0 - nearest);
			result = texture(grass_atlas, (source_pixel + vec2(0.5)) / vec2(128.0));
			if (side == 1) {
				result.rgb *= 0.88;
			}
		}
	}
	COLOR = result;
}

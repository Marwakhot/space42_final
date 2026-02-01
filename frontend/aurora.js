// Aurora.js - WebGL Aurora Background using OGL
// Converted from React component to vanilla JS

const VERT = `#version 300 es
in vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const FRAG = `#version 300 es
precision highp float;

uniform float uTime;
uniform float uAmplitude;
uniform vec3 uColorStops[3];
uniform vec2 uResolution;
uniform float uBlend;
uniform float uSpeed;

out vec4 fragColor;

vec3 permute(vec3 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v){
  const vec4 C = vec4(
      0.211324865405187, 0.366025403784439,
      -0.577350269189626, 0.024390243902439
  );
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);

  vec3 p = permute(
      permute(i.y + vec3(0.0, i1.y, 1.0))
    + i.x + vec3(0.0, i1.x, 1.0)
  );

  vec3 m = max(
      0.5 - vec3(
          dot(x0, x0),
          dot(x12.xy, x12.xy),
          dot(x12.zw, x12.zw)
      ), 
      0.0
  );
  m = m * m;
  m = m * m;

  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);

  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

struct ColorStop {
  vec3 color;
  float position;
};

#define COLOR_RAMP(colors, factor, finalColor) {              \
  int index = 0;                                            \
  for (int i = 0; i < 2; i++) {                               \
     ColorStop currentColor = colors[i];                    \
     bool isInBetween = currentColor.position <= factor;    \
     index = int(mix(float(index), float(i), float(isInBetween))); \
  }                                                         \
  ColorStop currentColor = colors[index];                   \
  ColorStop nextColor = colors[index + 1];                  \
  float range = nextColor.position - currentColor.position; \
  float lerpFactor = (factor - currentColor.position) / range; \
  finalColor = mix(currentColor.color, nextColor.color, lerpFactor); \
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  
  ColorStop colors[3];
  colors[0] = ColorStop(uColorStops[0], 0.0);
  colors[1] = ColorStop(uColorStops[1], 0.5);
  colors[2] = ColorStop(uColorStops[2], 1.0);
  
  vec3 rampColor;
  COLOR_RAMP(colors, uv.x, rampColor);
  
  float height = snoise(vec2(uv.x * 2.0 + uTime * 0.1 * uSpeed, uTime * 0.25 * uSpeed)) * 0.5 * uAmplitude;
  height = exp(height);
  height = (uv.y * 2.0 - height + 0.2);
  float intensity = 0.6 * height;
  
  float midPoint = 0.20;
  float auroraAlpha = smoothstep(midPoint - uBlend * 0.5, midPoint + uBlend * 0.5, intensity);
  
  vec3 auroraColor = intensity * rampColor;
  
  fragColor = vec4(auroraColor * auroraAlpha, auroraAlpha);
}
`;

// Simple OGL-compatible classes
class Renderer {
    constructor(options = {}) {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2', options);
        if (!gl) {
            console.error('WebGL2 not supported');
            return;
        }
        this.gl = gl;
        this.canvas = canvas;
    }

    setSize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
        this.gl.viewport(0, 0, width, height);
    }

    render({ scene }) {
        this.gl.clear(this.gl.COLOR_BUFFER_BIT);
        scene.draw();
    }
}

class Program {
    constructor(gl, { vertex, fragment, uniforms }) {
        this.gl = gl;
        this.uniforms = uniforms || {};

        const vertexShader = this.createShader(gl.VERTEX_SHADER, vertex);
        const fragmentShader = this.createShader(gl.FRAGMENT_SHADER, fragment);

        this.program = gl.createProgram();
        gl.attachShader(this.program, vertexShader);
        gl.attachShader(this.program, fragmentShader);
        gl.linkProgram(this.program);

        if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
            console.error('Program link error:', gl.getProgramInfoLog(this.program));
        }
    }

    createShader(type, source) {
        const shader = this.gl.createShader(type);
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);

        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            console.error('Shader compile error:', this.gl.getShaderInfoLog(shader));
        }
        return shader;
    }

    use() {
        this.gl.useProgram(this.program);

        for (const [name, uniform] of Object.entries(this.uniforms)) {
            const location = this.gl.getUniformLocation(this.program, name);
            if (location === null) continue;

            const value = uniform.value;
            if (typeof value === 'number') {
                this.gl.uniform1f(location, value);
            } else if (value.length === 2) {
                this.gl.uniform2fv(location, value);
            } else if (value.length === 3) {
                this.gl.uniform3fv(location, value);
            } else if (value.length === 9) {
                this.gl.uniform3fv(location, value);
            }
        }
    }
}

class Triangle {
    constructor(gl) {
        this.gl = gl;
        const vertices = new Float32Array([
            -1, -1,
            3, -1,
            -1, 3
        ]);

        this.buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    }
}

class Mesh {
    constructor(gl, { geometry, program }) {
        this.gl = gl;
        this.geometry = geometry;
        this.program = program;
    }

    draw() {
        const gl = this.gl;
        this.program.use();

        gl.bindBuffer(gl.ARRAY_BUFFER, this.geometry.buffer);

        const posLoc = gl.getAttribLocation(this.program.program, 'position');

        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

        gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
}

class Color {
    constructor(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        this.r = parseInt(result[1], 16) / 255;
        this.g = parseInt(result[2], 16) / 255;
        this.b = parseInt(result[3], 16) / 255;
    }
}

// Aurora class
class Aurora {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            colorStops: options.colorStops || ['#5227FF', '#7cff67', '#5227FF'],
            amplitude: options.amplitude !== undefined ? options.amplitude : 1.0,
            blend: options.blend !== undefined ? options.blend : 0.5,
            speed: options.speed !== undefined ? options.speed : 1.0
        };

        this.init();
    }

    init() {
        const renderer = new Renderer({
            alpha: true,
            premultipliedAlpha: true,
            antialias: true
        });

        if (!renderer.gl) return;

        const gl = renderer.gl;
        this.gl = gl;
        this.renderer = renderer;

        gl.clearColor(0, 0, 0, 0);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.canvas.style.backgroundColor = 'transparent';

        this.resize();
        window.addEventListener('resize', () => this.resize());

        const geometry = new Triangle(gl);

        const colorStopsArray = this.options.colorStops.map(hex => {
            const c = new Color(hex);
            return [c.r, c.g, c.b];
        }).flat();

        this.program = new Program(gl, {
            vertex: VERT,
            fragment: FRAG,
            uniforms: {
                uTime: { value: 0 },
                uAmplitude: { value: this.options.amplitude },
                uColorStops: { value: colorStopsArray },
                uResolution: { value: [this.container.offsetWidth, this.container.offsetHeight] },
                uBlend: { value: this.options.blend },
                uSpeed: { value: this.options.speed }
            }
        });

        this.mesh = new Mesh(gl, { geometry, program: this.program });

        this.container.appendChild(gl.canvas);
        this.animate();
    }

    resize() {
        if (!this.renderer || !this.container) return;
        const width = this.container.offsetWidth;
        const height = this.container.offsetHeight;
        this.renderer.setSize(width, height);
        if (this.program) {
            this.program.uniforms.uResolution.value = [width, height];
        }
    }

    animate(t = 0) {
        requestAnimationFrame((time) => this.animate(time));

        if (this.program) {
            this.program.uniforms.uTime.value = t * 0.001;
            this.program.uniforms.uAmplitude.value = this.options.amplitude;
            this.program.uniforms.uBlend.value = this.options.blend;
            this.program.uniforms.uSpeed.value = this.options.speed;

            const colorStopsArray = this.options.colorStops.map(hex => {
                const c = new Color(hex);
                return [c.r, c.g, c.b];
            }).flat();
            this.program.uniforms.uColorStops.value = colorStopsArray;

            this.renderer.render({ scene: this.mesh });
        }
    }
}

// Initialize Aurora on element
if (typeof window !== 'undefined') {
    window.Aurora = Aurora;
    window.initAurora = function (elementId, options) {
        const container = document.getElementById(elementId);
        if (container) {
            return new Aurora(container, options);
        }
    };
}

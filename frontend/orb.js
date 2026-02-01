// Orb.js - WebGL Orb Background using OGL
// Converted from React component to vanilla JS

// Simple OGL-compatible classes for Orb
class OrbRenderer {
    constructor(options = {}) {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl', options);
        if (!gl) {
            console.error('WebGL not supported');
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

class OrbProgram {
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
            } else if (value.x !== undefined && value.y !== undefined && value.z !== undefined) {
                this.gl.uniform3f(location, value.x, value.y, value.z);
            }
        }
    }
}

class OrbTriangle {
    constructor(gl) {
        this.gl = gl;
        const vertices = new Float32Array([
            -1, -1, 0, 0,
            3, -1, 2, 0,
            -1, 3, 0, 2
        ]);

        this.buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    }
}

class OrbMesh {
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
        const uvLoc = gl.getAttribLocation(this.program.program, 'uv');

        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 16, 0);

        gl.enableVertexAttribArray(uvLoc);
        gl.vertexAttribPointer(uvLoc, 2, gl.FLOAT, false, 16, 8);

        gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
}

class Vec3 {
    constructor(x = 0, y = 0, z = 0) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    set(x, y, z) {
        this.x = x;
        this.y = y;
        this.z = z;
    }
}

// Orb class
class Orb {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            hue: options.hue !== undefined ? options.hue : 0,
            hoverIntensity: options.hoverIntensity !== undefined ? options.hoverIntensity : 0.2,
            rotateOnHover: options.rotateOnHover !== undefined ? options.rotateOnHover : true,
            forceHoverState: options.forceHoverState !== undefined ? options.forceHoverState : false,
            backgroundColor: options.backgroundColor || '#000000'
        };

        this.targetHover = 0;
        this.currentHover = 0;
        this.currentRot = 0;
        this.lastTime = 0;

        this.init();
    }

    hexToVec3(color) {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16) / 255;
            const g = parseInt(color.slice(3, 5), 16) / 255;
            const b = parseInt(color.slice(5, 7), 16) / 255;
            return new Vec3(r, g, b);
        }
        return new Vec3(0, 0, 0);
    }

    init() {
        const vert = `
            precision highp float;
            attribute vec2 position;
            attribute vec2 uv;
            varying vec2 vUv;
            void main() {
              vUv = uv;
              gl_Position = vec4(position, 0.0, 1.0);
            }
        `;

        const frag = `
            precision highp float;

            uniform float iTime;
            uniform vec3 iResolution;
            uniform float hue;
            uniform float hover;
            uniform float rot;
            uniform float hoverIntensity;
            uniform vec3 backgroundColor;
            varying vec2 vUv;

            vec3 rgb2yiq(vec3 c) {
              float y = dot(c, vec3(0.299, 0.587, 0.114));
              float i = dot(c, vec3(0.596, -0.274, -0.322));
              float q = dot(c, vec3(0.211, -0.523, 0.312));
              return vec3(y, i, q);
            }
            
            vec3 yiq2rgb(vec3 c) {
              float r = c.x + 0.956 * c.y + 0.621 * c.z;
              float g = c.x - 0.272 * c.y - 0.647 * c.z;
              float b = c.x - 1.106 * c.y + 1.703 * c.z;
              return vec3(r, g, b);
            }
            
            vec3 adjustHue(vec3 color, float hueDeg) {
              float hueRad = hueDeg * 3.14159265 / 180.0;
              vec3 yiq = rgb2yiq(color);
              float cosA = cos(hueRad);
              float sinA = sin(hueRad);
              float i = yiq.y * cosA - yiq.z * sinA;
              float q = yiq.y * sinA + yiq.z * cosA;
              yiq.y = i;
              yiq.z = q;
              return yiq2rgb(yiq);
            }
            
            vec3 hash33(vec3 p3) {
              p3 = fract(p3 * vec3(0.1031, 0.11369, 0.13787));
              p3 += dot(p3, p3.yxz + 19.19);
              return -1.0 + 2.0 * fract(vec3(
                p3.x + p3.y,
                p3.x + p3.z,
                p3.y + p3.z
              ) * p3.zyx);
            }
            
            float snoise3(vec3 p) {
              const float K1 = 0.333333333;
              const float K2 = 0.166666667;
              vec3 i = floor(p + (p.x + p.y + p.z) * K1);
              vec3 d0 = p - (i - (i.x + i.y + i.z) * K2);
              vec3 e = step(vec3(0.0), d0 - d0.yzx);
              vec3 i1 = e * (1.0 - e.zxy);
              vec3 i2 = 1.0 - e.zxy * (1.0 - e);
              vec3 d1 = d0 - (i1 - K2);
              vec3 d2 = d0 - (i2 - K1);
              vec3 d3 = d0 - 0.5;
              vec4 h = max(0.6 - vec4(
                dot(d0, d0),
                dot(d1, d1),
                dot(d2, d2),
                dot(d3, d3)
              ), 0.0);
              vec4 n = h * h * h * h * vec4(
                dot(d0, hash33(i)),
                dot(d1, hash33(i + i1)),
                dot(d2, hash33(i + i2)),
                dot(d3, hash33(i + 1.0))
              );
              return dot(vec4(31.316), n);
            }
            
            vec4 extractAlpha(vec3 colorIn) {
              float a = max(max(colorIn.r, colorIn.g), colorIn.b);
              return vec4(colorIn.rgb / (a + 1e-5), a);
            }
            
            const vec3 baseColor1 = vec3(0.8, 0.4, 1.0);  // Brighter purple
            const vec3 baseColor2 = vec3(0.5, 0.85, 1.0); // Brighter blue
            const vec3 baseColor3 = vec3(0.2, 0.25, 0.75); // Brighter dark blue
            const float innerRadius = 0.5;  // Larger visible radius
            const float noiseScale = 0.65;
            
            float light1(float intensity, float attenuation, float dist) {
              return intensity / (1.0 + dist * attenuation);
            }
            
            float light2(float intensity, float attenuation, float dist) {
              return intensity / (1.0 + dist * dist * attenuation);
            }
            
            vec4 draw(vec2 uv) {
              vec3 color1 = adjustHue(baseColor1, hue);
              vec3 color2 = adjustHue(baseColor2, hue);
              vec3 color3 = adjustHue(baseColor3, hue);
              
              float ang = atan(uv.y, uv.x);
              float len = length(uv);
              float invLen = len > 0.0 ? 1.0 / len : 0.0;
              
              float bgLuminance = dot(backgroundColor, vec3(0.299, 0.587, 0.114));
              
              float n0 = snoise3(vec3(uv * noiseScale, iTime * 0.5)) * 0.5 + 0.5;
              float r0 = mix(mix(innerRadius, 1.0, 0.4), mix(innerRadius, 1.0, 0.6), n0);
              float d0 = distance(uv, (r0 * invLen) * uv);
              float v0 = light1(1.5, 8.0, d0);

              v0 *= smoothstep(r0 * 1.1, r0, len);
              float innerFade = smoothstep(r0 * 0.7, r0 * 0.9, len);
              v0 *= mix(innerFade, 1.0, bgLuminance * 0.7);
              float cl = cos(ang + iTime * 2.0) * 0.5 + 0.5;
              
              float a = iTime * -1.0;
              vec2 pos = vec2(cos(a), sin(a)) * r0;
              float d = distance(uv, pos);
              float v1 = light2(2.0, 4.0, d);
              v1 *= light1(1.2, 40.0, d0);
              
              float v2 = smoothstep(1.0, mix(innerRadius, 1.0, n0 * 0.6), len);
              float v3 = smoothstep(innerRadius * 0.9, mix(innerRadius, 1.0, 0.6), len);
              
              vec3 colBase = mix(color1, color2, cl);
              float fadeAmount = mix(1.0, 0.2, bgLuminance);
              
              vec3 darkCol = mix(color3, colBase, v0);
              darkCol = (darkCol + v1 * 0.5) * v2 * v3 * 1.2;
              darkCol = clamp(darkCol, 0.0, 1.0);
              
              vec3 lightCol = (colBase + v1 * 0.8) * mix(1.0, v2 * v3, fadeAmount) * 1.1;
              lightCol = mix(backgroundColor, lightCol, v0);
              lightCol = clamp(lightCol, 0.0, 1.0);
              
              vec3 finalCol = mix(darkCol, lightCol, bgLuminance);
              
              return extractAlpha(finalCol);
            }
            
            vec4 mainImage(vec2 fragCoord) {
              vec2 center = iResolution.xy * 0.5;
              float size = min(iResolution.x, iResolution.y);
              vec2 uv = (fragCoord - center) / size * 2.0;
              
              float angle = rot;
              float s = sin(angle);
              float c = cos(angle);
              uv = vec2(c * uv.x - s * uv.y, s * uv.x + c * uv.y);
              
              uv.x += hover * hoverIntensity * 0.1 * sin(uv.y * 10.0 + iTime);
              uv.y += hover * hoverIntensity * 0.1 * sin(uv.x * 10.0 + iTime);
              
              return draw(uv);
            }
            
            void main() {
              vec2 fragCoord = vUv * iResolution.xy;
              vec4 col = mainImage(fragCoord);
              gl_FragColor = vec4(col.rgb * col.a, col.a);
            }
        `;

        const renderer = new OrbRenderer({
            alpha: true,
            premultipliedAlpha: false
        });

        if (!renderer.gl) return;

        const gl = renderer.gl;
        this.gl = gl;
        this.renderer = renderer;

        gl.clearColor(0, 0, 0, 0);
        this.container.appendChild(gl.canvas);

        const geometry = new OrbTriangle(gl);
        this.program = new OrbProgram(gl, {
            vertex: vert,
            fragment: frag,
            uniforms: {
                iTime: { value: 0 },
                iResolution: { value: new Vec3(gl.canvas.width, gl.canvas.height, gl.canvas.width / gl.canvas.height) },
                hue: { value: this.options.hue },
                hover: { value: 0 },
                rot: { value: 0 },
                hoverIntensity: { value: this.options.hoverIntensity },
                backgroundColor: { value: this.hexToVec3(this.options.backgroundColor) }
            }
        });

        this.mesh = new OrbMesh(gl, { geometry, program: this.program });

        this.resize = () => {
            if (!this.container) return;
            const dpr = window.devicePixelRatio || 1;
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;
            this.renderer.setSize(width * dpr, height * dpr);
            gl.canvas.style.width = width + 'px';
            gl.canvas.style.height = height + 'px';
            this.program.uniforms.iResolution.value.set(gl.canvas.width, gl.canvas.height, gl.canvas.width / gl.canvas.height);
        };

        window.addEventListener('resize', this.resize);
        this.resize();

        const handleMouseMove = (e) => {
            const rect = this.container.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const width = rect.width;
            const height = rect.height;
            const size = Math.min(width, height);
            const centerX = width / 2;
            const centerY = height / 2;
            const uvX = ((x - centerX) / size) * 2.0;
            const uvY = ((y - centerY) / size) * 2.0;

            if (Math.sqrt(uvX * uvX + uvY * uvY) < 0.8) {
                this.targetHover = 1;
            } else {
                this.targetHover = 0;
            }
        };

        const handleMouseLeave = () => {
            this.targetHover = 0;
        };

        this.container.addEventListener('mousemove', handleMouseMove);
        this.container.addEventListener('mouseleave', handleMouseLeave);

        this.animate();
    }

    animate(t = 0) {
        requestAnimationFrame((time) => this.animate(time));

        const dt = (t - this.lastTime) * 0.001;
        this.lastTime = t;

        this.program.uniforms.iTime.value = t * 0.001;
        this.program.uniforms.hue.value = this.options.hue;
        this.program.uniforms.hoverIntensity.value = this.options.hoverIntensity;

        const effectiveHover = this.options.forceHoverState ? 1 : this.targetHover;
        this.currentHover += (effectiveHover - this.currentHover) * 0.1;
        this.program.uniforms.hover.value = this.currentHover;

        if (this.options.rotateOnHover && effectiveHover > 0.5) {
            this.currentRot += dt * 0.3;
        }
        this.program.uniforms.rot.value = this.currentRot;
        this.program.uniforms.backgroundColor.value = this.hexToVec3(this.options.backgroundColor);

        this.renderer.render({ scene: this.mesh });
    }
}

// Initialize Orb on element
if (typeof window !== 'undefined') {
    window.Orb = Orb;
    window.initOrb = function (elementId, options) {
        const container = document.getElementById(elementId);
        if (container) {
            return new Orb(container, options);
        }
    };
}

import { useRef, useEffect } from 'react';

const vertexShaderSource = `
attribute vec2 position;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
}
`;

const fragmentShaderSource = `
precision highp float;
uniform vec2 uResolution;
uniform float uTime;
uniform float uHueShift;
uniform float uNoise;
uniform float uWarp;

#define iTime uTime
#define iResolution uResolution

vec4 sigmoid(vec4 x) { return 1.0 / (1.0 + exp(-x)); }

float rand(vec2 c) { return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453); }

mat3 rgb2yiq = mat3(0.299, 0.587, 0.114, 0.596, -0.274, -0.322, 0.211, -0.523, 0.312);
mat3 yiq2rgb = mat3(1.0, 0.956, 0.621, 1.0, -0.272, -0.647, 1.0, -1.106, 1.703);

vec3 hueShiftRGB(vec3 col, float deg) {
    vec3 yiq = rgb2yiq * col;
    float rad = radians(deg);
    float cosh = cos(rad), sinh = sin(rad);
    vec3 yiqShift = vec3(yiq.x, yiq.y * cosh - yiq.z * sinh, yiq.y * sinh + yiq.z * cosh);
    return clamp(yiq2rgb * yiqShift, 0.0, 1.0);
}

void main() {
    vec2 fragCoord = gl_FragCoord.xy;
    vec2 uv = (fragCoord / uResolution.xy) * 2.0 - 1.0;
    uv.y *= uResolution.y / uResolution.x;

    float t = uTime * 0.2;
    
    // Abstract Flow Logic (Simplified CPPN-style)
    vec3 col = vec3(0.0);
    float d = length(uv);
    
    vec2 st = uv;
    st += uWarp * vec2(sin(st.y * 5.0 + t), cos(st.x * 5.0 + t));
    
    float v1 = sin(st.x * 2.0 + t) + sin(st.y * 3.0 - t * 0.5);
    float v2 = cos(length(st * 4.0) - t);
    
    col.r = sigmoid(vec4(v1 * 5.0)).x;
    col.g = sigmoid(vec4(v2 * 3.0)).x;
    col.b = sigmoid(vec4((v1 + v2) * 2.0)).x;

    col.rgb = hueShiftRGB(col.rgb, uHueShift);
    col.rgb += (rand(uv + uTime) - 0.5) * uNoise;
    
    gl_FragColor = vec4(col, 1.0);
}
`;

export default function DarkVeil({
    hueShift = 220,
    noiseIntensity = 0.02,
    warpAmount = 0.2,
    speed = 0.5
}) {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        const gl = canvas.getContext('webgl');
        if (!gl) return;

        function createShader(gl, type, source) {
            const shader = gl.createShader(type);
            gl.shaderSource(shader, source);
            gl.compileShader(shader);
            return shader;
        }

        const program = gl.createProgram();
        gl.attachShader(program, createShader(gl, gl.VERTEX_SHADER, vertexShaderSource));
        gl.attachShader(program, createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource));
        gl.linkProgram(program);
        gl.useProgram(program);

        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);

        const positionLocation = gl.getAttribLocation(program, 'position');
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

        const resolutionLocation = gl.getUniformLocation(program, 'uResolution');
        const timeLocation = gl.getUniformLocation(program, 'uTime');
        const hueLocation = gl.getUniformLocation(program, 'uHueShift');
        const noiseLocation = gl.getUniformLocation(program, 'uNoise');
        const warpLocation = gl.getUniformLocation(program, 'uWarp');

        let animationFrameId;
        const render = (time) => {
            canvas.width = canvas.clientWidth;
            canvas.height = canvas.clientHeight;
            gl.viewport(0, 0, canvas.width, canvas.height);

            gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
            gl.uniform1f(timeLocation, time * 0.001 * speed);
            gl.uniform1f(hueLocation, hueShift);
            gl.uniform1f(noiseLocation, noiseIntensity);
            gl.uniform1f(warpLocation, warpAmount);

            gl.drawArrays(gl.TRIANGLES, 0, 6);
            animationFrameId = requestAnimationFrame(render);
        };

        animationFrameId = requestAnimationFrame(render);
        return () => cancelAnimationFrame(animationFrameId);
    }, [hueShift, noiseIntensity, warpAmount, speed]);

    return <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

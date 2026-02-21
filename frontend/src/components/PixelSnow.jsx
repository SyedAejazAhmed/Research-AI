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
uniform float uDensity;
uniform float uSpeed;

float rand(vec2 n) { 
    return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
}

void main() {
    vec2 uv = gl_FragCoord.xy / uResolution.xy;
    float time = uTime * uSpeed;
    
    vec3 col = vec3(0.0);
    
    // Simple vertical moving particles for "Synthesis Signal" snow
    for(float i=0.0; i<30.0; i++) {
        float floor_i = i;
        float h = rand(vec2(floor_i, 1.337));
        float x = h;
        float y = fract(0.2 * time * (0.5 + h) + h); // moving down
        
        vec2 p = vec2(x, 1.0 - y);
        float dist = length(uv - p);
        
        float size = 0.002 + 0.001 * sin(time + i);
        float brightness = 0.4 / (dist / size);
        brightness *= smoothstep(0.0, 0.1, y) * smoothstep(1.0, 0.9, y); // fade edges
        
        col += vec3(brightness) * uDensity;
    }
    
    gl_FragColor = vec4(col, col.r);
}
`;

export default function PixelSnow({ density = 0.5, speed = 1.0 }) {
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

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);

    const posAttr = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(posAttr);
    gl.vertexAttribPointer(posAttr, 2, gl.FLOAT, false, 0, 0);

    const resUnif = gl.getUniformLocation(program, 'uResolution');
    const timeUnif = gl.getUniformLocation(program, 'uTime');
    const densUnif = gl.getUniformLocation(program, 'uDensity');
    const speedUnif = gl.getUniformLocation(program, 'uSpeed');

    let frameId;
    const render = (time) => {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      gl.uniform2f(resUnif, canvas.width, canvas.height);
      gl.uniform1f(timeUnif, time * 0.001);
      gl.uniform1f(densUnif, density);
      gl.uniform1f(speedUnif, speed);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
      frameId = requestAnimationFrame(render);
    };

    frameId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frameId);
  }, [density, speed]);

  return <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />;
}

"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  Color,
  Points,
  ShaderMaterial,
} from "three";

const vertexShader = `
  uniform float uTime;
  uniform float uDepth;
  attribute float aBand;
  attribute float aPhase;
  varying float vBand;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    float wave = sin((p.x * 1.12) + uTime * 0.74 + aPhase) * 0.42;
    float twist = cos((p.y * 1.38) - uTime * 0.56 + aPhase) * 0.36;
    p.z += wave + twist + sin(uTime * 0.45 + aPhase) * uDepth;
    p.y += sin(p.x * 0.62 + uTime * 0.52 + aPhase) * 0.2;
    p.x += cos(p.y * 0.7 + uTime * 0.34 + aPhase) * 0.13;

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
    gl_PointSize = (2.0 + aBand * 0.9) * (9.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
    vBand = aBand;
    vAlpha = 0.42 + 0.38 * sin(uTime * 0.7 + aPhase);
  }
`;

const fragmentShader = `
  uniform vec3 uMagenta;
  uniform vec3 uTeal;
  varying float vBand;
  varying float vAlpha;

  void main() {
    vec2 center = gl_PointCoord - vec2(0.5);
    float distanceFromCenter = length(center);
    float dotMask = smoothstep(0.5, 0.16, distanceFromCenter);
    if (dotMask <= 0.02) discard;

    vec3 color = mix(uTeal, uMagenta, vBand);
    gl_FragColor = vec4(color, dotMask * vAlpha);
  }
`;

function WavePoints() {
  const pointsRef = useRef<Points>(null);
  const materialRef = useRef<ShaderMaterial>(null);

  const geometryData = useMemo(() => {
    const rows = 58;
    const columns = 124;
    const positions: number[] = [];
    const bands: number[] = [];
    const phases: number[] = [];

    for (let yIndex = 0; yIndex < rows; yIndex += 1) {
      for (let xIndex = 0; xIndex < columns; xIndex += 1) {
        const u = xIndex / (columns - 1);
        const v = yIndex / (rows - 1);
        const centeredX = u * 2 - 1;
        const centeredY = v * 2 - 1;
        const x = centeredX * 6.4;
        const baseY = centeredY * 2.35;
        const ridge =
          Math.cos(centeredX * Math.PI * 1.18) * 1.06 -
          Math.cos(centeredX * Math.PI * 2.36) * 0.36;
        const bandWidth = 0.28 + Math.cos(centeredX * Math.PI * 2.0) * 0.045;
        const bandCurve = Math.abs(centeredY - Math.sin(centeredX * Math.PI) * 0.12) < bandWidth;

        if (!bandCurve && (xIndex + yIndex) % 4 !== 0) {
          continue;
        }

        const y = baseY + ridge * 0.38;
        const z =
          Math.sin(centeredX * Math.PI * 2.0) * 0.92 +
          Math.cos(centeredY * Math.PI) * 0.78;
        const magentaWeight = Math.max(
          0,
          Math.min(1, 0.56 + Math.cos(centeredX * Math.PI * 1.35) * 0.34 - Math.abs(centeredY) * 0.18),
        );

        positions.push(x, y, z);
        bands.push(magentaWeight);
        phases.push((Math.abs(centeredX) * 7.0 + v * 9.0 + ((xIndex + yIndex) % 11)) * 0.28);
      }
    }

    return {
      bands: new Float32Array(bands),
      phases: new Float32Array(phases),
      positions: new Float32Array(positions),
    };
  }, []);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = elapsed;
      materialRef.current.uniforms.uDepth.value = 0.36 + Math.sin(elapsed * 0.28) * 0.18;
    }
    if (pointsRef.current) {
      pointsRef.current.rotation.x = -0.28 + Math.sin(elapsed * 0.18) * 0.05;
      pointsRef.current.rotation.y = Math.sin(elapsed * 0.16) * 0.1;
      pointsRef.current.rotation.z = Math.sin(elapsed * 0.11) * 0.025;
      pointsRef.current.position.x = 0;
      pointsRef.current.position.y = Math.cos(elapsed * 0.15) * 0.1;
    }
  });

  return (
    <points ref={pointsRef} position={[0, -0.2, -0.2]}>
      <bufferGeometry>
        <bufferAttribute
          args={[geometryData.positions, 3]}
          attach="attributes-position"
        />
        <bufferAttribute
          args={[geometryData.bands, 1]}
          attach="attributes-aBand"
        />
        <bufferAttribute
          args={[geometryData.phases, 1]}
          attach="attributes-aPhase"
        />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        blending={AdditiveBlending}
        depthWrite={false}
        fragmentShader={fragmentShader}
        transparent
        uniforms={{
          uDepth: { value: 0.4 },
          uMagenta: { value: new Color("#ff2aa3") },
          uTeal: { value: new Color("#035f72") },
          uTime: { value: 0 },
        }}
        vertexShader={vertexShader}
      />
    </points>
  );
}

export function ParticleWaveBackground() {
  return (
    <div className="three-wave-background" aria-hidden="true">
      <Canvas
        camera={{ fov: 44, position: [0, 0.15, 10] }}
        dpr={[1, 1.6]}
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
      >
        <WavePoints />
      </Canvas>
    </div>
  );
}

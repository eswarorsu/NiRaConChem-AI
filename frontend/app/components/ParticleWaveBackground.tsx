"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  AdditiveBlending,
  Color,
  Points,
  ShaderMaterial,
} from "three";

// ── Shaders for the Globe Grid (Longitude/Latitude cage) ──
const globeVertexShader = `
  uniform float uTime;
  attribute float aLat;
  varying float vY;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    
    // Calculate polar coordinates
    float angle = atan(p.z, p.x);
    float radius = length(vec2(p.x, p.z));
    
    // Liquid twisting waves along the vertical latitude slices
    float twist = sin(p.y * 1.3 + uTime * 1.1) * 0.22;
    float twistedAngle = angle + twist;
    
    p.x = radius * cos(twistedAngle);
    p.z = radius * sin(twistedAngle);
    
    // Radial ripples traveling vertically down the globe
    float ripple = sin(p.y * 2.0 - uTime * 1.8) * 0.06;
    vec3 normal2D = vec3(normalize(vec2(p.x, p.z)), 0.0);
    p += normal2D * ripple;

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
    
    // Size attenuation
    float ptSize = 1.9 * (10.0 / -mvPosition.z);
    
    // Make poles denser and slightly larger
    float poleIntensity = smoothstep(0.4, 0.0, abs(aLat - 0.5));
    ptSize *= (1.0 + poleIntensity * 0.6);
    
    gl_PointSize = ptSize;
    gl_Position = projectionMatrix * mvPosition;
    
    vY = position.y;
    vAlpha = 0.7;
  }
`;

const globeFragmentShader = `
  uniform vec3 uBlue;
  uniform vec3 uFuchsia;
  uniform vec3 uWhite;
  varying float vY;
  varying float vAlpha;

  void main() {
    vec2 center = gl_PointCoord - vec2(0.5);
    float dist = length(center);
    float mask = smoothstep(0.5, 0.16, dist);
    if (mask <= 0.0) discard;

    // Map Y position [-2.4, 2.4] to t [0.0, 1.0]
    float t = clamp((vY + 2.4) / 4.8, 0.0, 1.0);
    
    // Top is electric blue, bottom is fuchsia
    vec3 color = mix(uFuchsia, uBlue, t);
    
    // Glow white highlights at the absolute poles
    float poleDist = abs(t - 0.5) * 2.0; 
    if (poleDist > 0.82) {
      color = mix(color, uWhite, (poleDist - 0.82) / 0.18);
    }

    gl_FragColor = vec4(color, mask * vAlpha);
  }
`;

// ── Shaders for the Fuzzy Cloud Envelope ──
const cloudVertexShader = `
  uniform float uTime;
  attribute vec3 aRandom;
  varying float vY;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    vec3 normal = normalize(position);
    
    // Orbit drifting motion
    float orbitSpeed = 0.15 + aRandom.x * 0.2;
    float angle = atan(p.z, p.x) + uTime * orbitSpeed;
    float r = length(vec2(p.x, p.z));
    p.x = r * cos(angle);
    p.z = r * sin(angle);
    
    // Breathing wave oscillations
    p.y += sin(uTime * 0.7 + aRandom.y * 6.28) * 0.12;
    p += normal * (sin(uTime * 0.4 + aRandom.z * 6.28) * 0.06);

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
    
    float ptSize = 1.3 * (10.0 / -mvPosition.z);
    // Subtle shimmer (kept restrained rather than sparkly)
    ptSize *= (0.78 + 0.22 * sin(uTime * 2.6 + aRandom.y * 12.0));
    
    gl_PointSize = ptSize;
    gl_Position = projectionMatrix * mvPosition;
    
    vY = position.y;
    vAlpha = 0.3 + 0.2 * sin(uTime * 2.0 + aRandom.x * 6.0);
  }
`;

const cloudFragmentShader = `
  uniform vec3 uBlue;
  uniform vec3 uFuchsia;
  varying float vY;
  varying float vAlpha;

  void main() {
    vec2 center = gl_PointCoord - vec2(0.5);
    float dist = length(center);
    float mask = smoothstep(0.5, 0.18, dist);
    if (mask <= 0.0) discard;

    float t = clamp((vY + 2.8) / 5.6, 0.0, 1.0);
    vec3 color = mix(uFuchsia, uBlue, t);

    gl_FragColor = vec4(color, mask * vAlpha * 0.45);
  }
`;

function ParticleBall() {
  const globeRef = useRef<Points>(null);
  const cloudRef = useRef<Points>(null);

  const globeMaterialRef = useRef<ShaderMaterial>(null);
  const cloudMaterialRef = useRef<ShaderMaterial>(null);

  // 1. Globe Grid Geometry (Longitude slices)
  const globeData = useMemo(() => {
    const numColumns = 60;
    const pointsPerColumn = 120;
    const positions: number[] = [];
    const lats: number[] = [];

    for (let col = 0; col < numColumns; col++) {
      const theta = (col / numColumns) * 2.0 * Math.PI;
      for (let row = 0; row < pointsPerColumn; row++) {
        const phi = (row / (pointsPerColumn - 1)) * Math.PI;
        
        const radius = 2.4;
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.cos(phi);
        const z = radius * Math.sin(phi) * Math.sin(theta);
        
        positions.push(x, y, z);
        lats.push(row / (pointsPerColumn - 1));
      }
    }

    return {
      positions: new Float32Array(positions),
      lats: new Float32Array(lats),
    };
  }, []);

  // 2. Cloud Geometry (Fuzzy envelope)
  const cloudData = useMemo(() => {
    const numPoints = 14000;
    const positions: number[] = [];
    const randoms: number[] = [];

    for (let i = 0; i < numPoints; i++) {
      const phi = Math.acos(1 - 2 * Math.random());
      const theta = Math.PI * 2 * Math.random();
      
      // Spherical band with variable radius to form fuzzy outline
      const radius = 2.2 + Math.random() * 0.72;
      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.cos(phi);
      const z = radius * Math.sin(phi) * Math.sin(theta);

      positions.push(x, y, z);
      randoms.push(Math.random(), Math.random(), Math.random());
    }

    return {
      positions: new Float32Array(positions),
      randoms: new Float32Array(randoms),
    };
  }, []);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    
    if (globeMaterialRef.current) globeMaterialRef.current.uniforms.uTime.value = elapsed;
    if (cloudMaterialRef.current) cloudMaterialRef.current.uniforms.uTime.value = elapsed;

    // Slow organic rotation
    if (globeRef.current) {
      globeRef.current.rotation.y = elapsed * 0.08;
      globeRef.current.rotation.x = elapsed * 0.04;
    }
    if (cloudRef.current) {
      cloudRef.current.rotation.y = elapsed * 0.06;
      cloudRef.current.rotation.x = elapsed * 0.02;
    }
  });

  return (
    <group position={[0, -0.2, 0]}>
      {/* 1. Globe Grid */}
      <points ref={globeRef}>
        <bufferGeometry>
          <bufferAttribute
            args={[globeData.positions, 3]}
            attach="attributes-position"
          />
          <bufferAttribute
            args={[globeData.lats, 1]}
            attach="attributes-aLat"
          />
        </bufferGeometry>
        <shaderMaterial
          ref={globeMaterialRef}
          blending={AdditiveBlending}
          depthWrite={false}
          fragmentShader={globeFragmentShader}
          transparent
          uniforms={{
            uBlue: { value: new Color("#c4a373") },
            uFuchsia: { value: new Color("#a8542f") },
            uWhite: { value: new Color("#fdf8ec") },
            uTime: { value: 0 },
          }}
          vertexShader={globeVertexShader}
        />
      </points>

      {/* 2. Fuzzy Cloud */}
      <points ref={cloudRef}>
        <bufferGeometry>
          <bufferAttribute
            args={[cloudData.positions, 3]}
            attach="attributes-position"
          />
          <bufferAttribute
            args={[cloudData.randoms, 3]}
            attach="attributes-aRandom"
          />
        </bufferGeometry>
        <shaderMaterial
          ref={cloudMaterialRef}
          blending={AdditiveBlending}
          depthWrite={false}
          fragmentShader={cloudFragmentShader}
          transparent
          uniforms={{
            uBlue: { value: new Color("#c4a373") },
            uFuchsia: { value: new Color("#a8542f") },
            uTime: { value: 0 },
          }}
          vertexShader={cloudVertexShader}
        />
      </points>
    </group>
  );
}

export function ParticleWaveBackground() {
  return (
    <div className="three-wave-background" aria-hidden="true">
      <Canvas
        camera={{ fov: 44, position: [0, 0, 9.5] }}
        dpr={[1, 1.6]}
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
      >
        <ParticleBall />
      </Canvas>
    </div>
  );
}

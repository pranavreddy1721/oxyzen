import { Suspense, useMemo, useRef, useState, Component } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, useTexture } from "@react-three/drei";
import * as THREE from "three";
import { Globe } from "lucide-react";

const MAP_URL = "/textures/earth.jpg";
const BUMP_URL = "/textures/topology.png";

function hasWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")));
  } catch {
    return false;
  }
}

function latLonToVec3(lat, lon, r) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

function EarthMesh({ markers, reduced }) {
  const groupRef = useRef();
  const [map, bump] = useTexture([MAP_URL, BUMP_URL]);
  map.colorSpace = THREE.SRGBColorSpace;

  useFrame((_, delta) => {
    if (reduced || !groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.06;
  });

  return (
    <group ref={groupRef} rotation={[0.3, -1.2, 0]}>
      <mesh>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial map={map} bumpMap={bump} bumpScale={0.05} metalness={0.1} roughness={0.85} />
      </mesh>
      <mesh>
        <sphereGeometry args={[2.16, 64, 64]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.13} side={THREE.BackSide} />
      </mesh>
      {(markers || []).map((m) => {
        const pos = latLonToVec3(m.lat, m.lon, 2.04);
        return (
          <mesh key={m.id} position={pos}>
            <sphereGeometry args={[0.028, 12, 12]} />
            <meshBasicMaterial color={m.color} toneMapped={false} />
          </mesh>
        );
      })}
    </group>
  );
}

class GlobeErrorBoundary extends Component {
  constructor(p) { super(p); this.state = { err: false }; }
  static getDerivedStateFromError() { return { err: true }; }
  render() { return this.state.err ? this.props.fallback : this.props.children; }
}

function StaticGlobe() {
  return (
    <div className="flex h-full w-full items-center justify-center" data-testid="globe-fallback">
      <div className="relative h-64 w-64 rounded-full bg-gradient-to-br from-blue-600 via-emerald-500 to-blue-900 shadow-2xl">
        <div className="absolute inset-0 rounded-full opacity-40 tech-grid" style={{ maskImage: "radial-gradient(circle, black 60%, transparent 70%)" }} />
        <Globe className="absolute left-1/2 top-1/2 h-20 w-20 -translate-x-1/2 -translate-y-1/2 text-white/70" strokeWidth={1} />
      </div>
    </div>
  );
}

export default function EarthGlobe({ markers = [] }) {
  const [webgl] = useState(() => hasWebGL());
  const reduced = useMemo(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    []
  );

  if (!webgl) return <StaticGlobe />;

  return (
    <div className="h-full w-full" data-testid="earth-globe">
      <GlobeErrorBoundary fallback={<StaticGlobe />}>
        <Canvas camera={{ position: [0, 0, 6], fov: 45 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
          <ambientLight intensity={0.9} />
          <directionalLight position={[5, 3, 5]} intensity={2.6} />
          <directionalLight position={[-5, -2, -4]} intensity={0.5} />
          <Suspense fallback={null}>
            <Stars radius={100} depth={50} count={2200} factor={4} saturation={0} fade speed={0.4} />
            <EarthMesh markers={markers} reduced={reduced} />
          </Suspense>
          <OrbitControls enableZoom={false} enablePan={false} rotateSpeed={0.4} />
        </Canvas>
      </GlobeErrorBoundary>
    </div>
  );
}

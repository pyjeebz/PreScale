import { useState, useRef, useMemo, useCallback, Suspense, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Center, Environment } from "@react-three/drei";
import { EffectComposer, RenderPass, ShaderPass } from "three/examples/jsm/postprocessing/EffectComposer";
import * as THREE from "three";
import { PreScaleLogo } from "./PreScaleLogo";

/* ─── ASCII character sets ─── */
const ASCII_PRESETS: Record<string, { label: string; chars: string }> = {
    dense: { label: "Dense", chars: "@%#*+=-:. " },
    balanced: { label: "Balanced", chars: "@#S%?*+;:,. " },
    minimal: { label: "Minimal", chars: "@. " },
    blocks: { label: "Blocks", chars: "█▓▒░ " },
};

/* ─── Built-in geometric models ─── */
const MODELS = [
    { id: "torus-knot", name: "Torus Knot", type: "geometry" as const },
    { id: "icosahedron", name: "Icosahedron", type: "geometry" as const },
    { id: "octahedron", name: "Octahedron", type: "geometry" as const },
    { id: "dodecahedron", name: "Dodecahedron", type: "geometry" as const },
    { id: "sphere", name: "Sphere", type: "geometry" as const },
];

/* ─── ASCII Effect (custom post-processing) ─── */
function AsciiEffect({
    characters,
    cellSize,
}: {
    characters: string;
    cellSize: number;
}) {
    const { gl, scene, camera, size } = useThree();
    const composerRef = useRef<any>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const preRef = useRef<HTMLPreElement | null>(null);
    const renderTarget = useMemo(
        () => new THREE.WebGLRenderTarget(size.width, size.height),
        [size.width, size.height]
    );

    useEffect(() => {
        // Create an offscreen canvas for reading pixels
        const canvas = document.createElement("canvas");
        canvasRef.current = canvas;

        // Create a <pre> element for ASCII output overlaid on the canvas
        const container = gl.domElement.parentElement;
        if (!container) return;

        let pre = container.querySelector("pre.ascii-overlay") as HTMLPreElement;
        if (!pre) {
            pre = document.createElement("pre");
            pre.className = "ascii-overlay";
            pre.style.cssText = `
                position: absolute; inset: 0; margin: 0; padding: 0;
                pointer-events: none; z-index: 10;
                font-family: 'DM Mono', monospace;
                line-height: 1;
                overflow: hidden;
                color: #c4b5fd;
                background: transparent;
            `;
            container.style.position = "relative";
            container.appendChild(pre);
        }
        preRef.current = pre;

        // Hide the WebGL canvas visually (we only show ASCII)
        gl.domElement.style.opacity = "0";

        return () => {
            pre.remove();
            gl.domElement.style.opacity = "1";
            renderTarget.dispose();
        };
    }, [gl, renderTarget]);

    useFrame(() => {
        if (!preRef.current || !canvasRef.current) return;

        // Render scene to offscreen target
        gl.setRenderTarget(renderTarget);
        gl.render(scene, camera);
        gl.setRenderTarget(null);

        // Read pixels
        const w = renderTarget.width;
        const h = renderTarget.height;
        const pixels = new Uint8Array(w * h * 4);
        gl.readRenderTargetPixels(renderTarget, 0, 0, w, h, pixels);

        // Convert to ASCII
        const cols = Math.floor(w / cellSize);
        const rows = Math.floor(h / cellSize);
        const fontSize = Math.max(cellSize * 0.85, 4);

        let ascii = "";
        for (let row = rows - 1; row >= 0; row--) {
            for (let col = 0; col < cols; col++) {
                const x = col * cellSize + Math.floor(cellSize / 2);
                const y = row * cellSize + Math.floor(cellSize / 2);
                const idx = (y * w + x) * 4;
                const r = pixels[idx] || 0;
                const g = pixels[idx + 1] || 0;
                const b = pixels[idx + 2] || 0;
                const brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255;
                const charIdx = Math.floor(brightness * (characters.length - 1));
                ascii += characters[charIdx] || " ";
            }
            ascii += "\n";
        }

        preRef.current.textContent = ascii;
        preRef.current.style.fontSize = `${fontSize}px`;
        preRef.current.style.letterSpacing = `${cellSize * 0.15}px`;
    });

    return null;
}

/* ─── Rotating geometric model ─── */
function GeometricModel({ modelId }: { modelId: string }) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((_, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.y += delta * 0.4;
            meshRef.current.rotation.x += delta * 0.15;
        }
    });

    const geometry = useMemo(() => {
        switch (modelId) {
            case "torus-knot":
                return new THREE.TorusKnotGeometry(1, 0.35, 128, 32);
            case "icosahedron":
                return new THREE.IcosahedronGeometry(1.3, 1);
            case "octahedron":
                return new THREE.OctahedronGeometry(1.4, 0);
            case "dodecahedron":
                return new THREE.DodecahedronGeometry(1.3, 0);
            case "sphere":
                return new THREE.SphereGeometry(1.3, 32, 32);
            default:
                return new THREE.TorusKnotGeometry(1, 0.35, 128, 32);
        }
    }, [modelId]);

    return (
        <mesh ref={meshRef} geometry={geometry}>
            <meshStandardMaterial
                color="#a78bfa"
                emissive="#4c1d95"
                emissiveIntensity={0.3}
                roughness={0.4}
                metalness={0.6}
            />
        </mesh>
    );
}

/* ─── Scene ─── */
function Scene({
    modelId,
    characters,
    cellSize,
}: {
    modelId: string;
    characters: string;
    cellSize: number;
}) {
    return (
        <>
            <ambientLight intensity={0.5} />
            <directionalLight position={[5, 5, 5]} intensity={1} />
            <directionalLight position={[-3, -3, 2]} intensity={0.4} />
            <pointLight position={[0, 2, 0]} intensity={0.6} color="#818cf8" />

            <Center>
                <GeometricModel modelId={modelId} />
            </Center>

            <OrbitControls
                enableDamping
                dampingFactor={0.05}
                enablePan={false}
                minDistance={2}
                maxDistance={8}
            />

            <AsciiEffect characters={characters} cellSize={cellSize} />
        </>
    );
}

/* ─── Main Page ─── */
export function AsciiViewer() {
    const [selectedModel, setSelectedModel] = useState(MODELS[0].id);
    const [preset, setPreset] = useState<string>("balanced");
    const [cellSize, setCellSize] = useState(8);

    const characters = ASCII_PRESETS[preset].chars;

    return (
        <div
            className="flex h-screen w-full overflow-hidden"
            style={{
                backgroundColor: "#0a0a0a",
                fontFamily: "'DM Mono', monospace",
                fontSize: 15,
                paddingTop: 56, /* navbar height */
            }}
        >
            {/* Left sidebar — model list */}
            <div
                className="flex flex-col shrink-0 w-56 p-6"
                style={{ gap: 32 }}
            >
                <div>
                    <div
                        className="text-xs uppercase tracking-widest mb-4"
                        style={{ color: "#737373" }}
                    >
                        Models
                    </div>
                    <div className="flex flex-col" style={{ gap: 4 }}>
                        {MODELS.map((model) => (
                            <button
                                key={model.id}
                                onClick={() => setSelectedModel(model.id)}
                                className="text-left px-3 py-2 rounded-md transition-colors text-sm"
                                style={{
                                    color:
                                        selectedModel === model.id
                                            ? "#c4b5fd"
                                            : "#737373",
                                    backgroundColor:
                                        selectedModel === model.id
                                            ? "rgba(139, 92, 246, 0.1)"
                                            : "transparent",
                                }}
                            >
                                {model.name}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Center — 3D canvas */}
            <div className="flex-1 relative" style={{ margin: 32 }}>
                <Canvas
                    key={selectedModel}
                    gl={{ antialias: true, alpha: false }}
                    camera={{ position: [0, 0, 4], fov: 50 }}
                    style={{
                        background: "#0a0a0a",
                        borderRadius: 12,
                    }}
                >
                    <color attach="background" args={["#0a0a0a"]} />
                    <Suspense fallback={null}>
                        <Scene
                            modelId={selectedModel}
                            characters={characters}
                            cellSize={cellSize}
                        />
                    </Suspense>
                </Canvas>
            </div>

            {/* Right panel — presets & controls */}
            <div
                className="flex flex-col shrink-0 w-56 p-6"
                style={{ gap: 32 }}
            >
                {/* ASCII Presets */}
                <div>
                    <div
                        className="text-xs uppercase tracking-widest mb-4"
                        style={{ color: "#737373" }}
                    >
                        ASCII Preset
                    </div>
                    <div className="flex flex-col" style={{ gap: 4 }}>
                        {Object.entries(ASCII_PRESETS).map(([key, val]) => (
                            <button
                                key={key}
                                onClick={() => setPreset(key)}
                                className="text-left px-3 py-2 rounded-md transition-colors text-sm"
                                style={{
                                    color:
                                        preset === key ? "#c4b5fd" : "#737373",
                                    backgroundColor:
                                        preset === key
                                            ? "rgba(139, 92, 246, 0.1)"
                                            : "transparent",
                                }}
                            >
                                {val.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Resolution slider */}
                <div>
                    <div
                        className="text-xs uppercase tracking-widest mb-4"
                        style={{ color: "#737373" }}
                    >
                        Resolution
                    </div>
                    <div className="flex items-center" style={{ gap: 12 }}>
                        <span
                            className="text-xs tabular-nums"
                            style={{ color: "#525252" }}
                        >
                            Fine
                        </span>
                        <input
                            type="range"
                            min={2}
                            max={16}
                            value={cellSize}
                            onChange={(e) =>
                                setCellSize(Number(e.target.value))
                            }
                            className="flex-1 accent-purple-500"
                            style={{ cursor: "pointer" }}
                        />
                        <span
                            className="text-xs tabular-nums"
                            style={{ color: "#525252" }}
                        >
                            Coarse
                        </span>
                    </div>
                    <div
                        className="text-center text-xs mt-2 tabular-nums"
                        style={{ color: "#525252" }}
                    >
                        Cell: {cellSize}px
                    </div>
                </div>

                {/* Characters preview */}
                <div>
                    <div
                        className="text-xs uppercase tracking-widest mb-3"
                        style={{ color: "#737373" }}
                    >
                        Characters
                    </div>
                    <div
                        className="text-sm tracking-widest break-all"
                        style={{ color: "#525252" }}
                    >
                        {characters}
                    </div>
                </div>
            </div>
        </div>
    );
}

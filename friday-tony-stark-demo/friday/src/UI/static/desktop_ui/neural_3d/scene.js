import * as THREE from "./vendor/three.module.min.js";

const shell = document.getElementById("neural-shell");
const canvas = document.getElementById("neural-canvas");
const inspector = document.getElementById("inspector");
const layerLegend = document.getElementById("layer-legend");
const pauseButton = document.getElementById("pause-button");
const resetButton = document.getElementById("reset-button");
const renderError = document.getElementById("render-error");

const fields = {
  liveState: document.getElementById("live-state"),
  inspectorKind: document.getElementById("inspector-kind"),
  inspectorTitle: document.getElementById("inspector-title"),
  inspectorStatus: document.getElementById("inspector-status"),
  inspectorDescription: document.getElementById("inspector-description"),
  inspectorData: document.getElementById("inspector-data"),
  inspectorSource: document.getElementById("inspector-source"),
  inspectorTarget: document.getElementById("inspector-target"),
  inspectorTrace: document.getElementById("inspector-trace"),
  inspectorLatency: document.getElementById("inspector-latency"),
  runtimeState: document.getElementById("runtime-state"),
  runtimeTrace: document.getElementById("runtime-trace"),
  runtimePackets: document.getElementById("runtime-packets"),
  runtimeLatency: document.getElementById("runtime-latency"),
  runtimeFps: document.getElementById("runtime-fps"),
};

const STATUS_COLORS = {
  active: new THREE.Color("#58e1e5"),
  success: new THREE.Color("#70e6a7"),
  error: new THREE.Color("#ff766e"),
};

const STATE_COLORS = {
  online: new THREE.Color("#58e1e5"),
  listening: new THREE.Color("#63dff2"),
  thinking: new THREE.Color("#f0b75e"),
  speaking: new THREE.Color("#71efb3"),
  sleeping: new THREE.Color("#60747d"),
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const scene = new THREE.Scene();
scene.background = new THREE.Color("#020608");
scene.fog = new THREE.FogExp2("#020608", 0.021);

const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 80);
const initialCamera = new THREE.Vector3(0, 0.2, 18);
camera.position.copy(initialCamera);

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const networkGroup = new THREE.Group();
scene.add(networkGroup);

const brainGroup = new THREE.Group();
scene.add(brainGroup);

scene.add(new THREE.AmbientLight("#8fdfe3", 0.52));
const leftLight = new THREE.PointLight("#58e1e5", 8, 18, 2);
leftLight.position.set(-4.5, 2.8, 5.5);
scene.add(leftLight);
const rightLight = new THREE.PointLight("#ff9d72", 6, 18, 2);
rightLight.position.set(4.5, -1.8, 4.5);
scene.add(rightLight);

const nodeMeshes = new Map();
const edgeMeshes = new Map();
const nodeRuntime = new Map();
const edgeRuntime = new Map();
const pulses = [];
const interactiveObjects = [];
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2(2, 2);
const clock = new THREE.Clock();
const projected = new THREE.Vector3();

let topology = null;
let ready = false;
let paused = false;
let visible = true;
let state = "online";
let hovered = null;
let pinned = null;
let dragStart = null;
let dragMoved = false;
let yaw = 0;
let pitch = -0.05;
let elapsed = 0;
let frameCount = 0;
let fpsWindowStart = performance.now();
let measuredFps = 0;
let latestTrace = "-";
let latestLatency = null;
let brainTissue = null;

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function defaultCameraDistance() {
  const aspect = Math.max(0.35, shell.clientWidth / Math.max(1, shell.clientHeight));
  return aspect < 0.85 ? clamp(16 / aspect, 20, 38) : 15.5;
}

function cleanText(value, fallback = "-") {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function nodeLabel(nodeId) {
  const entry = nodeRuntime.get(nodeId);
  return entry ? entry.definition.label : "none";
}

function seededRandomFactory(seed) {
  let stateSeed = seed >>> 0;
  return () => {
    stateSeed = (Math.imul(1664525, stateSeed) + 1013904223) >>> 0;
    return stateSeed / 4294967296;
  };
}

function createBackdrop() {
  const random = seededRandomFactory(0xf31da7);
  const starCount = 170;
  const positions = new Float32Array(starCount * 3);
  for (let index = 0; index < starCount; index += 1) {
    const offset = index * 3;
    positions[offset] = (random() - 0.5) * 30;
    positions[offset + 1] = (random() - 0.5) * 15;
    positions[offset + 2] = -5 - random() * 18;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color: "#4a9da5",
    size: 0.022,
    transparent: true,
    opacity: 0.25,
    depthWrite: false,
  });
  scene.add(new THREE.Points(geometry, material));
}

function createLayer(layer) {
  const item = document.createElement("span");
  item.textContent = layer.label;
  item.style.setProperty("--layer-color", layer.color);
  layerLegend.appendChild(item);
}

function sampleBrainPoint(random, hemisphere) {
  while (true) {
    const u = random() * 2 - 1;
    const v = random() * 2 - 1;
    const w = random() * 2 - 1;
    if (u * u + v * v + w * w > 1) continue;
    const taper = 1 - Math.max(0, -v) * 0.12;
    return {
      position: new THREE.Vector3(
        hemisphere * (0.16 + Math.abs(u) * 5.25 * taper),
        v * 3.45,
        w * 2.65 * taper,
      ),
      depth: Math.min(1, Math.sqrt(u * u + v * v + w * w)),
    };
  }
}

function createBrainTissue() {
  const random = seededRandomFactory(0x51a7b1e);
  const pointsPerHemisphere = 560;
  const positions = [];
  const colors = [];
  const deepColor = new THREE.Color("#2f7785");
  const palette = [
    new THREE.Color("#58e1e5"),
    new THREE.Color("#70e6a7"),
    new THREE.Color("#6291ff"),
    new THREE.Color("#f0b75e"),
    new THREE.Color("#ff766e"),
  ];

  [-1, 1].forEach((hemisphere) => {
    for (let created = 0; created < pointsPerHemisphere; created += 1) {
      const sample = sampleBrainPoint(random, hemisphere);
      positions.push(sample.position.x, sample.position.y, sample.position.z);
      const paletteOffset = hemisphere < 0 ? 0 : 2;
      const color = deepColor.clone().lerp(
        palette[(paletteOffset + Math.floor(random() * 3)) % palette.length],
        0.42 + sample.depth * 0.48,
      );
      colors.push(color.r, color.g, color.b);
    }
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  brainTissue = new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      size: 0.022,
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      sizeAttenuation: true,
    }),
  );
  brainGroup.add(brainTissue);

  [-1, 1].forEach((hemisphere) => {
    const shell = new THREE.Mesh(
      new THREE.SphereGeometry(1, 24, 16),
      new THREE.MeshStandardMaterial({
        color: hemisphere < 0 ? "#58e1e5" : "#718ef4",
        emissive: hemisphere < 0 ? "#1d5960" : "#26365f",
        emissiveIntensity: 0.18,
        roughness: 0.62,
        metalness: 0.04,
        transparent: true,
        opacity: 0.024,
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    );
    shell.scale.set(2.95, 3.35, 2.62);
    shell.position.x = hemisphere * 2.45;
    brainGroup.add(shell);
  });
}

function createCircuitLattice() {
  const random = seededRandomFactory(0xc1ac017);
  const palette = ["#58e1e5", "#70e6a7", "#6291ff", "#f0b75e", "#ff766e"];
  const linePositions = [];
  const lineColors = [];
  const junctionPositions = [];
  const junctionColors = [];

  for (let pathIndex = 0; pathIndex < 150; pathIndex += 1) {
    const hemisphere = random() < 0.5 ? -1 : 1;
    const start = sampleBrainPoint(random, hemisphere).position.multiplyScalar(0.88);
    const color = new THREE.Color(palette[pathIndex % palette.length]);
    const first = start.clone().add(new THREE.Vector3(
      (random() - 0.5) * 0.85,
      0,
      0,
    ));
    const second = first.clone().add(new THREE.Vector3(
      0,
      (random() - 0.5) * 0.72,
      0,
    ));
    const end = second.clone().add(new THREE.Vector3(
      0,
      0,
      (random() - 0.5) * 0.62,
    ));
    [[start, first], [first, second], [second, end]].forEach(([from, to]) => {
      linePositions.push(from.x, from.y, from.z, to.x, to.y, to.z);
      lineColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
    });
    junctionPositions.push(end.x, end.y, end.z);
    junctionColors.push(color.r, color.g, color.b);
  }

  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));
  lineGeometry.setAttribute("color", new THREE.Float32BufferAttribute(lineColors, 3));
  brainGroup.add(new THREE.LineSegments(
    lineGeometry,
    new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.12,
      depthWrite: false,
    }),
  ));

  const junctionGeometry = new THREE.BufferGeometry();
  junctionGeometry.setAttribute("position", new THREE.Float32BufferAttribute(junctionPositions, 3));
  junctionGeometry.setAttribute("color", new THREE.Float32BufferAttribute(junctionColors, 3));
  brainGroup.add(new THREE.Points(
    junctionGeometry,
    new THREE.PointsMaterial({
      size: 0.032,
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      sizeAttenuation: true,
    }),
  ));
}

function createCorticalFolds() {
  [-1, 1].forEach((hemisphere) => {
    for (let foldIndex = 0; foldIndex < 6; foldIndex += 1) {
      const points = [];
      const zBase = -1.55 + foldIndex * 0.62;
      for (let step = 0; step <= 48; step += 1) {
        const angle = (step / 48) * Math.PI * 2;
        const ripple = 1 + Math.sin(angle * 5 + foldIndex * 0.9) * 0.045;
        points.push(new THREE.Vector3(
          hemisphere * (2.42 + Math.cos(angle) * 2.86 * ripple),
          Math.sin(angle) * 3.18 * ripple,
          zBase + Math.sin(angle * 3 + foldIndex) * 0.16,
        ));
      }
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const fold = new THREE.Line(
        geometry,
        new THREE.LineBasicMaterial({
          color: hemisphere < 0 ? "#45bac4" : "#5f7fd1",
          transparent: true,
          opacity: 0.045,
          depthWrite: false,
        }),
      );
      brainGroup.add(fold);
    }
  });

  const fissurePoints = [];
  for (let index = 0; index <= 32; index += 1) {
    const t = index / 32;
    fissurePoints.push(new THREE.Vector3(
      Math.sin(t * Math.PI * 5) * 0.055,
      -3.0 + t * 6.0,
      2.3 + Math.sin(t * Math.PI * 3) * 0.13,
    ));
  }
  brainGroup.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(fissurePoints),
    new THREE.LineBasicMaterial({
      color: "#8adfe2",
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    }),
  ));
}

function createNode(definition) {
  const color = new THREE.Color(definition.color);
  const isProcessor = definition.id === "reasoning.llm";
  const geometry = new THREE.SphereGeometry(definition.radius, 22, 16);
  const material = new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: isProcessor ? 1.15 : (definition.core ? 0.74 : 0.52),
    roughness: 0.28,
    metalness: 0.18,
    transparent: true,
    opacity: 0.92,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(
    definition.position.x,
    definition.position.y,
    definition.position.z,
  );
  mesh.userData = { kind: "node", id: definition.id };
  networkGroup.add(mesh);
  interactiveObjects.push(mesh);

  const ringMaterial = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: isProcessor ? 0.76 : (definition.core ? 0.38 : 0.13),
    depthWrite: false,
  });
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(definition.radius * 1.55, 0.008, 6, 32),
    ringMaterial,
  );
  ring.position.copy(mesh.position);
  ring.rotation.set(Math.PI / 2.8, 0.35, 0);
  networkGroup.add(ring);

  const orbit = new THREE.Mesh(
    new THREE.TorusGeometry(definition.radius * 1.92, 0.005, 5, 30),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: isProcessor ? 0.44 : (definition.core ? 0.20 : 0.065),
      depthWrite: false,
    }),
  );
  orbit.position.copy(mesh.position);
  orbit.rotation.set(-0.65, 0.85, 0.3);
  networkGroup.add(orbit);

  if (isProcessor) {
    const outerRing = new THREE.Mesh(
      new THREE.TorusGeometry(definition.radius * 2.28, 0.007, 6, 42),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      }),
    );
    outerRing.position.copy(mesh.position);
    outerRing.rotation.x = Math.PI / 2.7;
    networkGroup.add(outerRing);
  }

  const label = document.createElement("span");
  label.className = "node-label";
  label.textContent = definition.label;
  label.dataset.core = String(isProcessor);
  label.style.setProperty("--node-color", definition.color);
  shell.appendChild(label);

  nodeMeshes.set(definition.id, {
    mesh,
    ring,
    orbit,
    label,
    definition,
    baseColor: color.clone(),
  });
  nodeRuntime.set(definition.id, {
    definition,
    activity: 0,
    incomingCount: 0,
    outgoingCount: 0,
    lastEvent: null,
    lastIncoming: null,
    lastOutgoing: null,
  });
}

function hashText(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createDendrites() {
  const positions = [];
  const colors = [];
  const junctionPositions = [];
  const junctionColors = [];

  nodeMeshes.forEach((entry, nodeId) => {
    const random = seededRandomFactory(hashText(nodeId));
    for (let branchIndex = 0; branchIndex < 4; branchIndex += 1) {
      const start = entry.mesh.position.clone();
      const direction = new THREE.Vector3(
        random() * 2 - 1,
        random() * 2 - 1,
        random() * 2 - 1,
      ).normalize();
      const joint = start.clone().add(direction.clone().multiplyScalar(0.36 + random() * 0.28));
      const end = joint.clone().add(new THREE.Vector3(
        (random() - 0.5) * 0.9,
        (random() - 0.5) * 0.9,
        (random() - 0.5) * 0.8,
      ));
      const control = joint.clone().add(new THREE.Vector3(0, (random() - 0.5) * 0.22, 0));
      const curve = new THREE.QuadraticBezierCurve3(
        start,
        control,
        end,
      );
      const points = curve.getPoints(6);
      for (let pointIndex = 1; pointIndex < points.length; pointIndex += 1) {
        const from = points[pointIndex - 1];
        const to = points[pointIndex];
        positions.push(from.x, from.y, from.z, to.x, to.y, to.z);
        colors.push(
          entry.baseColor.r, entry.baseColor.g, entry.baseColor.b,
          entry.baseColor.r, entry.baseColor.g, entry.baseColor.b,
        );
      }
      junctionPositions.push(end.x, end.y, end.z);
      junctionColors.push(entry.baseColor.r, entry.baseColor.g, entry.baseColor.b);
    }
  });

  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  lineGeometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  networkGroup.add(new THREE.LineSegments(
    lineGeometry,
    new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
    }),
  ));

  const junctionGeometry = new THREE.BufferGeometry();
  junctionGeometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(junctionPositions, 3),
  );
  junctionGeometry.setAttribute("color", new THREE.Float32BufferAttribute(junctionColors, 3));
  networkGroup.add(new THREE.Points(
    junctionGeometry,
    new THREE.PointsMaterial({
      size: 0.036,
      vertexColors: true,
      transparent: true,
      opacity: 0.78,
      depthWrite: false,
      sizeAttenuation: true,
    }),
  ));
}

function createEdge(definition) {
  const source = nodeMeshes.get(definition.source).mesh.position;
  const target = nodeMeshes.get(definition.target).mesh.position;
  const random = seededRandomFactory(hashText(definition.id));
  const controlA = source.clone().lerp(target, 0.32);
  const controlB = source.clone().lerp(target, 0.68);
  const verticalBend = definition.bend * 8 + (random() - 0.5) * 0.36;
  const depthBend = definition.bend * 10 + (random() - 0.5) * 0.72;
  controlA.y += verticalBend;
  controlB.y -= verticalBend * 0.42;
  controlA.z += depthBend;
  controlB.z -= depthBend * 0.34;
  const curve = new THREE.CubicBezierCurve3(
    source.clone(),
    controlA,
    controlB,
    target.clone(),
  );
  const material = new THREE.MeshBasicMaterial({
    color: "#43bec8",
    transparent: true,
    opacity: 0.095,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 34, 0.009, 5, false),
    material,
  );
  mesh.userData = { kind: "edge", id: definition.id };
  networkGroup.add(mesh);
  interactiveObjects.push(mesh);
  edgeMeshes.set(definition.id, { mesh, curve, definition });
  edgeRuntime.set(definition.id, { lastEvent: null, activity: 0 });
}

function createPulse(edge, event) {
  const color = STATUS_COLORS[event.status] || STATUS_COLORS.active;
  const count = reducedMotion ? 1 : 7;
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  for (let index = 0; index < count; index += 1) {
    positions[index * 3 + 2] = 1000;
    const intensity = index === 0 ? 1 : Math.max(0.18, 0.72 - index * 0.09);
    colors[index * 3] = color.r * intensity;
    colors[index * 3 + 1] = color.g * intensity;
    colors[index * 3 + 2] = color.b * intensity;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const cloud = new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      size: 0.065,
      vertexColors: true,
      transparent: true,
      opacity: 0.96,
      depthWrite: false,
      sizeAttenuation: true,
    }),
  );
  networkGroup.add(cloud);
  pulses.push({
    edge,
    event,
    cloud,
    count,
    progress: 0,
    speed: reducedMotion ? 1.1 : 0.30,
  });
  while (pulses.length > 64) {
    const removed = pulses.shift();
    networkGroup.remove(removed.cloud);
  }
  fields.runtimePackets.textContent = String(pulses.length);
}

function updatePulse(pulse, delta) {
  pulse.progress += delta * pulse.speed;
  const positions = pulse.cloud.geometry.attributes.position;
  for (let index = 0; index < pulse.count; index += 1) {
    const progress = pulse.progress - index * 0.021;
    if (progress < 0 || progress > 1) {
      positions.setXYZ(index, 0, 0, 1000);
      continue;
    }
    const point = pulse.edge.curve.getPointAt(clamp(progress, 0, 1));
    positions.setXYZ(index, point.x, point.y, point.z);
  }
  positions.needsUpdate = true;
  return pulse.progress <= 1.12;
}

function removeFinishedPulses(delta) {
  for (let index = pulses.length - 1; index >= 0; index -= 1) {
    if (!updatePulse(pulses[index], delta)) {
      networkGroup.remove(pulses[index].cloud);
      pulses.splice(index, 1);
    }
  }
  fields.runtimePackets.textContent = String(pulses.length);
}

function setNodeActivity(nodeId, event, amount) {
  const runtime = nodeRuntime.get(nodeId);
  if (!runtime) return;
  runtime.activity = Math.max(runtime.activity, amount);
  runtime.lastEvent = event;
}

function ingestEvent(event) {
  if (!event || !nodeRuntime.has(event.targetNode)) return false;
  const targetRuntime = nodeRuntime.get(event.targetNode);
  targetRuntime.incomingCount += event.sourceNode ? 1 : 0;
  targetRuntime.lastIncoming = event.sourceNode ? event : targetRuntime.lastIncoming;
  setNodeActivity(event.targetNode, event, 1);

  if (event.sourceNode && nodeRuntime.has(event.sourceNode)) {
    const sourceRuntime = nodeRuntime.get(event.sourceNode);
    sourceRuntime.outgoingCount += 1;
    sourceRuntime.lastOutgoing = event;
    setNodeActivity(event.sourceNode, event, 0.72);
    const edgeId = `${event.sourceNode}->${event.targetNode}`;
    const edge = edgeMeshes.get(edgeId);
    if (edge) {
      edgeRuntime.get(edgeId).lastEvent = event;
      edgeRuntime.get(edgeId).activity = 1;
      createPulse(edge, event);
    }
  }

  latestTrace = cleanText(event.traceId, "-").slice(0, 16);
  latestLatency = Number.isFinite(event.durationMs) ? event.durationMs : null;
  fields.runtimeTrace.textContent = latestTrace;
  fields.runtimeLatency.textContent = latestLatency === null ? "LIVE" : `${Math.round(latestLatency)} MS`;
  if (pinned || hovered) showInspector(pinned || hovered);
  return true;
}

function inspectorStatus(event) {
  const status = event ? cleanText(event.status, "idle") : "idle";
  const colors = {
    active: "#58e1e5",
    success: "#70e6a7",
    error: "#ff766e",
    idle: "#80a8ac",
  };
  inspector.style.setProperty("--status-color", colors[status] || colors.idle);
  return status.toUpperCase();
}

function showNodeInspector(nodeId) {
  const runtime = nodeRuntime.get(nodeId);
  if (!runtime) return;
  const event = runtime.lastEvent;
  fields.inspectorKind.textContent = runtime.definition.group;
  fields.inspectorTitle.textContent = runtime.definition.label;
  fields.inspectorStatus.textContent = inspectorStatus(event);
  fields.inspectorDescription.textContent = runtime.definition.description;
  fields.inspectorData.textContent = cleanText(event?.summary, "No data yet");
  fields.inspectorSource.textContent = event?.sourceNode ? nodeLabel(event.sourceNode) : "none";
  fields.inspectorTarget.textContent = event ? nodeLabel(event.targetNode) : "none";
  fields.inspectorTrace.textContent = cleanText(event?.traceId, "-").slice(0, 18);
  fields.inspectorLatency.textContent = Number.isFinite(event?.durationMs)
    ? `${Math.round(event.durationMs)} ms`
    : "live";
  inspector.hidden = false;
}

function showEdgeInspector(edgeId) {
  const edge = edgeMeshes.get(edgeId);
  if (!edge) return;
  const event = edgeRuntime.get(edgeId).lastEvent;
  fields.inspectorKind.textContent = "TRANSFER";
  fields.inspectorTitle.textContent = `${nodeLabel(edge.definition.source)} > ${nodeLabel(edge.definition.target)}`;
  fields.inspectorStatus.textContent = inspectorStatus(event);
  fields.inspectorDescription.textContent = "Directed runtime transfer between FRIDAY subsystems.";
  fields.inspectorData.textContent = cleanText(event?.summary, "No transfer recorded");
  fields.inspectorSource.textContent = nodeLabel(edge.definition.source);
  fields.inspectorTarget.textContent = nodeLabel(edge.definition.target);
  fields.inspectorTrace.textContent = cleanText(event?.traceId, "-").slice(0, 18);
  fields.inspectorLatency.textContent = Number.isFinite(event?.durationMs)
    ? `${Math.round(event.durationMs)} ms`
    : "live";
  inspector.hidden = false;
}

function showInspector(selection) {
  if (!selection) {
    inspector.hidden = true;
    return;
  }
  if (selection.kind === "node") showNodeInspector(selection.id);
  else showEdgeInspector(selection.id);
}

function applyEmphasis() {
  const selection = pinned || hovered;
  const selectedNode = selection?.kind === "node" ? selection.id : null;
  const selectedEdge = selection?.kind === "edge" ? selection.id : null;

  edgeMeshes.forEach((entry, edgeId) => {
    const related = selectedNode
      && (entry.definition.source === selectedNode || entry.definition.target === selectedNode);
    const runtime = edgeRuntime.get(edgeId);
    const active = runtime.activity > 0.02;
    entry.mesh.material.opacity = selection
      ? (related || selectedEdge === edgeId ? 0.72 : 0.025)
      : (active ? 0.14 + runtime.activity * 0.42 : 0.095);
    const eventColor = runtime.lastEvent
      ? (STATUS_COLORS[runtime.lastEvent.status] || STATUS_COLORS.active)
      : new THREE.Color("#43bec8");
    entry.mesh.material.color.copy(
      selectedEdge === edgeId ? new THREE.Color("#efffff") : eventColor,
    );
  });

  nodeMeshes.forEach((entry, nodeId) => {
    const selected = selectedNode === nodeId;
    entry.mesh.material.opacity = selection && !selected ? 0.34 : 0.92;
    entry.ring.material.opacity = selected ? 0.92 : (entry.definition.core ? 0.62 : 0.20);
    entry.orbit.material.opacity = selected ? 0.68 : (entry.definition.core ? 0.34 : 0.11);
  });
}

function hitTest(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(interactiveObjects, false)[0];
  if (hit) return { kind: hit.object.userData.kind, id: hit.object.userData.id };

  let nearest = null;
  nodeMeshes.forEach((entry, nodeId) => {
    entry.mesh.getWorldPosition(projected);
    projected.project(camera);
    if (projected.z < -1 || projected.z > 1) return;
    const screenX = rect.left + (projected.x * 0.5 + 0.5) * rect.width;
    const screenY = rect.top + (-projected.y * 0.5 + 0.5) * rect.height;
    const distance = Math.hypot(clientX - screenX, clientY - screenY);
    if (distance <= 14 && (!nearest || distance < nearest.distance)) {
      nearest = { kind: "node", id: nodeId, distance };
    }
  });
  return nearest ? { kind: nearest.kind, id: nearest.id } : null;
}

function updateHover(clientX, clientY) {
  const next = hitTest(clientX, clientY);
  const changed = next?.kind !== hovered?.kind || next?.id !== hovered?.id;
  hovered = next;
  canvas.style.cursor = next ? "pointer" : "grab";
  if (!pinned) showInspector(hovered);
  if (changed) applyEmphasis();
}

function resetCamera() {
  yaw = 0;
  pitch = -0.05;
  camera.position.set(initialCamera.x, initialCamera.y, defaultCameraDistance());
  networkGroup.rotation.set(pitch, yaw, 0);
  brainGroup.rotation.set(pitch, yaw, 0);
  pinned = null;
  hovered = null;
  inspector.hidden = true;
  applyEmphasis();
}

function resize() {
  const width = Math.max(1, shell.clientWidth);
  const height = Math.max(1, shell.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  camera.position.z = defaultCameraDistance();
}

function updateLabels() {
  const width = shell.clientWidth;
  const height = shell.clientHeight;
  const selectedNode = (pinned || hovered)?.kind === "node"
    ? (pinned || hovered).id
    : null;
  nodeMeshes.forEach((entry, nodeId) => {
    entry.mesh.getWorldPosition(projected);
    projected.project(camera);
    const behind = projected.z < -1 || projected.z > 1;
    entry.label.dataset.hidden = behind ? "true" : "false";
    entry.label.dataset.visible = String(nodeId === "reasoning.llm" || selectedNode === nodeId);
    entry.label.dataset.align = projected.x > 0.62 ? "right" : "left";
    entry.label.style.left = `${(projected.x * 0.5 + 0.5) * width}px`;
    entry.label.style.top = `${(-projected.y * 0.5 + 0.5) * height}px`;
  });
}

function animate() {
  if (!visible) return;
  const delta = Math.min(clock.getDelta(), 0.05);
  elapsed += delta;
  if (!paused) {
    if (!reducedMotion && !dragStart) {
      const driftYaw = Math.sin(elapsed * 0.22) * 0.035;
      const driftPitch = Math.cos(elapsed * 0.18) * 0.014;
      networkGroup.rotation.set(pitch + driftPitch, yaw + driftYaw, 0);
      brainGroup.rotation.set(pitch + driftPitch, yaw + driftYaw, 0);
    }
    if (!reducedMotion) {
      nodeMeshes.forEach((entry, nodeId) => {
        const runtime = nodeRuntime.get(nodeId);
        const idle = state === "sleeping" ? 0.004 : 0.016;
        const phase = elapsed * 1.4 + entry.mesh.position.y * 0.3;
        const activityScale = runtime.activity * 0.10;
        const scale = 1 + Math.sin(phase) * idle + activityScale;
        entry.mesh.scale.setScalar(scale);
        entry.ring.rotation.z += delta * (entry.definition.core ? 0.35 : 0.12);
        entry.orbit.rotation.y += delta * (entry.definition.core ? 0.28 : 0.09);
        runtime.activity = Math.max(0, runtime.activity - delta * 0.44);
        const activityColor = runtime.lastEvent && runtime.activity > 0.01
          ? (STATUS_COLORS[runtime.lastEvent.status] || STATE_COLORS[state])
          : entry.baseColor;
        entry.mesh.material.color.lerp(activityColor, Math.min(1, delta * 3));
        entry.mesh.material.emissive.lerp(activityColor, Math.min(1, delta * 4));
        entry.mesh.material.emissiveIntensity = (
          (entry.definition.core ? 0.76 : 0.42) + runtime.activity * 1.55
        );
      });
      if (brainTissue) {
        const baseOpacity = state === "sleeping" ? 0.24 : 0.64;
        brainTissue.material.opacity = baseOpacity + Math.sin(elapsed * 0.75) * 0.025;
      }
    }
    const selection = pinned || hovered;
    edgeRuntime.forEach((runtime, edgeId) => {
      runtime.activity = Math.max(0, runtime.activity - delta * 0.32);
      if (selection) return;
      const entry = edgeMeshes.get(edgeId);
      entry.mesh.material.opacity = 0.095 + runtime.activity * 0.46;
      const targetColor = runtime.lastEvent && runtime.activity > 0.01
        ? (STATUS_COLORS[runtime.lastEvent.status] || STATUS_COLORS.active)
        : new THREE.Color("#43bec8");
      entry.mesh.material.color.lerp(targetColor, Math.min(1, delta * 5));
    });
    removeFinishedPulses(delta);
  }

  renderer.render(scene, camera);
  updateLabels();
  frameCount += 1;
  const now = performance.now();
  if (now - fpsWindowStart >= 1000) {
    measuredFps = Math.round((frameCount * 1000) / (now - fpsWindowStart));
    fields.runtimeFps.textContent = String(measuredFps);
    frameCount = 0;
    fpsWindowStart = now;
  }
}

function initialize(payload) {
  if (ready || !payload?.nodes?.length || !payload?.edges?.length) return diagnostics();
  topology = payload;
  payload.layers.forEach(createLayer);
  createBrainTissue();
  createCircuitLattice();
  createCorticalFolds();
  payload.nodes.forEach(createNode);
  createDendrites();
  payload.edges.forEach(createEdge);
  resize();
  resetCamera();
  ready = true;
  frameCount = 0;
  fpsWindowStart = performance.now();
  renderError.hidden = true;
  renderer.setAnimationLoop(animate);
  window.dispatchEvent(new CustomEvent("friday-neural-ready"));
  return diagnostics();
}

function setState(nextState) {
  state = STATE_COLORS[nextState] ? nextState : "online";
  shell.dataset.state = state;
  fields.runtimeState.textContent = state.toUpperCase();
  fields.liveState.textContent = state === "online" ? "LIVE" : state.toUpperCase();
  return state;
}

function clearTelemetry() {
  pulses.splice(0).forEach((pulse) => networkGroup.remove(pulse.cloud));
  nodeRuntime.forEach((runtime) => {
    runtime.activity = 0;
    runtime.incomingCount = 0;
    runtime.outgoingCount = 0;
    runtime.lastEvent = null;
    runtime.lastIncoming = null;
    runtime.lastOutgoing = null;
  });
  edgeRuntime.forEach((runtime) => {
    runtime.lastEvent = null;
    runtime.activity = 0;
  });
  latestTrace = "-";
  latestLatency = null;
  fields.runtimeTrace.textContent = "-";
  fields.runtimePackets.textContent = "0";
  fields.runtimeLatency.textContent = "LIVE";
  inspector.hidden = true;
  applyEmphasis();
  return true;
}

function setVisible(nextVisible) {
  visible = Boolean(nextVisible);
  if (visible) clock.start();
  return visible;
}

function togglePaused() {
  paused = !paused;
  pauseButton.setAttribute("aria-pressed", String(paused));
  pauseButton.setAttribute("aria-label", paused ? "Resume neural animation" : "Pause neural animation");
  fields.liveState.textContent = paused ? "PAUSED" : (state === "online" ? "LIVE" : state.toUpperCase());
  return paused;
}

function diagnostics() {
  const context = renderer.getContext();
  return {
    ready,
    webgl: Boolean(context),
    nodeCount: nodeMeshes.size,
    edgeCount: edgeMeshes.size,
    pulseCount: pulses.length,
    renderCalls: renderer.info.render.calls,
    triangles: renderer.info.render.triangles,
    fps: measuredFps,
    canvasWidth: canvas.width,
    canvasHeight: canvas.height,
    state,
  };
}

canvas.addEventListener("pointerdown", (event) => {
  dragStart = { x: event.clientX, y: event.clientY, yaw, pitch };
  dragMoved = false;
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (dragStart) {
    const dx = event.clientX - dragStart.x;
    const dy = event.clientY - dragStart.y;
    dragMoved = dragMoved || Math.hypot(dx, dy) > 4;
    if (dragMoved) {
      yaw = dragStart.yaw + dx * 0.006;
      pitch = clamp(dragStart.pitch + dy * 0.004, -0.62, 0.62);
      networkGroup.rotation.set(pitch, yaw, 0);
      brainGroup.rotation.set(pitch, yaw, 0);
      canvas.style.cursor = "grabbing";
    }
    return;
  }
  updateHover(event.clientX, event.clientY);
});

canvas.addEventListener("pointerup", (event) => {
  if (!dragMoved) {
    const selection = hitTest(event.clientX, event.clientY);
    pinned = selection && selection.kind === pinned?.kind && selection.id === pinned?.id
      ? null
      : selection;
    showInspector(pinned || hovered);
    applyEmphasis();
  }
  dragStart = null;
  dragMoved = false;
  canvas.style.cursor = hovered ? "pointer" : "grab";
});

canvas.addEventListener("pointerleave", () => {
  if (!dragStart) {
    hovered = null;
    if (!pinned) inspector.hidden = true;
    applyEmphasis();
  }
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  camera.position.z = clamp(camera.position.z + event.deltaY * 0.012, 12, 40);
}, { passive: false });

pauseButton.addEventListener("click", togglePaused);
resetButton.addEventListener("click", resetCamera);
window.addEventListener("resize", resize);

createBackdrop();
resize();
renderer.render(scene, camera);

window.fridayNeural = {
  initialize,
  ingestEvent,
  setState,
  clearTelemetry,
  setVisible,
  togglePaused,
  resetCamera,
  diagnostics,
};

window.addEventListener("error", () => {
  renderError.hidden = false;
});

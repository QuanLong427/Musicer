import * as THREE from "three";

// ==========================================
// Full-screen Starfield Background
// ==========================================
const BASE_SPEED = 0.0001;

export function initVisualizer(container: HTMLElement): () => void {
  // Scene
  const scene = new THREE.Scene();
  const bgColor = new THREE.Color(0x050510);
  scene.background = bgColor;
  scene.fog = new THREE.FogExp2(bgColor, 0.0005);

  // Camera
  const camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    2000
  );
  camera.position.z = 500;

  // Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  // Stars with vertex colors
  const particleCount = 5000;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount; i++) {
    // Positions - uniformly distributed in spherical space
    positions[i * 3] = (Math.random() - 0.5) * 2000;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 2000;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 2000;

    // Vertex colors: 60% blue-white, 25% white, 13% warm yellow, 2% purple
    const rand = Math.random();
    let r: number, g: number, b: number;

    if (rand < 0.6) {
      // 60% blue-white (hot stars)
      r = 0.6 + Math.random() * 0.3;
      g = 0.8 + Math.random() * 0.2;
      b = 1.0;
    } else if (rand < 0.85) {
      // 25% white/silver
      r = 0.9 + Math.random() * 0.1;
      g = 0.9 + Math.random() * 0.1;
      b = 0.9 + Math.random() * 0.1;
    } else if (rand < 0.98) {
      // 13% warm yellow/orange (cooler stars)
      r = 1.0;
      g = 0.7 + Math.random() * 0.2;
      b = 0.4 + Math.random() * 0.2;
    } else {
      // 2% dreamy purple/pink
      r = 0.9 + Math.random() * 0.1;
      g = 0.4 + Math.random() * 0.2;
      b = 0.8 + Math.random() * 0.2;
    }

    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }

  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    vertexColors: true,
    size: 1.0,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
  });

  const starSystem = new THREE.Points(geometry, material);
  scene.add(starSystem);

  // Meteors
  const meteors: THREE.Mesh[] = [];
  const meteorMaterial = new THREE.MeshBasicMaterial({
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
  });

  const meteorDir = new THREE.Vector3(-1, -0.8, -0.2).normalize();
  const meteorQuaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    meteorDir
  );

  const resetMeteor = (meteor: THREE.Mesh) => {
    meteor.position.set(
      Math.random() * 2000,
      Math.random() * 1000 + 500,
      Math.random() * 2000 - 1000
    );
  };

  for (let i = 0; i < 12; i++) {
    const length = 40 + Math.random() * 50;
    const thickness = 0.4 + Math.random() * 0.4;

    const mGeometry = new THREE.CylinderGeometry(thickness, 0, length, 4, 1);
    mGeometry.translate(0, -length / 2, 0);

    // Vertex color gradient: head bright, tail dark
    const count = mGeometry.attributes.position.count;
    const mColors = new Float32Array(count * 3);
    const mPositions = mGeometry.attributes.position.array;

    for (let j = 0; j < count; j++) {
      const y = mPositions[j * 3 + 1]; // y range: 0 to -length
      const ratio = 1.0 - Math.abs(y / length);
      mColors[j * 3] = ratio;
      mColors[j * 3 + 1] = ratio;
      mColors[j * 3 + 2] = ratio;
    }
    mGeometry.setAttribute("color", new THREE.BufferAttribute(mColors, 3));

    const meteor = new THREE.Mesh(mGeometry, meteorMaterial);
    meteor.quaternion.copy(meteorQuaternion);
    meteor.userData = {
      speed: 0.5 + Math.random() * 1.5,
    };

    resetMeteor(meteor);
    scene.add(meteor);
    meteors.push(meteor);
  }

  // Animation
  let animationId: number;
  let frameCount = 0;

  const animate = () => {
    animationId = requestAnimationFrame(animate);
    frameCount++;

    // Skip every other frame to reduce computation
    if (frameCount % 2 !== 0) {
      renderer.render(scene, camera);
      return;
    }

    starSystem.rotation.y += BASE_SPEED * 2; // Double speed to compensate for frame skip
    starSystem.rotation.x += BASE_SPEED * 0.6;

    // Meteor animation (boundary check every 6 frames = 3 seconds at 30fps)
    for (const meteor of meteors) {
      meteor.position.addScaledVector(meteorDir, meteor.userData.speed * 2);
      if (frameCount % 6 === 0 && (meteor.position.y < -1000 || meteor.position.x < -1000)) {
        resetMeteor(meteor);
      }
    }

    renderer.render(scene, camera);
  };

  animate();

  // Resize
  const onResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  };

  window.addEventListener("resize", onResize);

  // Cleanup
  return () => {
    cancelAnimationFrame(animationId);
    window.removeEventListener("resize", onResize);
    renderer.dispose();
    geometry.dispose();
    material.dispose();
    meteorMaterial.dispose();
    for (const meteor of meteors) {
      meteor.geometry.dispose();
    }
    if (container.contains(renderer.domElement)) {
      container.removeChild(renderer.domElement);
    }
  };
}

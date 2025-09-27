import * as THREE from 'https://unpkg.com/three@0.152.2/build/three.module.js';

const ROTATION_SPEED = 0.0006;
const EARTH_TEXTURE = 'https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg';
const MOON_TEXTURE = 'https://threejs.org/examples/textures/moon_1024.jpg';

const canvas = document.getElementById('globe-canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 0, 3);

const ambient = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambient);
const dir = new THREE.DirectionalLight(0xffffff, 0.8);
dir.position.set(5, 3, 5);
scene.add(dir);

const loader = new THREE.TextureLoader();
loader.crossOrigin = '';

let earth, moon;
let moonAngle = 0;

loader.load(EARTH_TEXTURE, (earthTexture) => {
  const earthMaterial = new THREE.MeshPhongMaterial({ map: earthTexture, shininess: 6 });
  const earthGeometry = new THREE.SphereGeometry(1, 64, 64);
  earth = new THREE.Mesh(earthGeometry, earthMaterial);
  scene.add(earth);
  earth.rotation.z = THREE.MathUtils.degToRad(23.5 * 0.4);

  const glowGeometry = new THREE.SphereGeometry(1.02, 64, 64);
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0x00ffff,
    transparent: true,
    opacity: 0.3,
    blending: THREE.AdditiveBlending,
    side: THREE.BackSide
  });
  const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
  scene.add(glowMesh);

  const orbitGeometry = new THREE.RingGeometry(1.6, 1.62, 128);
  const orbitMaterial = new THREE.MeshBasicMaterial({
    color: 0x00ffff,
    transparent: true,
    opacity: 0.25,
    side: THREE.DoubleSide
  });
  const orbit = new THREE.Mesh(orbitGeometry, orbitMaterial);
  orbit.rotation.x = Math.PI / 2;
  scene.add(orbit);

  loader.load(MOON_TEXTURE, (moonTexture) => {
    const moonMaterial = new THREE.MeshPhongMaterial({ map: moonTexture });
    const moonGeometry = new THREE.SphereGeometry(0.27, 32, 32);
    moon = new THREE.Mesh(moonGeometry, moonMaterial);
    scene.add(moon);
  });

  let lastTime = performance.now();
  function animate(now) {
    const dt = now - lastTime;
    lastTime = now;

    earth.rotation.y += ROTATION_SPEED * dt;
    if (moon) {
      moonAngle += 0.002;
      moon.position.set(Math.cos(moonAngle) * 1.6, 0, Math.sin(moonAngle) * 1.6);
    }
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
});

window.addEventListener('resize', () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
});

// Stars
window.addEventListener('DOMContentLoaded', () => {
  const globeContainer = document.body;
  const starCanvas = document.createElement('canvas');
  starCanvas.width = window.innerWidth;
  starCanvas.height = window.innerHeight;
  starCanvas.style.position = 'absolute';
  starCanvas.style.top = '0';
  starCanvas.style.left = '0';
  starCanvas.style.zIndex = '1';
  starCanvas.style.pointerEvents = 'none';
  globeContainer.prepend(starCanvas);

  const ctx = starCanvas.getContext('2d');
  let stars = [];
  function createStars(count) {
    stars = [];
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * starCanvas.width,
        y: Math.random() * starCanvas.height,
        size: Math.random() * 2 + 0.5,
        speedX: (Math.random() - 0.5) * 0.1,
        speedY: (Math.random() - 0.5) * 0.1,
        glow: `hsl(${Math.random() * 60 + 180}, 100%, 80%)`
      });
    }
  }
  function drawStars() {
    ctx.clearRect(0, 0, starCanvas.width, starCanvas.height);
    stars.forEach(star => {
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
      ctx.shadowBlur = 6;
      ctx.shadowColor = star.glow;
      ctx.fillStyle = star.glow;
      ctx.fill();
      star.x += star.speedX;
      star.y += star.speedY;
      if (star.x < 0) star.x = starCanvas.width;
      if (star.x > starCanvas.width) star.x = 0;
      if (star.y < 0) star.y = starCanvas.height;
      if (star.y > starCanvas.height) star.y = 0;
    });
  }
  function animateStars() {
    drawStars();
    requestAnimationFrame(animateStars);
  }
  createStars(80);
  animateStars();
  window.addEventListener('resize', () => {
    starCanvas.width = window.innerWidth;
    starCanvas.height = window.innerHeight;
    createStars(80);
  });
});

// Button click animations
document.getElementById('start-btn').addEventListener('click', () => {
  document.getElementById('earth-container').classList.add('moved', 'floating');
  document.getElementById('intro-card').classList.add('hidden');
  setTimeout(() => {
    const info = document.getElementById('info-section');
    info.style.display = 'block';
    setTimeout(() => info.classList.add('visible'), 50);
  }, 500);
});

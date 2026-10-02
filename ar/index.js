/* globals XR8 XRExtras THREE */

import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { configManager } from './configManager.js';
import { modelRegistry } from './modelRegistry.js';
import { targetTracker } from './targetTracker.js';
import * as THREE from 'three';

THREE.ColorManagement.enabled = false;

let scene = null;
let camera = null;
let renderer = null;

const initXrScene = ({ scene: xrScene, camera: xrCamera, renderer: xrRenderer }) => {
  scene = xrScene;
  camera = xrCamera;
  renderer = xrRenderer;

  targetTracker.setScene(scene);

  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
  directionalLight.position.set(0, 5, 5);
  directionalLight.castShadow = true;
  directionalLight.shadow.mapSize.width = 1024;
  directionalLight.shadow.mapSize.height = 1024;
  directionalLight.shadow.camera.near = 0.1;
  directionalLight.shadow.camera.far = 20;
  directionalLight.shadow.camera.left = -5;
  directionalLight.shadow.camera.right = 5;
  directionalLight.shadow.camera.top = 5;
  directionalLight.shadow.camera.bottom = -5;
  scene.add(directionalLight);

  // Add a ground plane for shadows (invisible)
  const groundGeometry = new THREE.PlaneGeometry(100, 100);
  const groundMaterial = new THREE.ShadowMaterial({ opacity: 0.3 });
  const ground = new THREE.Mesh(groundGeometry, groundMaterial);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = 0;
  ground.receiveShadow = true;
  scene.add(ground);

  camera.position.set(0, 0, 0);

  // Preload models once config is ready
  configManager.onChange(snapshot => {
    if (snapshot.products.size > 0) {
      modelRegistry.preload(Array.from(snapshot.products.values())).catch(console.error);
    }
  });

  console.log('[AR] Scene initialized');
};

const onStart = ({ canvas }) => {
  const { scene: xrScene, camera: xrCamera, renderer: xrRenderer } = XR8.Threejs.xrScene();
  initXrScene({ scene: xrScene, camera: xrCamera, renderer: xrRenderer });

  canvas.addEventListener('touchmove', (event) => {
    event.preventDefault();
  }, { passive: false });

  XR8.XrController.updateCameraProjectionMatrix({
    origin: camera.position,
    facing: camera.quaternion,
  });
};

const setupEventListeners = () => {
  XR8.XrController.addEventListener('reality.imagefound', (event) => {
    targetTracker.onTargetFound(event);
  });

  XR8.XrController.addEventListener('reality.imageupdated', (event) => {
    targetTracker.onTargetUpdated(event);
  });

  XR8.XrController.addEventListener('reality.imagelost', (event) => {
    targetTracker.onTargetLost(event);
  });
};

const configureTargets = () => {
  // Pass the CLI-generated target config through untouched (especially
  // `properties`: crop + geometry). Never invent width/height here.
  const targetDataArray = configManager.espacios.map(entry => {
    const targetConfig = entry.targetConfig;
    const codigo = entry.espacio.codigo;
    return {
      type: targetConfig.type || 'PLANAR',
      name: targetConfig.name || codigo,
      imagePath: targetConfig.imagePath || `targets/${codigo}_luminance.png`,
      properties: { ...targetConfig.properties },
    };
  });

  XR8.XrController.configure({
    disableWorldTracking: true,
    imageTargetData: targetDataArray,
  });
};

const onxrloaded = () => {
  // Wait for config before configuring targets
  const waitForConfig = () => {
    if (configManager.ready && configManager.espacios.length > 0) {
      configureTargets();
      startXR();
    } else {
      setTimeout(waitForConfig, 50);
    }
  };
  waitForConfig();
};

const startXR = () => {
  XR8.addCameraPipelineModules([
    XR8.GlTextureRenderer.pipelineModule(),
    XR8.Threejs.pipelineModule(),
    XR8.XrController.pipelineModule(),
    XRExtras.FullWindowCanvas.pipelineModule(),
    XRExtras.Loading.pipelineModule(),
    XRExtras.RuntimeError.pipelineModule(),
    {
      name: 'ar-engine',
      onStart,
      listeners: [
        { event: 'reality.imagefound', process: (e) => targetTracker.onTargetFound(e) },
        { event: 'reality.imageupdated', process: (e) => targetTracker.onTargetUpdated(e) },
        { event: 'reality.imagelost', process: (e) => targetTracker.onTargetLost(e) },
      ],
    },
  ]);

    XR8.run({
      canvas: document.getElementById('camerafeed'),
      allowedDevices: XR8.XrConfig.device().MOBILE,
      cameraConfig: { direction: XR8.XrConfig.camera().BACK },
    });
  };

const load = () => {
  XRExtras.Loading.showLoading({ onxrloaded });
};

if (window.XRExtras) {
  load();
} else {
  window.addEventListener('xrextrasloaded', load);
}

console.log('[AR Engine] Initialized, loading config from API...');
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useCargoStore } from '../../store/useCargoStore.js';
import { CONTAINERS, CARGO_TYPES } from '../../constants';

/**
 * 純 Three.js 版本的 3D 容器（不使用 React Three Fiber）
 *
 * 設計策略：
 *   - 只在 mount 時建立一次 scene/camera/renderer/controls（用 ref 保存）
 *   - 用 useCargoStore.subscribe() 訂閱 store 變化，直接操作 Three.js 物件
 *     不透過 React state，避免 React 重渲染干擾 Three.js 內部狀態
 *   - 對應 prototype02.html 的 initThree / drawContainer / renderPackedItems /
 *     toggleXray / setView / updateVisibility / onMouseMove
 *
 * 為什麼用 ref 而不是 state：
 *   Three.js 物件是「可變的」（mutable），React state 假設物件不可變。
 *   把 Three.js 物件放進 state 會導致 React 試圖追蹤它的變化、製造重渲染。
 */
export default function Container3D() {
  const mountRef = useRef(null);

  // Three.js 物件（用 ref 保存可變狀態）
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const containerMeshRef = useRef(null);
  const cargoMeshesRef = useRef([]);
  const animationIdRef = useRef(null);

  // hover tooltip 元素
  const tooltipRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // ====== 1. 建立 scene / camera / renderer ======
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const w = mount.clientWidth;
    const h = mount.clientHeight;
    const camera = new THREE.PerspectiveCamera(45, w / h, 10, 100000);
    camera.position.set(15000, 10000, 15000);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controlsRef.current = controls;

    // 燈光
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
    dirLight.position.set(10000, 15000, 8000);
    scene.add(dirLight);
    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
    dirLight2.position.set(-5000, 5000, -5000);
    scene.add(dirLight2);

    // ====== 2. 第一次繪製貨櫃 ======
    drawContainer();

    // ====== 3. 動畫迴圈 ======
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // ====== 4. resize ======
    const onResize = () => {
      const newW = mount.clientWidth;
      const newH = mount.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener('resize', onResize);

    // ====== 5. 滑鼠 hover ======
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(cargoMeshesRef.current);
      const tooltip = tooltipRef.current;
      if (!tooltip) return;
      if (intersects.length > 0) {
        const item = intersects[0].object.userData.item;
        const typeLabel = CARGO_TYPES[item.type]?.label || item.type;
        tooltip.innerHTML = `
          <strong>${item.id}</strong><br>
          類型：${typeLabel}<br>
          尺寸：${item.L}×${item.W}×${item.H} mm${item.rotated ? ' 🔄已旋轉' : ''}<br>
          重量：${item.weight} kg<br>
          位置：(${item.x}, ${item.y}, ${item.z})<br>
          ${item.stackable ? '可堆疊' : '⚠ 不可堆疊'}
        `;
        tooltip.style.display = 'block';
        tooltip.style.left = (e.clientX + 12) + 'px';
        tooltip.style.top = (e.clientY + 12) + 'px';
      } else {
        tooltip.style.display = 'none';
      }
    };
    renderer.domElement.addEventListener('mousemove', onMouseMove);

    // ====== 6. 訂閱 store 變化（取代 R3F 的 reactive 行為）======
    let prevState = {
      containerType: null,
      packedItems: null,
      currentStep: -1,
      xrayMode: null,
      viewMode: null,
    };
    const unsubscribe = useCargoStore.subscribe((state) => {
      // 貨櫃類型變了 → 重畫貨櫃
      if (state.containerType !== prevState.containerType) {
        drawContainer();
      }
      // 裝箱結果變了 → 重新渲染所有箱子
      if (state.packedItems !== prevState.packedItems) {
        renderPackedItems(state.packedItems);
      }
      // currentStep 變了 → 顯示前 N 件
      if (state.currentStep !== prevState.currentStep ||
          state.packedItems !== prevState.packedItems) {
        updateVisibility(state.currentStep);
      }
      // X 光模式切換
      if (state.xrayMode !== prevState.xrayMode) {
        toggleXray(state.xrayMode);
      }
      // 視角模式切換
      if (state.viewMode !== prevState.viewMode) {
        applyViewMode(state.viewMode);
      }
      prevState = {
        containerType: state.containerType,
        packedItems: state.packedItems,
        currentStep: state.currentStep,
        xrayMode: state.xrayMode,
        viewMode: state.viewMode,
      };
    });

    // 啟動時也要套用初始狀態（避免初次掛載漏掉）
    const initialState = useCargoStore.getState();
    if (initialState.packedItems.length > 0) {
      renderPackedItems(initialState.packedItems);
      updateVisibility(initialState.currentStep);
    }

    // ====== 清理 ======
    return () => {
      cancelAnimationFrame(animationIdRef.current);
      window.removeEventListener('resize', onResize);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      unsubscribe();
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ====== drawContainer：搬自 prototype02 ======
  function drawContainer() {
    const scene = sceneRef.current;
    if (!scene) return;
    const containerType = useCargoStore.getState().containerType;
    const c = CONTAINERS[containerType];

    // 移除舊的（包括網格與軸線）
    if (containerMeshRef.current) {
      scene.remove(containerMeshRef.current);
      containerMeshRef.current = null;
    }
    // 清理舊的 helper（用 name 標記找出來）
    const oldHelpers = scene.children.filter(
      o => o.userData?.helper === true
    );
    oldHelpers.forEach(o => scene.remove(o));

    // 半透明線框
    const group = new THREE.Group();
    const geo = new THREE.BoxGeometry(c.L, c.H, c.W);
    const edges = new THREE.EdgesGeometry(geo);
    const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 });
    const line = new THREE.LineSegments(edges, lineMat);
    line.position.set(c.L / 2, c.H / 2, c.W / 2);
    group.add(line);

    // 半透明面
    const faceMat = new THREE.MeshBasicMaterial({
      color: 0x88aacc, transparent: true, opacity: 0.05,
      side: THREE.DoubleSide, depthWrite: false,
    });
    const faceMesh = new THREE.Mesh(geo, faceMat);
    faceMesh.position.set(c.L / 2, c.H / 2, c.W / 2);
    group.add(faceMesh);

    scene.add(group);
    containerMeshRef.current = group;

    // 網格
    const gridSize = Math.max(c.L, c.W) * 1.2;
    const gridHelper = new THREE.GridHelper(gridSize, 24, 0x666666, 0x444444);
    gridHelper.position.set(c.L / 2, 0, c.W / 2);
    gridHelper.userData.helper = true;
    scene.add(gridHelper);

    // 座標軸
    const axesHelper = new THREE.AxesHelper(2000);
    axesHelper.userData.helper = true;
    scene.add(axesHelper);

    // 門口指示器（X = L 端）
    const doorGroup = new THREE.Group();
    // 門面
    const doorGeo = new THREE.PlaneGeometry(c.W, c.H);
    const doorMat = new THREE.MeshBasicMaterial({
      color: 0xff3b30, transparent: true, opacity: 0.12,
      side: THREE.DoubleSide, depthWrite: false,
    });
    const doorPlane = new THREE.Mesh(doorGeo, doorMat);
    doorPlane.rotation.y = Math.PI / 2;
    doorPlane.position.set(c.L, c.H / 2, c.W / 2);
    doorGroup.add(doorPlane);
    // 門框
    const doorEdgeGeo = new THREE.EdgesGeometry(doorGeo);
    const doorEdgeMat = new THREE.LineBasicMaterial({ color: 0xff3b30, linewidth: 3 });
    const doorEdge = new THREE.LineSegments(doorEdgeGeo, doorEdgeMat);
    doorEdge.rotation.y = Math.PI / 2;
    doorEdge.position.set(c.L, c.H / 2, c.W / 2);
    doorGroup.add(doorEdge);
    // 入庫箭頭
    const arrowDir = new THREE.Vector3(-1, 0, 0);
    const arrowOrigin = new THREE.Vector3(c.L + 1500, c.H / 2, c.W / 2);
    const arrow = new THREE.ArrowHelper(arrowDir, arrowOrigin, 1200, 0xff3b30, 400, 200);
    doorGroup.add(arrow);

    group.add(doorGroup);

    // 更新 controls target
    if (controlsRef.current) {
      controlsRef.current.target.set(c.L / 2, c.H / 2, c.W / 2);
    }

    // 既有的箱子也要重新渲染（貨櫃換大小可能要調位置）
    const state = useCargoStore.getState();
    if (state.packedItems.length > 0) {
      renderPackedItems(state.packedItems);
      updateVisibility(state.currentStep);
    }
  }

  // ====== renderPackedItems：搬自 prototype02 ======
  function renderPackedItems(packedItems) {
    const scene = sceneRef.current;
    if (!scene) return;

    // 清除舊 mesh
    cargoMeshesRef.current.forEach(m => {
      scene.remove(m);
      // 清理 geometry/material 避免記憶體洩漏
      m.geometry?.dispose();
      m.material?.dispose();
      m.children.forEach(child => {
        child.geometry?.dispose();
        child.material?.dispose();
      });
    });
    cargoMeshesRef.current = [];

    // 取得當前 X 光狀態（重新渲染時要套用）
    const xrayMode = useCargoStore.getState().xrayMode;

    packedItems.forEach((item, idx) => {
      const geo = new THREE.BoxGeometry(item.L, item.H, item.W);
      const colorHex = CARGO_TYPES[item.type]?.hex || CARGO_TYPES.normal.hex;

      const mat = new THREE.MeshLambertMaterial({
        color: colorHex,
        transparent: xrayMode,
        opacity: xrayMode ? 0.3 : 1.0,
        depthWrite: !xrayMode,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(
        item.x + item.L / 2,
        item.z + item.H / 2,
        item.y + item.W / 2
      );

      // 黑色邊線
      const edges = new THREE.EdgesGeometry(geo);
      const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({
        color: 0x000000, opacity: 0.4, transparent: true, depthWrite: false,
      }));
      mesh.add(line);

      // 不可堆疊：紅色頂面
      if (!item.stackable) {
        const topGeo = new THREE.PlaneGeometry(item.L * 0.9, item.W * 0.9);
        const topMat = new THREE.MeshBasicMaterial({
          color: 0xff3b30, transparent: true, opacity: 0.5,
          side: THREE.DoubleSide, depthWrite: false,
        });
        const topPlane = new THREE.Mesh(topGeo, topMat);
        topPlane.rotation.x = -Math.PI / 2;
        topPlane.position.y = item.H / 2 + 5;
        mesh.add(topPlane);
      }

      mesh.userData = { item, index: idx };
      scene.add(mesh);
      cargoMeshesRef.current.push(mesh);
    });
  }

  // ====== updateVisibility（依播放進度顯示前 N 件）======
  function updateVisibility(currentStep) {
    cargoMeshesRef.current.forEach((m, i) => {
      m.visible = i < currentStep;
    });
  }

  // ====== toggleXray ======
  function toggleXray(xrayMode) {
    cargoMeshesRef.current.forEach(m => {
      m.material.transparent = xrayMode;
      m.material.opacity = xrayMode ? 0.3 : 1.0;
      m.material.depthWrite = !xrayMode;
      m.material.needsUpdate = true;
    });
  }

  // ====== applyViewMode（視角切換）======
  function applyViewMode(mode) {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;

    const containerType = useCargoStore.getState().containerType;
    const c = CONTAINERS[containerType];
    const cx = c.L / 2, cy = c.H / 2, cz = c.W / 2;

    switch (mode) {
      case 'top':
        camera.position.set(cx, c.H * 4, cz);
        break;
      case 'side':
        camera.position.set(cx, cy, cz + c.W * 5);
        break;
      case 'front':
        camera.position.set(c.L * 1.5, cy, cz);
        break;
      case 'perspective':
      default:
        camera.position.set(c.L * 1.2, c.H * 2.5, c.W * 4);
        break;
    }
    controls.target.set(cx, cy, cz);
    controls.update();
  }

  return (
    <>
      <div
        ref={mountRef}
        style={{ width: '100%', height: '100%' }}
      />
      {/* hover tooltip — 用原生 DOM，避免 React state 干擾每幀更新 */}
      <div
        ref={tooltipRef}
        style={{
          position: 'absolute',
          background: 'rgba(0,0,0,0.85)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: 6,
          fontSize: 12,
          pointerEvents: 'none',
          display: 'none',
          zIndex: 20,
          lineHeight: 1.5,
        }}
      />
    </>
  );
}

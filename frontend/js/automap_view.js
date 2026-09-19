/**
 * synQ Industrial Robotics Operating System — AutoMap Studio
 * Scan-to-Digital-Twin Pipeline for Real-World Warehouse Deployment
 *
 * Workflow:
 * SCAN → MAPPING → 3D RECONSTRUCTION → DETECTION → REVIEW/LABEL → MAP GENERATED → READY FOR OPERATION
 */

(function (window) {
  'use strict';

  let currentStep = 'SCAN'; // SCAN, MAPPING, 3D_RECONSTRUCTION, DETECTION, REVIEW_LABEL, MAP_GENERATED, READY_FOR_OPERATION
  let activeFilter = 'ALL';
  let detectionsList = [];
  let selectedDetectionId = null;
  let threeScene = null;
  let threeCamera = null;
  let threeRenderer = null;
  let threeControls = null;
  let pointCloudMesh = null;
  let bboxGroup = null;
  let animationFrameId = null;
  let activeViewMode = '3D'; // '3D' or '2D'

  const STEP_SEQUENCE = [
    { key: 'SCAN', label: '1. Scan', desc: 'LiDAR & Pose Recording' },
    { key: 'MAPPING', label: '2. Mapping', desc: 'Trajectory & SLAM' },
    { key: '3D_RECONSTRUCTION', label: '3. 3D Recon', desc: 'Point Cloud Voxelization' },
    { key: 'DETECTION', label: '4. Detection', desc: 'Semantic Extraction' },
    { key: 'REVIEW_LABEL', label: '5. Review', desc: 'Human-in-the-Loop Confirmation' },
    { key: 'MAP_GENERATED', label: '6. Generated', desc: '4 Decoupled Models' },
    { key: 'READY_FOR_OPERATION', label: '7. Active', desc: 'Ready for Autonomous Fleet' }
  ];

  /* ==========================================================================
     PRIMARY ENTRY POINT: renderAutoMapView()
     ========================================================================== */
  function renderAutoMapView() {
    const container = document.getElementById('automapViewContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="automap-shell">
        <!-- 1. AutoMap Header Ribbon & Pipeline Stepper -->
        <div class="automap-header-strip">
          <div class="automap-title-block">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="view-title" style="font-size:16px;">AutoMap Studio — Scan to Digital Twin</span>
              <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>DEPLOYMENT PIPELINE</span>
            </div>
            <div style="font-size:11px; color:var(--synq-text-secondary); margin-top:2px;">
              Autonomous warehouse spatial reconstruction from LiDAR, depth point clouds, and odometry.
            </div>
          </div>

          <!-- 7-Stage Pipeline Stepper Bar -->
          <div class="automap-stepper-bar">
            ${STEP_SEQUENCE.map((s, idx) => `
              <div class="automap-step-item ${s.key === currentStep ? 'active' : ''}" id="step-node-${s.key}">
                <div class="step-num">${idx + 1}</div>
                <div class="step-text">
                  <span class="step-name">${s.label.split('. ')[1]}</span>
                  <span class="step-sub">${s.desc}</span>
                </div>
              </div>
              ${idx < STEP_SEQUENCE.length - 1 ? '<div class="step-line"></div>' : ''}
            `).join('')}
          </div>
        </div>

        <!-- 2. Main Studio Workspace: 3D Visualizer (Left) & Review Drawer (Right) -->
        <div class="automap-workspace">

          <!-- Left Visualizer Container -->
          <div class="automap-visual-container">
            <div class="automap-canvas-toolbar">
              <div style="display:flex; gap:6px; align-items:center;">
                <button class="tool-btn ${activeViewMode === '3D' ? 'active' : ''}" onclick="window.setAutoMapViewMode('3D')">3D Point Cloud & Meshes</button>
                <button class="tool-btn ${activeViewMode === '2D' ? 'active' : ''}" onclick="window.setAutoMapViewMode('2D')">2D Nav2 Costmap View</button>
              </div>
              <div style="display:flex; gap:8px; align-items:center;">
                <span id="reconPointsBadge" class="synq-badge neutral" style="font-size:10px;">0 POINTS LOADED</span>
                <button class="tool-btn" onclick="window.resetAutoMapCamera()">Reset View</button>
              </div>
            </div>

            <!-- 3D Three.js Canvas Mount -->
            <div id="automap3dViewport" class="automap-3d-mount"></div>

            <!-- 2D Canvas Mount (Hidden unless toggled) -->
            <canvas id="automap2dCanvas" class="automap-2d-canvas" style="display:none;"></canvas>

            <!-- Bottom Live Telemetry Hud -->
            <div class="automap-viewport-hud">
              <div>Facility Size: <strong>15.0m × 15.0m</strong></div>
              <div>Grid Voxel: <strong>0.15m</strong></div>
              <div>SLAM Reference: <strong>/synq_amr_01/map</strong></div>
              <div id="automapStatusMsg" style="color:#58a6ff;">Ready to begin mapping scan.</div>
            </div>
          </div>

          <!-- Right Operator Review & Classification Drawer -->
          <div class="automap-drawer">
            <!-- Stage Control Buttons -->
            <div class="automap-action-card">
              <div style="font-size:11px; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">
                Active Workflow Stage
              </div>
              <div id="stageControlButtons" style="display:flex; flex-direction:column; gap:8px;">
                <button class="synq-btn" style="background:#238636; color:#fff; border-color:#2ea043;" onclick="window.startAutoMapScan()">
                  <span>▶ 1. Run AMR Mapping Scan</span>
                </button>
                <button class="synq-btn" style="background:rgba(56,189,248,0.15); color:#38bdf8; border-color:rgba(56,189,248,0.4);" onclick="window.runAutoMapReconstruction()">
                  <span>⚡ 2. Reconstruct & Detect Objects</span>
                </button>
                <div style="display:flex; gap:6px;">
                  <button class="synq-btn" style="flex:1;" onclick="window.confirmAllDetections()">
                    <span>Approve All (✓)</span>
                  </button>
                  <button class="synq-btn" style="flex:1; background:#1f6feb; color:#fff; border-color:#388bfd;" onclick="window.generateRepresentations()">
                    <span>3. Compile World Model</span>
                  </button>
                </div>
                <button class="synq-btn" style="background:rgba(163,113,247,0.2); color:#d2a8ff; border-color:rgba(163,113,247,0.5); font-weight:700;" onclick="window.activateAutoMapIntoFMS()">
                  <span>🚀 4. Activate in synQ FMS & Digital Twin</span>
                </button>
              </div>
            </div>

            <!-- Semantic Filter Tabs -->
            <div class="automap-filter-strip">
              <button class="filter-tab ${activeFilter === 'ALL' ? 'active' : ''}" onclick="window.setAutoMapFilter('ALL')">All (<span id="countAll">0</span>)</button>
              <button class="filter-tab ${activeFilter === 'NEEDS_CONFIRMATION' ? 'active' : ''}" onclick="window.setAutoMapFilter('NEEDS_CONFIRMATION')">
                Needs Review (<span id="countNeedsReview" style="color:#d29922; font-weight:700;">0</span>)
              </button>
              <button class="filter-tab ${activeFilter === 'rack' ? 'active' : ''}" onclick="window.setAutoMapFilter('rack')">Racks</button>
              <button class="filter-tab ${activeFilter === 'stations' ? 'active' : ''}" onclick="window.setAutoMapFilter('stations')">Stations</button>
            </div>

            <!-- Detection Cards List -->
            <div id="automapDetectionsList" class="automap-detections-scroll">
              <div style="padding:24px 16px; text-align:center; color:var(--synq-text-muted); font-size:12px;">
                No objects detected yet. Click <strong>"Run AMR Mapping Scan"</strong> to record LiDAR and extract warehouse infrastructure.
              </div>
            </div>
          </div>

        </div>
      </div>
    `;

    // Initialize 3D Three.js scene
    setTimeout(initThreeScene, 60);

    // Initial check on backend session status
    fetch('/api/v1/automap/session/status')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && data.keyframes > 0) {
          fetchDetectionsAndRender();
        }
      })
      .catch(() => {});
  }

  /* ==========================================================================
     THREE.JS 3D VIEWPORT INITIALIZATION
     ========================================================================== */
  function initThreeScene() {
    const mount = document.getElementById('automap3dViewport');
    if (!mount || typeof THREE === 'undefined') return;

    if (threeRenderer) {
      if (mount.contains(threeRenderer.domElement)) {
        mount.removeChild(threeRenderer.domElement);
      }
    }

    const width = mount.clientWidth || 800;
    const height = mount.clientHeight || 550;

    threeScene = new THREE.Scene();
    threeScene.background = new THREE.Color(0x0a0c10);

    threeCamera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    threeCamera.position.set(7.5, -12, 16);
    threeCamera.up.set(0, 0, 1);

    threeRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    threeRenderer.setSize(width, height);
    threeRenderer.setPixelRatio(window.devicePixelRatio || 1);
    threeRenderer.shadowMap.enabled = true;
    mount.appendChild(threeRenderer.domElement);

    if (typeof THREE.OrbitControls !== 'undefined') {
      threeControls = new THREE.OrbitControls(threeCamera, threeRenderer.domElement);
      threeControls.target.set(7.5, 7.5, 0);
      threeControls.enableDamping = true;
      threeControls.dampingFactor = 0.08;
      threeControls.maxPolarAngle = Math.PI / 2 - 0.05;
    }

    // Grid Floor
    const gridHelper = new THREE.GridHelper(15, 15, 0x30363d, 0x161b22);
    gridHelper.rotation.x = Math.PI / 2;
    gridHelper.position.set(7.5, 7.5, 0);
    threeScene.add(gridHelper);

    // Coordinate Axes
    const axes = new THREE.AxesHelper(2.0);
    axes.position.set(0, 0, 0.01);
    threeScene.add(axes);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    threeScene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
    dirLight.position.set(10, -5, 20);
    threeScene.add(dirLight);

    bboxGroup = new THREE.Group();
    threeScene.add(bboxGroup);

    // Render loop
    function animate() {
      animationFrameId = requestAnimationFrame(animate);
      if (threeControls) threeControls.update();
      if (threeRenderer && threeScene && threeCamera) {
        threeRenderer.render(threeScene, threeCamera);
      }
    }
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    animate();

    window.addEventListener('resize', onWindowResize);
  }

  function onWindowResize() {
    const mount = document.getElementById('automap3dViewport');
    if (!mount || !threeCamera || !threeRenderer) return;
    const width = mount.clientWidth;
    const height = mount.clientHeight;
    threeCamera.aspect = width / height;
    threeCamera.updateProjectionMatrix();
    threeRenderer.setSize(width, height);
  }

  window.resetAutoMapCamera = function () {
    if (!threeCamera || !threeControls) return;
    threeCamera.position.set(7.5, -12, 16);
    threeControls.target.set(7.5, 7.5, 0);
    threeControls.update();
  };

  /* ==========================================================================
     AUTONOMOUS PIPELINE ACTIONS & API CALLS
     ========================================================================== */
  window.startAutoMapScan = async function () {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    const msg = document.getElementById('automapStatusMsg');
    if (msg) msg.textContent = 'AMR traversing warehouse recording LiDAR/odometry keyframes...';

    currentStep = 'SCAN';
    updateStepperUI('SCAN');

    try {
      const res = await fetch('/api/v1/automap/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ robot_id: 'synq-amr-01', profile: 'standard_hub' })
      });
      const data = await res.json();
      currentStep = 'MAPPING';
      updateStepperUI('MAPPING');
      if (msg) msg.textContent = `Scan complete: ${data.keyframes_recorded} keyframes captured on FastDDS /scan & /odom.`;
      
      // Auto-trigger 3D reconstruction and detection
      setTimeout(window.runAutoMapReconstruction, 600);
    } catch (e) {
      if (msg) msg.textContent = 'Scan failed to connect to ROS 2 backend.';
    }
  };

  window.runAutoMapReconstruction = async function () {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    const msg = document.getElementById('automapStatusMsg');
    if (msg) msg.textContent = 'Voxel filtering point clouds and extracting 3D clusters...';

    currentStep = '3D_RECONSTRUCTION';
    updateStepperUI('3D_RECONSTRUCTION');

    try {
      const res = await fetch('/api/v1/automap/reconstruct', { method: 'POST' });
      const data = await res.json();
      currentStep = 'REVIEW_LABEL';
      updateStepperUI('REVIEW_LABEL');

      if (msg) {
        msg.innerHTML = `Identified <strong>${data.total_detected}</strong> entities (<span style="color:#d29922; font-weight:700;">${data.needs_confirmation_count} need operator confirmation</span>).`;
      }

      const badge = document.getElementById('reconPointsBadge');
      if (badge) {
        badge.textContent = `${data.reconstruction_stats.voxel_filtered_points} VOXELS / ${data.clusters_count} CLUSTERS`;
      }

      detectionsList = data.detections || [];
      renderDetectionsList();
      render3DBoundingBoxes(detectionsList);
      renderSyntheticPointCloud(data.reconstruction_stats.voxel_filtered_points);
    } catch (e) {
      if (msg) msg.textContent = 'Reconstruction failed.';
    }
  };

  window.confirmAllDetections = async function () {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    try {
      await fetch('/api/v1/automap/detections/confirm-all', { method: 'POST' });
      detectionsList.forEach(d => {
        d.status = 'CONFIRMED';
        d.needs_confirmation = false;
      });
      renderDetectionsList();
      render3DBoundingBoxes(detectionsList);
      const msg = document.getElementById('automapStatusMsg');
      if (msg) msg.textContent = 'All semantic entities confirmed by operator.';
    } catch (e) {}
  };

  window.generateRepresentations = async function () {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    const msg = document.getElementById('automapStatusMsg');
    if (msg) msg.textContent = 'Compiling decoupled 3D, Nav2 2D, Semantic, and Topology representations...';

    try {
      const res = await fetch('/api/v1/automap/generate', { method: 'POST' });
      const data = await res.json();
      currentStep = 'MAP_GENERATED';
      updateStepperUI('MAP_GENERATED');

      if (msg) {
        msg.innerHTML = `Artifacts compiled: 3D Twin (${data.racks_count} racks), Nav2 Occupancy (${data.nav2_resolution_m}m), Topology (${data.topology_nodes_count} nodes).`;
      }

      openArtifactsModal(data);
    } catch (e) {
      if (msg) msg.textContent = 'Failed to generate representations.';
    }
  };

  window.activateAutoMapIntoFMS = async function () {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    const msg = document.getElementById('automapStatusMsg');

    try {
      const res = await fetch('/api/v1/automap/activate', { method: 'POST' });
      const data = await res.json();
      currentStep = 'READY_FOR_OPERATION';
      updateStepperUI('READY_FOR_OPERATION');

      if (msg) {
        msg.innerHTML = `<strong style="color:#3fb950;">${data.message}</strong>`;
      }

      // Sync into window.synqStore
      if (window.synqStore) {
        window.synqStore.logActivity('AutoMap', 'Newly scanned warehouse topology activated into live FMS and Digital Twin.');
      }

      alert('AutoMap Activated! synQ FMS, Digital Twin, and CBS Router are now synchronized with the real-world scanned layout.');
      if (typeof navigateTo === 'function') {
        navigateTo('overview');
      }
    } catch (e) {}
  };

  /* ==========================================================================
     UI RENDERING & OPERATOR REVIEW DRAWER
     ========================================================================== */
  function updateStepperUI(activeStepKey) {
    STEP_SEQUENCE.forEach(s => {
      const el = document.getElementById(`step-node-${s.key}`);
      if (el) el.classList.toggle('active', s.key === activeStepKey);
    });
  }

  window.setAutoMapFilter = function (filter) {
    activeFilter = filter;
    renderDetectionsList();
  };

  window.setAutoMapViewMode = function (mode) {
    activeViewMode = mode;
    const mount3d = document.getElementById('automap3dViewport');
    const canvas2d = document.getElementById('automap2dCanvas');
    if (!mount3d || !canvas2d) return;

    if (mode === '3D') {
      mount3d.style.display = 'block';
      canvas2d.style.display = 'none';
    } else {
      mount3d.style.display = 'none';
      canvas2d.style.display = 'block';
      render2DNav2Canvas();
    }
  };

  async function fetchDetectionsAndRender() {
    try {
      const res = await fetch('/api/v1/automap/detections');
      const data = await res.json();
      if (data && data.detections) {
        detectionsList = data.detections;
        renderDetectionsList();
        render3DBoundingBoxes(detectionsList);
      }
    } catch (e) {}
  }

  function renderDetectionsList() {
    const container = document.getElementById('automapDetectionsList');
    if (!container) return;

    const needsReviewCount = detectionsList.filter(d => d.needs_confirmation && d.status !== 'CONFIRMED').length;
    const countAllEl = document.getElementById('countAll');
    const countRevEl = document.getElementById('countNeedsReview');
    if (countAllEl) countAllEl.textContent = detectionsList.length;
    if (countRevEl) countRevEl.textContent = needsReviewCount;

    let filtered = detectionsList;
    if (activeFilter === 'NEEDS_CONFIRMATION') {
      filtered = detectionsList.filter(d => d.needs_confirmation && d.status !== 'CONFIRMED');
    } else if (activeFilter === 'rack') {
      filtered = detectionsList.filter(d => d.semantic_type === 'rack');
    } else if (activeFilter === 'stations') {
      filtered = detectionsList.filter(d => d.semantic_type === 'pick_station' || d.semantic_type === 'drop_station' || d.semantic_type === 'charger');
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="padding:24px 16px; text-align:center; color:var(--synq-text-muted); font-size:12px;">
          No entities matching filter "<strong>${activeFilter}</strong>".
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(d => {
      const isUncertain = d.needs_confirmation && d.status !== 'CONFIRMED';
      const isConfirmed = d.status === 'CONFIRMED';
      const confPct = Math.round(d.confidence * 100);
      const bb = d.bounding_box || { center: { x: 0, y: 0, z: 0 }, dimensions: { width: 1, depth: 1, height: 1 } };
      const c = bb.center || { x: 0, y: 0, z: 0 };
      const dim = bb.dimensions || { width: 1, depth: 1, height: 1 };

      const typeBadgeClass = {
        rack: 'color:#a371f7; background:rgba(163,113,247,0.15); border:1px solid rgba(163,113,247,0.3);',
        charger: 'color:#d29922; background:rgba(210,153,34,0.15); border:1px solid rgba(210,153,34,0.3);',
        pick_station: 'color:#3fb950; background:rgba(46,160,67,0.15); border:1px solid rgba(46,160,67,0.3);',
        drop_station: 'color:#58a6ff; background:rgba(31,111,235,0.15); border:1px solid rgba(31,111,235,0.3);',
        restricted_zone: 'color:#f85149; background:rgba(248,81,73,0.15); border:1px solid rgba(248,81,73,0.3);',
        obstacle: 'color:#f0883e; background:rgba(240,136,62,0.15); border:1px solid rgba(240,136,62,0.3);'
      }[d.semantic_type] || 'color:#c9d1d9;';

      return `
        <div class="automap-det-card ${isUncertain ? 'uncertain-card' : ''} ${d.id === selectedDetectionId ? 'selected' : ''}" onclick="window.selectDetectionObject('${d.id}')">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
            <div>
              <span style="font-weight:700; font-size:12px; color:#fff;">${d.label}</span>
              <div style="font-size:10px; color:var(--synq-text-secondary); margin-top:1px;">ID: ${d.id}</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:3px;">
              <span style="font-size:9px; font-weight:700; padding:2px 6px; border-radius:3px; ${typeBadgeClass}">${d.semantic_type.toUpperCase()}</span>
              <span style="font-size:9.5px; font-weight:700; color:${confPct >= 85 ? '#3fb950' : '#d29922'};">
                ${confPct}% ${confPct >= 85 ? 'AUTO' : 'UNCERTAIN'}
              </span>
            </div>
          </div>

          <div style="font-size:10px; color:var(--synq-text-secondary); display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-bottom:6px;">
            <div>Pos: <strong style="color:#c9d1d9;">(${c.x.toFixed(1)}, ${c.y.toFixed(1)}, ${c.z.toFixed(1)})m</strong></div>
            <div>Size: <strong style="color:#c9d1d9;">${dim.width.toFixed(1)}m × ${dim.depth.toFixed(1)}m × ${dim.height.toFixed(1)}m</strong></div>
          </div>

          ${isUncertain ? `
            <div style="background:rgba(210,153,34,0.12); border:1px solid rgba(210,153,34,0.25); border-radius:3px; padding:6px; font-size:10px; color:#e3b341; margin-bottom:6px;">
              <strong>Needs Confirmation:</strong> ${d.confirmation_reason || 'Spatial cluster requires human validation.'}
            </div>
          ` : ''}

          <div style="display:flex; gap:6px; align-items:center; margin-top:4px;">
            <select class="select-input" style="font-size:10px; padding:2px 6px; margin-bottom:0; flex:1;" onchange="window.reclassifyObject('${d.id}', this.value)">
              <option value="rack" ${d.semantic_type === 'rack' ? 'selected' : ''}>Storage Rack</option>
              <option value="charger" ${d.semantic_type === 'charger' ? 'selected' : ''}>Charging Dock</option>
              <option value="pick_station" ${d.semantic_type === 'pick_station' ? 'selected' : ''}>Pick Station</option>
              <option value="drop_station" ${d.semantic_type === 'drop_station' ? 'selected' : ''}>Drop Station</option>
              <option value="conveyor" ${d.semantic_type === 'conveyor' ? 'selected' : ''}>Conveyor Line</option>
              <option value="restricted_zone" ${d.semantic_type === 'restricted_zone' ? 'selected' : ''}>Restricted Zone</option>
              <option value="obstacle" ${d.semantic_type === 'obstacle' ? 'selected' : ''}>Obstacle</option>
            </select>
            ${isConfirmed
              ? '<span style="font-size:10px; color:#3fb950; font-weight:700;">Confirmed ✓</span>'
              : `<button class="synq-btn" style="padding:2px 8px; font-size:10px; background:#238636; color:#fff;" onclick="window.confirmSingleObject('${d.id}')">Confirm</button>`
            }
            <button class="synq-btn" style="padding:2px 6px; font-size:10px; color:#f85149; border-color:rgba(248,81,73,0.3);" onclick="window.rejectSingleObject('${d.id}')" title="Reject / Delete">✕</button>
          </div>
        </div>
      `;
    }).join('');
  }

  window.selectDetectionObject = function (id) {
    selectedDetectionId = id;
    renderDetectionsList();
  };

  window.reclassifyObject = async function (id, newType) {
    try {
      const res = await fetch('/api/v1/automap/detections/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ object_id: id, semantic_type: newType, status: 'CONFIRMED' })
      });
      const updated = await res.json();
      const local = detectionsList.find(d => d.id === id);
      if (local) {
        local.semantic_type = updated.semantic_type;
        local.status = 'CONFIRMED';
        local.needs_confirmation = false;
      }
      renderDetectionsList();
      render3DBoundingBoxes(detectionsList);
    } catch (e) {}
  };

  window.confirmSingleObject = async function (id) {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    try {
      await fetch('/api/v1/automap/detections/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ object_id: id, status: 'CONFIRMED' })
      });
      const local = detectionsList.find(d => d.id === id);
      if (local) {
        local.status = 'CONFIRMED';
        local.needs_confirmation = false;
      }
      renderDetectionsList();
      render3DBoundingBoxes(detectionsList);
    } catch (e) {}
  };

  window.rejectSingleObject = async function (id) {
    if (typeof playHapticClick === 'function') playHapticClick('low');
    try {
      await fetch('/api/v1/automap/detections/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ object_id: id, status: 'REJECTED' })
      });
      detectionsList = detectionsList.filter(d => d.id !== id);
      renderDetectionsList();
      render3DBoundingBoxes(detectionsList);
    } catch (e) {}
  };

  /* ==========================================================================
     3D POINT CLOUD & BOUNDING BOX MESH GENERATION
     ========================================================================== */
  function renderSyntheticPointCloud(pointCount) {
    if (!threeScene || typeof THREE === 'undefined') return;

    if (pointCloudMesh) {
      threeScene.remove(pointCloudMesh);
    }

    const count = Math.min(6000, pointCount || 3500);
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const px = Math.random() * 14.8 + 0.1;
      const py = Math.random() * 14.8 + 0.1;
      const pz = Math.random() * 3.2;

      positions[i * 3] = px;
      positions[i * 3 + 1] = py;
      positions[i * 3 + 2] = pz;

      // LiDAR elevation color gradient (cyan to purple)
      const t = pz / 3.2;
      colors[i * 3] = 0.2 + 0.4 * t;
      colors[i * 3 + 1] = 0.7 - 0.3 * t;
      colors[i * 3 + 2] = 0.95;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.65
    });

    pointCloudMesh = new THREE.Points(geometry, material);
    threeScene.add(pointCloudMesh);
  }

  function render3DBoundingBoxes(detections) {
    if (!threeScene || !bboxGroup || typeof THREE === 'undefined') return;

    // Clear existing boxes
    while (bboxGroup.children.length > 0) {
      const obj = bboxGroup.children[0];
      bboxGroup.remove(obj);
    }

    const colorMap = {
      rack: 0xa371f7,
      charger: 0xd29922,
      pick_station: 0x2ea043,
      drop_station: 0x388bfd,
      restricted_zone: 0xf85149,
      conveyor: 0x38bdf8,
      obstacle: 0xf0883e
    };

    detections.forEach(d => {
      if (d.status === 'REJECTED') return;

      const bb = d.bounding_box || { center: { x: 0, y: 0, z: 0 }, dimensions: { width: 1, depth: 1, height: 1 } };
      const c = bb.center || { x: 0, y: 0, z: 0 };
      const dim = bb.dimensions || { width: 1, depth: 1, height: 1 };
      const color = colorMap[d.semantic_type] || 0xffffff;

      const geom = new THREE.BoxGeometry(dim.width, dim.depth, dim.height);
      const wireGeom = new THREE.WireframeGeometry(geom);
      const wireMat = new THREE.LineBasicMaterial({
        color: color,
        linewidth: 1.5,
        transparent: true,
        opacity: d.needs_confirmation ? 0.9 : 0.6
      });
      const wire = new THREE.LineSegments(wireGeom, wireMat);
      wire.position.set(c.x, c.y, c.z);

      // Translucent solid fill
      const fillMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: d.needs_confirmation ? 0.25 : 0.12
      });
      const mesh = new THREE.Mesh(geom, fillMat);
      mesh.position.set(c.x, c.y, c.z);

      const objGroup = new THREE.Group();
      objGroup.add(wire);
      objGroup.add(mesh);
      bboxGroup.add(objGroup);
    });
  }

  /* ==========================================================================
     2D NAV2 OCCUPANCY GRID CANVAS RENDERING
     ========================================================================== */
  function render2DNav2Canvas() {
    const canvas = document.getElementById('automap2dCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.parentElement.clientWidth;
    const h = canvas.parentElement.clientHeight;
    canvas.width = w;
    canvas.height = h;

    const scale = Math.min(w / 16.0, h / 16.0);
    const offsetX = (w - 15.0 * scale) / 2;
    const offsetY = (h - 15.0 * scale) / 2;

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, w, h);

    // Grid Floor
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    for (let x = 0; x <= 15; x++) {
      ctx.beginPath();
      ctx.moveTo(offsetX + x * scale, offsetY);
      ctx.lineTo(offsetX + x * scale, offsetY + 15 * scale);
      ctx.stroke();
    }
    for (let y = 0; y <= 15; y++) {
      ctx.beginPath();
      ctx.moveTo(offsetX, offsetY + y * scale);
      ctx.lineTo(offsetX + 15 * scale, offsetY + y * scale);
      ctx.stroke();
    }

    // Outer Perimeter Wall
    ctx.strokeStyle = '#f85149';
    ctx.lineWidth = 4;
    ctx.strokeRect(offsetX, offsetY, 15 * scale, 15 * scale);

    // Render Occupancy Footprints
    detectionsList.forEach(d => {
      if (d.status === 'REJECTED') return;
      const bb = d.bounding_box;
      const cx = bb.center.x;
      const cy = bb.center.y;
      const dw = bb.dimensions.width;
      const dd = bb.dimensions.depth;

      const px = offsetX + (cx - dw / 2) * scale;
      const py = offsetY + (cy - dd / 2) * scale;
      const pw = dw * scale;
      const ph = dd * scale;

      // Inscribed Costmap Inflation Halo
      ctx.fillStyle = 'rgba(248, 81, 73, 0.15)';
      ctx.fillRect(px - 0.35 * scale, py - 0.35 * scale, pw + 0.7 * scale, ph + 0.7 * scale);

      // Solid Object
      ctx.fillStyle = d.semantic_type === 'rack' ? '#21262d' : (d.semantic_type === 'charger' ? '#d29922' : '#388bfd');
      ctx.fillRect(px, py, pw, ph);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.strokeRect(px, py, pw, ph);

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 9px monospace';
      ctx.fillText(d.id, px + 4, py + 12);
    });
  }

  /* ==========================================================================
     ARTIFACTS MODAL (PREVIEW OF 4 DECOUPLED REPRESENTATIONS)
     ========================================================================== */
  function openArtifactsModal(data) {
    let modal = document.getElementById('automapArtifactsModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'automapArtifactsModal';
      modal.className = 'synq-modal-backdrop visible';
      document.body.appendChild(modal);
    } else {
      modal.style.display = 'flex';
      modal.classList.add('visible');
    }

    modal.innerHTML = `
      <div class="synq-modal-dialog" style="max-width: 780px;">
        <div class="synq-modal-header">
          <div class="synq-modal-title">
            <span>Compiled AutoMap World Representations</span>
            <span class="synq-badge online" style="font-size:9px;">4 DECOUPLED ARTIFACTS</span>
          </div>
          <button class="synq-btn" onclick="document.getElementById('automapArtifactsModal').style.display='none'">✕</button>
        </div>

        <div class="animated-tabs-strip" style="margin-bottom: 12px;">
          <button class="tab-btn active" onclick="window.switchModalTab('3d')">1. 3D Digital Twin</button>
          <button class="tab-btn" onclick="window.switchModalTab('nav2')">2. Nav2 2D Occupancy</button>
          <button class="tab-btn" onclick="window.switchModalTab('semantic')">3. Semantic Entities</button>
          <button class="tab-btn" onclick="window.switchModalTab('topology')">4. FMS CBS Topology</button>
        </div>

        <div id="modalArtifactContent" style="background:#0d1117; border:1px solid #30363d; border-radius:4px; padding:12px; max-height:360px; overflow-y:auto; font-family:var(--synq-font-mono); font-size:11px; line-height:1.45;">
          Loading artifact spec...
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px;">
          <div style="font-size:11px; color:var(--synq-text-secondary);">
            Models ready for live deployment across ROS 2 Gazebo and physical AMRs.
          </div>
          <div style="display:flex; gap:8px;">
            <button class="synq-btn" onclick="document.getElementById('automapArtifactsModal').style.display='none'">Close</button>
            <button class="synq-btn" style="background:#238636; color:#fff;" onclick="window.activateAutoMapIntoFMS()">
              <span>Activate into Live synQ</span>
            </button>
          </div>
        </div>
      </div>
    `;

    window.switchModalTab('3d');
  }

  window.switchModalTab = async function (tab) {
    const box = document.getElementById('modalArtifactContent');
    if (!box) return;
    box.innerHTML = 'Fetching decoupled artifact spec...';

    try {
      const res = await fetch(`/api/v1/automap/export/${tab}`);
      const data = await res.json();
      box.innerHTML = `<pre style="color:#58a6ff;">${JSON.stringify(data, null, 2)}</pre>`;
    } catch (e) {
      box.innerHTML = '<span style="color:red;">Failed to load representation.</span>';
    }
  };

  // Attach to global window
  window.renderAutoMapView = renderAutoMapView;

})(window);

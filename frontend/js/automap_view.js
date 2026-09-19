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
      <div class="synq-command-body" style="height:100%;">

        <!-- LEFT DRAWER: PRE-FLIGHT HARDWARE, AMRs, SENSORS -->
        <aside class="synq-operate-sidebar" style="width: 260px; padding: 0;">
          <div style="padding: 10px; border-bottom: 1px solid #1e2633;">
            <div style="font-size: 9.5px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Deployment Target</div>
            <div style="display:flex; background:#121720; border:1px solid #1e2633; border-radius:4px; padding:2px;">
              <button class="filter-pill" style="flex:1; font-size:9.5px; padding:3px 0; text-align:center;">Simulation</button>
              <button class="filter-pill active" style="flex:1; font-size:9.5px; padding:3px 0; text-align:center;">Real World</button>
            </div>
          </div>

          <!-- Pre-Flight Hardware Checklist -->
          <div style="padding: 10px; border-bottom: 1px solid #1e2633;">
            <div style="font-size: 9.5px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Pre-Flight Hardware Checklist</div>
            <div style="display:flex; flex-direction:column; gap:4px; font-size:9.5px; color:#c9d1d9;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="color:#3fb950; font-weight:700;">✔</span>
                <span>LiDAR Ouster OS1-128 Connected (10Hz)</span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="color:#3fb950; font-weight:700;">✔</span>
                <span>Intel RealSense D455 Depth (30fps)</span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="color:#3fb950; font-weight:700;">✔</span>
                <span>RTK-GPS / Wheel Odometry Calibrated</span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="color:#3fb950; font-weight:700;">✔</span>
                <span>ROS 2 DDS Domain 42 Bridge Ready</span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="color:#3fb950; font-weight:700;">✔</span>
                <span>Nav2 Lifecycle Nodes Active</span>
              </div>
            </div>

            <!-- Vibrant Green Action Button -->
            <button class="synq-btn" style="width:100%; margin-top:10px; background:#238636; color:#fff; border-color:#2ea043; font-weight:700; padding:7px 0; justify-content:center;" onclick="window.startAutoMapScan()">
              <span>▶ Start Mapping Mission</span>
            </button>
          </div>

          <!-- Connected AMRs Matrix -->
          <div style="padding: 10px; border-bottom: 1px solid #1e2633;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size: 9.5px; font-weight:700; color:#64748b; text-transform:uppercase;">Connected AMRs</span>
              <span class="synq-badge online" style="font-size:8.5px;">5 PAIRED</span>
            </div>
            <table class="cockpit-table">
              <thead>
                <tr>
                  <th>Unit</th>
                  <th>IP Address</th>
                  <th>Ping</th>
                  <th>SLAM Node</th>
                </tr>
              </thead>
              <tbody>
                <tr style="background:rgba(56,189,248,0.1);">
                  <td style="color:#38bdf8; font-weight:700;">AMR-01</td>
                  <td>192.168.1.21</td>
                  <td style="color:#3fb950;">4ms</td>
                  <td><span class="synq-badge online" style="font-size:8px;">ONLINE</span></td>
                </tr>
                <tr>
                  <td>AMR-02</td>
                  <td>192.168.1.22</td>
                  <td>6ms</td>
                  <td><span class="synq-badge neutral" style="font-size:8px;">STANDBY</span></td>
                </tr>
                <tr>
                  <td>AMR-03</td>
                  <td>192.168.1.23</td>
                  <td>5ms</td>
                  <td><span class="synq-badge neutral" style="font-size:8px;">STANDBY</span></td>
                </tr>
                <tr>
                  <td>AMR-04</td>
                  <td>192.168.1.24</td>
                  <td>8ms</td>
                  <td><span class="synq-badge neutral" style="font-size:8px;">STANDBY</span></td>
                </tr>
                <tr>
                  <td>AMR-05</td>
                  <td>192.168.1.25</td>
                  <td>4ms</td>
                  <td><span class="synq-badge neutral" style="font-size:8px;">STANDBY</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Sensors Live Rates (AMR-01) -->
          <div style="padding: 10px; flex:1; overflow-y:auto;">
            <div style="font-size: 9.5px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Sensors (AMR-01)</div>
            <table class="cockpit-table">
              <thead>
                <tr>
                  <th>Sensor Stream</th>
                  <th>Rate</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>LiDAR 128-Beam</td>
                  <td style="color:#3fb950;">10.2 Hz</td>
                  <td><span style="color:#3fb950;">OK</span></td>
                </tr>
                <tr>
                  <td>RealSense RGB-D</td>
                  <td style="color:#3fb950;">29.8 fps</td>
                  <td><span style="color:#3fb950;">OK</span></td>
                </tr>
                <tr>
                  <td>IMU 6-DOF</td>
                  <td style="color:#38bdf8;">200 Hz</td>
                  <td><span style="color:#3fb950;">OK</span></td>
                </tr>
                <tr>
                  <td>Wheel Encoders</td>
                  <td>50 Hz</td>
                  <td><span style="color:#3fb950;">OK</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </aside>

        <!-- CENTER STACK: 3D RECONSTRUCTION VIEWPORT + BOTTOM COCKPIT -->
        <div class="synq-main-center-stack">

          <!-- 3D RECONSTRUCTION VIEWPORT -->
          <div class="synq-viewport-stage" id="automapStage">
            <div id="automap3dViewport" class="automap-3d-mount" style="width:100%; height:100%; position:absolute; top:0; left:0;"></div>
            <canvas id="automap2dCanvas" class="automap-2d-canvas" style="display:none; width:100%; height:100%; position:absolute; top:0; left:0;"></canvas>

            <!-- In-Canvas Top Floating Bar -->
            <div class="in-canvas-top-bar">
              <div class="in-canvas-pill-group">
                <button class="tool-btn ${activeViewMode === '3D' ? 'active' : ''}" onclick="window.setAutoMapViewMode('3D')">3D Point Cloud</button>
                <button class="tool-btn ${activeViewMode === '2D' ? 'active' : ''}" onclick="window.setAutoMapViewMode('2D')">2D Costmap</button>
                <span style="color:#2d3646;">|</span>
                <span id="reconPointsBadge" style="font-size:10px; color:#38bdf8; font-weight:600;">2.4M POINTS LOADED</span>
                <span style="color:#2d3646;">|</span>
                <span style="font-size:10px; color:#8c96a5;">Voxel Grid: 0.15m</span>
              </div>

              <div class="in-canvas-pill-group">
                <button class="synq-btn" style="padding: 2px 7px; font-size:9.5px; background:#1f6feb; color:#fff;" onclick="window.generateRepresentations()">
                  <span>Compile World Model</span>
                </button>
                <button class="synq-btn" style="padding: 2px 7px; font-size:9.5px; background:rgba(163,113,247,0.2); color:#d2a8ff; border-color:rgba(163,113,247,0.4);" onclick="window.activateAutoMapIntoFMS()">
                  <span>Activate in synQ</span>
                </button>
                <button class="in-canvas-icon-btn" onclick="window.resetAutoMapCamera()" title="Reset Camera">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
                </button>
              </div>
            </div>

            <!-- In-Canvas Bottom Floating Layer Pills -->
            <div class="in-canvas-bottom-pills">
              <button class="canvas-layer-pill active">
                <span style="width:5px; height:5px; border-radius:50%; background:#38bdf8;"></span>
                <span>Racks</span>
              </button>
              <button class="canvas-layer-pill active">
                <span style="width:5px; height:5px; border-radius:50%; background:#38bdf8;"></span>
                <span>Aisles</span>
              </button>
              <button class="canvas-layer-pill active">
                <span style="width:5px; height:5px; border-radius:50%; background:#38bdf8;"></span>
                <span>Bounding Boxes</span>
              </button>
              <button class="canvas-layer-pill active">
                <span style="width:5px; height:5px; border-radius:50%; background:#38bdf8;"></span>
                <span>Point Cloud</span>
              </button>
              <button class="canvas-layer-pill active">
                <span style="width:5px; height:5px; border-radius:50%; background:#38bdf8;"></span>
                <span>Stations</span>
              </button>
            </div>

            <div class="automap-viewport-hud" style="position:absolute; bottom:12px; left:12px; background:rgba(13,17,23,0.85); padding:4px 10px; border-radius:4px; font-size:9.5px; border:1px solid #1e2633; z-index:15;">
              <span id="automapStatusMsg" style="color:#58a6ff;">Real-time SLAM & Voxel Reconstruction Active</span>
            </div>
          </div>

          <!-- BOTTOM COCKPIT (3 COLUMNS: MAPPING PROGRESS, DETECTED OBJECTS, MISSION QUEUE) -->
          <div class="synq-bottom-cockpit">

            <!-- Column 1: Mapping Progress with Circular Gauge -->
            <div class="cockpit-panel">
              <div class="cockpit-panel-header">
                <div class="cockpit-panel-title">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle></svg>
                  <span>Mapping Progress</span>
                </div>
                <span class="synq-badge online" style="font-size:9px;">ACTIVE</span>
              </div>
              <div class="cockpit-panel-body" style="display:flex; flex-direction:column; justify-content:space-between;">
                <div class="circular-progress-wrap">
                  <svg class="circular-gauge" viewBox="0 0 80 80">
                    <circle class="gauge-bg" cx="40" cy="40" r="34"></circle>
                    <circle class="gauge-fill" cx="40" cy="40" r="34"></circle>
                    <text x="40" y="44" text-anchor="middle" fill="#f0f3f6" font-size="14" font-weight="700" font-family="var(--synq-font-mono)">68%</text>
                  </svg>
                  <div style="display:flex; flex-direction:column; gap:3px; font-size:9.5px;">
                    <div>Total Area: <strong>1,420 m²</strong></div>
                    <div>LiDAR Points: <strong style="color:#38bdf8;">2,418,200</strong></div>
                    <div>Loop Closures: <strong style="color:#3fb950;">14 Verified</strong></div>
                    <div>Confidence: <strong style="color:#3fb950;">98.4%</strong></div>
                  </div>
                </div>
                <div style="display:flex; gap:6px; margin-top:6px;">
                  <button class="synq-btn" style="flex:1; padding:3px 0; font-size:9px; justify-content:center;" onclick="window.generateRepresentations()">Save & Export</button>
                  <button class="synq-btn" style="flex:1; padding:3px 0; font-size:9px; justify-content:center;" onclick="window.activateAutoMapIntoFMS()">Align Twin</button>
                  <button class="synq-btn" style="padding:3px 8px; font-size:9px; color:#f85149;" onclick="window.resetAutoMapCamera()">Reset</button>
                </div>
              </div>
            </div>

            <!-- Column 2: Detected Objects (Live Table) -->
            <div class="cockpit-panel">
              <div class="cockpit-panel-header">
                <div class="cockpit-panel-title">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18"></rect></svg>
                  <span>Detected Objects (Live)</span>
                </div>
                <button class="synq-btn" style="padding:2px 6px; font-size:8.5px;" onclick="window.confirmAllDetections()">Approve All (✓)</button>
              </div>
              <div class="cockpit-panel-body">
                <table class="cockpit-table">
                  <thead>
                    <tr>
                      <th>Object</th>
                      <th>Category</th>
                      <th>Conf.</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody id="automapObjectsTableBody">
                    <tr>
                      <td style="color:#38bdf8; font-weight:700;">Rack R-12</td>
                      <td>Heavy Pallet</td>
                      <td>98.4%</td>
                      <td><span class="synq-badge online" style="font-size:8px;">CONFIRMED</span></td>
                      <td><button class="synq-btn" style="padding:1px 5px; font-size:8px;">View</button></td>
                    </tr>
                    <tr>
                      <td style="color:#38bdf8; font-weight:700;">Conveyor C-01</td>
                      <td>Material Flow</td>
                      <td>94.1%</td>
                      <td><span class="synq-badge online" style="font-size:8px;">CONFIRMED</span></td>
                      <td><button class="synq-btn" style="padding:1px 5px; font-size:8px;">View</button></td>
                    </tr>
                    <tr>
                      <td style="color:#d29922; font-weight:700;">Pallet P-04</td>
                      <td>Obstacle</td>
                      <td>87.2%</td>
                      <td><span class="synq-badge warning" style="font-size:8px;">NEEDS REVIEW</span></td>
                      <td><button class="synq-btn" style="padding:1px 5px; font-size:8px; background:#1f6feb; color:#fff;" onclick="window.confirmSingleDetection('Pallet P-04')">Verify</button></td>
                    </tr>
                    <tr>
                      <td style="color:#38bdf8; font-weight:700;">Zone Z-03</td>
                      <td>Restricted</td>
                      <td>99.0%</td>
                      <td><span class="synq-badge online" style="font-size:8px;">CONFIRMED</span></td>
                      <td><button class="synq-btn" style="padding:1px 5px; font-size:8px;">View</button></td>
                    </tr>
                    <tr>
                      <td style="color:#38bdf8; font-weight:700;">Dock D-01</td>
                      <td>Charging Pad</td>
                      <td>96.5%</td>
                      <td><span class="synq-badge online" style="font-size:8px;">CONFIRMED</span></td>
                      <td><button class="synq-btn" style="padding:1px 5px; font-size:8px;">View</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Column 3: AutoMap Mission Queue -->
            <div class="cockpit-panel">
              <div class="cockpit-panel-header">
                <div class="cockpit-panel-title">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>
                  <span>AutoMap Mission Queue</span>
                </div>
                <span style="font-size:9px; color:#64748b;">08:42 REMAINING</span>
              </div>
              <div class="cockpit-panel-body" style="font-size:9.5px;">
                <div style="display:flex; flex-direction:column; gap:5px;">
                  <div style="background:#121720; border:1px solid #1e2633; border-radius:4px; padding:5px 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                      <strong style="color:#38bdf8;">AUTOSCAN-01: Bay A-F Perimeter</strong>
                      <span style="color:#3fb950;">IN PROGRESS</span>
                    </div>
                    <div style="color:#8c96a5;">Waypoints: WP-01 → WP-02 → WP-03 → WP-04 → WP-05</div>
                    <div style="width:100%; height:3px; background:#1e2633; border-radius:2px; margin-top:4px; overflow:hidden;">
                      <div style="width:68%; height:100%; background:#238636;"></div>
                    </div>
                  </div>
                  <div style="background:#121720; border:1px solid #1e2633; border-radius:4px; padding:5px 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                      <strong style="color:#8c96a5;">AUTOSCAN-02: Aisle Crossings</strong>
                      <span style="color:#64748b;">QUEUED</span>
                    </div>
                    <div style="color:#64748b;">Awaiting completion of Bay perimeter sweep</div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- RIGHT TECHNICAL COCKPIT: QUAD SENSOR SPLIT & INSPECTOR -->
        <aside class="synq-right-cockpit">

          <!-- AMR-01 Live View: 4-Way Sensor Quad Split -->
          <div class="cockpit-card">
            <div class="cockpit-card-header">
              <div class="cockpit-card-title">
                <span style="width:6px; height:6px; border-radius:50%; background:#10b981;"></span>
                <span>AMR-01 — Live View</span>
              </div>
              <span class="synq-badge online" style="font-size:8.5px;">4 STREAMS</span>
            </div>
            <div class="quad-sensor-grid">
              <div class="sensor-quad-tile">
                <span class="sensor-tile-label">FRONT RGB</span>
                <img src="/static/public/warehouse_camera.jpg" alt="Front Camera Feed" class="sensor-quad-img">
              </div>
              <div class="sensor-quad-tile">
                <span class="sensor-tile-label">DEPTH D455</span>
                <img src="/static/public/warehouse_depth.jpg" alt="Depth Sensor Feed" class="sensor-quad-img">
              </div>
              <div class="sensor-quad-tile">
                <span class="sensor-tile-label">LIDAR TOP VIEW</span>
                <canvas id="automapRadarCanvas" style="width:100%; height:100%; display:block; background:#040608;"></canvas>
              </div>
              <div class="sensor-quad-tile">
                <span class="sensor-tile-label">3D POINT CLOUD</span>
                <canvas id="automapLidarPcdCanvas" style="width:100%; height:100%; display:block; background:#040608;"></canvas>
              </div>
            </div>
          </div>

          <!-- Robot Inspector AMR-01 (SLAM Telemetry) -->
          <div class="cockpit-card" style="border-bottom:none; flex:1; display:flex; flex-direction:column;">
            <div class="cockpit-card-header">
              <div class="cockpit-card-title">
                <span style="width:6px; height:6px; border-radius:50%; background:#38bdf8;"></span>
                <span>Robot Inspector AMR-01</span>
              </div>
              <span class="synq-badge online" style="font-size:8.5px;">SLAM MAPPING</span>
            </div>

            <div style="display:flex; flex-direction:column; gap:6px; font-size:9.5px; flex:1; overflow-y:auto;">
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">SLAM Node</span>
                <span style="font-family:var(--synq-font-mono); color:#3fb950;">slam_toolbox_async (ONLINE)</span>
              </div>
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">Keyframes Captured</span>
                <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">412 frames</span>
              </div>
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">Loop Closures</span>
                <span style="font-family:var(--synq-font-mono); color:#38bdf8;">14 validated</span>
              </div>
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">Estimated Drift</span>
                <span style="font-family:var(--synq-font-mono); color:#3fb950;">±0.012 m</span>
              </div>
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">Scan Match Score</span>
                <span style="font-family:var(--synq-font-mono); color:#3fb950;">0.984 (EXCELLENT)</span>
              </div>
              <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
                <span style="color:#8c96a5;">Battery SoC</span>
                <span style="font-family:var(--synq-font-mono); color:#3fb950;">64% (25.4V)</span>
              </div>
            </div>
          </div>

        </aside>

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

  /* ==========================================================================
     QUAD SENSOR RADAR & LIDAR LIVE ANIMATION
     ========================================================================== */
  let radarAngle = 0;
  function renderAutoMapRadar() {
    const canvas = document.getElementById('automapRadarCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width || 140;
      canvas.height = rect.height || 80;
    }

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#040608';
    ctx.fillRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const maxR = Math.min(w, h) / 2 - 4;

    // Range rings
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.2)';
    ctx.lineWidth = 1;
    for (let r = 1; r <= 3; r++) {
      ctx.beginPath();
      ctx.arc(cx, cy, (maxR / 3) * r, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Crosshairs
    ctx.beginPath();
    ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy);
    ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR);
    ctx.stroke();

    // Rotating sweep cone
    radarAngle += 0.08;
    const sweepGradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
    sweepGradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
    sweepGradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, maxR, radarAngle - 0.4, radarAngle);
    ctx.closePath();
    ctx.fillStyle = sweepGradient;
    ctx.fill();

    // Sweep line
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(radarAngle) * maxR, cy + Math.sin(radarAngle) * maxR);
    ctx.stroke();
    ctx.restore();

    // Obstacle blips
    const blips = [
      { r: 0.6 * maxR, a: 0.8 },
      { r: 0.8 * maxR, a: 2.2 },
      { r: 0.45 * maxR, a: 3.9 },
      { r: 0.75 * maxR, a: 5.1 }
    ];
    blips.forEach(b => {
      const bx = cx + Math.cos(b.a) * b.r;
      const by = cy + Math.sin(b.a) * b.r;
      ctx.fillStyle = '#f85149';
      ctx.beginPath();
      ctx.arc(bx, by, 2.5, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function renderAutoMapLidarPcd() {
    const canvas = document.getElementById('automapLidarPcdCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width || 140;
      canvas.height = rect.height || 80;
    }

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#040608';
    ctx.fillRect(0, 0, w, h);

    const numPoints = 120;
    const time = Date.now() * 0.002;
    for (let i = 0; i < numPoints; i++) {
      const angle = (i / numPoints) * Math.PI * 2;
      const depth = 15 + 20 * Math.sin(angle * 2 + time) + (Math.random() * 3);
      const px = w / 2 + Math.cos(angle) * (depth * 1.4);
      const py = h / 2 + Math.sin(angle) * (depth * 0.8);
      const hue = Math.floor((depth / 40) * 260);
      ctx.fillStyle = `hsl(${hue}, 90%, 65%)`;
      ctx.fillRect(px, py, 2, 2);
    }
  }

  window.confirmSingleDetection = function(name) {
    if (typeof playHapticClick === 'function') playHapticClick('high');
    if (typeof showToast === 'function') showToast(`Verified & Confirmed: ${name}`);
    const tbody = document.getElementById('automapObjectsTableBody');
    if (tbody) {
      const trs = tbody.querySelectorAll('tr');
      trs.forEach(tr => {
        if (tr.textContent.includes(name)) {
          const badge = tr.querySelector('.synq-badge');
          if (badge) {
            badge.className = 'synq-badge online';
            badge.textContent = 'CONFIRMED';
          }
          const btn = tr.querySelector('button');
          if (btn) {
            btn.style.background = 'transparent';
            btn.style.color = '#c9d1d9';
            btn.textContent = 'View';
          }
        }
      });
    }
  };

  // Run quad sensor periodic refresh
  setInterval(() => {
    renderAutoMapRadar();
    renderAutoMapLidarPcd();
  }, 60);

  // Attach to global window
  window.renderAutoMapView = renderAutoMapView;

})(window);

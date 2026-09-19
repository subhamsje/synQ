/* ==========================================================================
   synQ Industrial Robotics Operating System — Views & Modules Engine
   Aceternity UI Spotlight, Animista Transitions & Tactile Industrial Design
   ========================================================================== */

let currentFleetFilter = 'ALL';
let currentFleetSearch = '';
let currentMissionsFilter = 'ALL';
let diagLogFilter = '';

// Helper to format numbers safely
function numFmt(n, d = 2) {
  return Number(n).toFixed(d);
}

let currentFleetLayout = 'cards'; // 'cards' | 'table'

/* ==========================================================================
   1. FLEET MATRIX VIEW (Spotlight Cards & Search Filtering)
   ========================================================================== */
function renderFleetView(filter = currentFleetFilter) {
  currentFleetFilter = filter;
  const container = document.getElementById('fleetViewContainer');
  if (!container) return;

  const rawBots = window.synqStore ? window.synqStore.amrs : (window.ROBOTS || (typeof ROBOTS !== 'undefined' ? ROBOTS : {}));
  const bots = Object.values(rawBots);
  const activeCount = bots.filter(b => b.status === 'Navigating').length;
  const idleCount = bots.filter(b => b.status === 'Idle').length;
  const estopCount = bots.filter(b => b.status === 'Emergency Stop').length;

  // Filter & Search Logic
  const filteredBots = bots.filter(bot => {
    let matchFilter = true;
    if (filter === 'ACTIVE') matchFilter = (bot.status === 'Navigating');
    else if (filter === 'IDLE') matchFilter = (bot.status === 'Idle');
    else if (filter === 'ESTOP') matchFilter = (bot.status === 'Emergency Stop');

    let matchSearch = true;
    if (currentFleetSearch.trim()) {
      const q = currentFleetSearch.toLowerCase().trim();
      matchSearch = bot.id.toLowerCase().includes(q) ||
                    (bot.payload && bot.payload.toLowerCase().includes(q)) ||
                    (bot.serial && bot.serial.toLowerCase().includes(q));
    }
    return matchFilter && matchSearch;
  });

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Fleet Matrix & Spatial Telemetry</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>${bots.length} UNITS REGISTERED</span>
      </div>
      <div class="control-filter-bar">
        <div class="filter-btn-group">
          <button class="filter-pill ${filter === 'ALL' ? 'active' : ''}" onclick="playHapticClick('high'); renderFleetView('ALL');">All (${bots.length})</button>
          <button class="filter-pill ${filter === 'ACTIVE' ? 'active' : ''}" onclick="playHapticClick('high'); renderFleetView('ACTIVE');">Navigating (${activeCount})</button>
          <button class="filter-pill ${filter === 'IDLE' ? 'active' : ''}" onclick="playHapticClick('high'); renderFleetView('IDLE');">Idle (${idleCount})</button>
          <button class="filter-pill ${filter === 'ESTOP' ? 'active' : ''}" onclick="playHapticClick('high'); renderFleetView('ESTOP');">E-Stop (${estopCount})</button>
        </div>

        <div class="filter-btn-group" style="margin-left: 8px;">
          <button class="filter-pill ${currentFleetLayout === 'cards' ? 'active' : ''}" onclick="playHapticClick('high'); currentFleetLayout = 'cards'; renderFleetView();" title="Card Spotlight Grid View">
            Cards
          </button>
          <button class="filter-pill ${currentFleetLayout === 'table' ? 'active' : ''}" onclick="playHapticClick('high'); currentFleetLayout = 'table'; renderFleetView();" title="Foxglove High-Density Engineering Table">
            SCADA Table
          </button>
        </div>

        <div style="display:flex; align-items:center; gap:8px;">
          <input type="text" id="fleetSearchInput" class="select-input" style="margin-bottom:0; width:160px; font-size:10px;" placeholder="Search ID / Payload..." value="${currentFleetSearch}" oninput="currentFleetSearch = this.value; renderFleetView(currentFleetFilter);">
          <button class="synq-btn" onclick="playHapticClick('low'); toggleGlobalEstop();" style="background: rgba(248,81,73,0.15); color:#f85149; border-color: rgba(248,81,73,0.3);">
            <span>${(typeof isEstopActive !== 'undefined' && isEstopActive) ? 'Reset Global E-Stop' : 'Global E-Stop'}</span>
            <span class="kbd-chip" style="margin-left:4px; background:rgba(0,0,0,0.3); color:#fff; border-color:rgba(255,255,255,0.2);">E</span>
          </button>
        </div>
      </div>
    </div>

    ${filteredBots.length === 0 ? `
      <div class="empty-state-box">
        <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <div class="empty-state-title">No Autonomous Robots Found</div>
        <div class="empty-state-sub">No AMRs match the query "${currentFleetSearch}". Clear search to view the full warehouse fleet.</div>
        <button class="synq-btn" style="margin-top:12px;" onclick="currentFleetSearch=''; renderFleetView('ALL');">
          <span>Reset Search Filters</span>
        </button>
      </div>
    ` : currentFleetLayout === 'table' ? `
      <!-- FOXGLOVE / ALTARA HIGH-DENSITY SCADA ENGINEERING TABLE -->
      <div class="synq-table-wrap">
        <table class="synq-table">
          <thead>
            <tr>
              <th>AMR Unit & Serial</th>
              <th>Status</th>
              <th>SoC / Cells</th>
              <th>Pose (X, Y, θ)</th>
              <th>Speed / Drive</th>
              <th>Modular Payload</th>
              <th>Goal / Mission</th>
              <th>Safety PL e</th>
              <th>ROS 2 / DDS</th>
              <th style="text-align:right;">Control Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filteredBots.map(bot => {
              const isNav = (bot.status === 'Navigating');
              const isStop = (bot.status === 'Emergency Stop');
              const isSelected = (bot.id === (typeof selectedRobotId !== 'undefined' ? selectedRobotId : ''));
              const statusClass = isStop ? 'critical' : (isNav ? 'active' : 'idle');
              const cells = bot.cells || [3.32, 3.31, 3.32, 3.30];

              return `
                <tr style="background:${isSelected ? 'rgba(56,189,248,0.06)' : 'transparent'}; cursor:pointer;" onclick="inspectRobotFromMatrix('${bot.id}')">
                  <td>
                    <div style="display:flex; align-items:center; gap:6px;">
                      <span class="table-mono" style="font-weight:700; color:${isSelected ? '#38bdf8' : '#fff'}; font-size:11px;">${bot.id}</span>
                      <span style="font-size:9px; color:var(--text-muted); font-family:var(--synq-font-mono);">${bot.serial || 'SN-SYNQ'}</span>
                    </div>
                  </td>
                  <td>
                    <span class="synq-badge ${statusClass}" style="font-size:9px;">
                      <span class="synq-badge-dot ${isNav ? 'radar-ping' : ''}"></span>${bot.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div style="display:flex; flex-direction:column; gap:2px;">
                      <span class="table-mono" style="font-size:10.5px; font-weight:700; color:${bot.battery < 20 ? '#f85149' : (bot.battery < 40 ? '#d29922' : '#3fb950')};">${bot.battery.toFixed(1)}%</span>
                      <span style="font-size:8.5px; font-family:var(--synq-font-mono); color:var(--text-secondary);">${cells[0]}V | ${cells[1]}V | ${cells[2]}V | ${cells[3]}V</span>
                    </div>
                  </td>
                  <td class="table-mono" style="font-size:10px; color:#38bdf8;">
                    X: ${bot.x.toFixed(2)}m, Y: ${bot.y.toFixed(2)}m, θ: ${bot.heading.toFixed(0)}°
                  </td>
                  <td class="table-mono" style="font-size:10px;">
                    ${bot.speed.toFixed(2)} m/s <span style="color:var(--text-muted);">(${Math.round(bot.speed * 160)} RPM)</span>
                  </td>
                  <td>
                    <div style="display:flex; align-items:center; gap:4px;">
                      <span style="color:#a371f7; font-weight:600; font-size:10px;">${(bot.payload || 'SCISSOR_LIFT').replace('_', ' ')}</span>
                      <span style="color:#3fb950; font-size:9px;">✓</span>
                    </div>
                  </td>
                  <td>
                    <div style="font-size:10px;">
                      <span style="color:#58a6ff; font-weight:600;">${bot.mission || 'STANDBY'}</span>
                      <span style="color:var(--text-secondary); font-size:9px;">→ ${bot.destination || '—'}</span>
                    </div>
                  </td>
                  <td>
                    <span style="font-size:9.5px; font-family:var(--synq-font-mono); color:${bot.safetyState && bot.safetyState.lidarStopZone ? '#f85149' : '#3fb950'};">
                      ${bot.safetyState && bot.safetyState.lidarStopZone ? 'BREACHED' : 'CLEAR (0.45m)'}
                    </span>
                  </td>
                  <td>
                    <span class="table-mono" style="font-size:9.5px; color:#3fb950;">50.0 Hz</span>
                  </td>
                  <td style="text-align:right;">
                    <div style="display:inline-flex; gap:4px;" onclick="event.stopPropagation();">
                      <button class="synq-btn" style="padding:2px 6px; font-size:9px;" onclick="playHapticClick('high'); setViewportMode('3d'); set3DPreset('follow'); navigateTo('overview');" title="Track in 3D Viewport">
                        3D Track
                      </button>
                      <button class="synq-btn" style="padding:2px 6px; font-size:9px;" onclick="playHapticClick('high'); openExpandableRobotModal('${bot.id}');" title="Expand Telemetry">
                        Expand
                      </button>
                      <button class="synq-btn" style="padding:2px 6px; font-size:9px;" onclick="playHapticClick('high'); dockUnit('${bot.id}');" title="Dock & Charge">
                        Dock
                      </button>
                      <button class="synq-btn" style="padding:2px 6px; font-size:9px;" onclick="playHapticClick('high'); pauseUnit('${bot.id}');" title="Pause / Resume">
                        ${bot.status === 'Navigating' ? 'Pause' : 'Resume'}
                      </button>
                    </div>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    ` : `
      <!-- CARD SPOTLIGHT GRID -->
      <div class="synq-grid-3">
        ${filteredBots.map(bot => {
          const isNav = (bot.status === 'Navigating');
          const isStop = (bot.status === 'Emergency Stop');
          const isSelected = (bot.id === (typeof selectedRobotId !== 'undefined' ? selectedRobotId : ''));
          const statusClass = isStop ? 'critical' : (isNav ? 'active' : 'idle');
          const batClass = bot.battery > 50 ? 'nominal' : (bot.battery > 20 ? 'medium' : 'critical');

          const cardInnerHtml = `
            <div class="robot-card spotlight-card ${isNav ? 'active-navigating' : ''}" style="height: 100%;">
              <div class="robot-card-header">
                <div class="robot-id-group">
                  <span class="robot-id-title" style="color: ${isSelected ? '#38bdf8' : '#fff'};">${bot.id}</span>
                  <span class="robot-serial">${bot.serial || 'SN-SYNQ-2026'}</span>
                </div>
                <span class="synq-badge ${statusClass}">
                  <span class="synq-badge-dot ${isNav ? 'radar-ping' : ''}"></span>${bot.status.toUpperCase()}
                </span>
              </div>

              <!-- Battery Health Strip -->
              <div class="battery-gauge-wrap">
                <div class="battery-gauge-header">
                  <span style="color: var(--synq-text-muted); font-size: 9px; font-weight:700; text-transform:uppercase;">LiFePO4 State of Charge</span>
                  <span class="table-mono" style="font-size: 11px;">${bot.battery.toFixed(1)}%</span>
                </div>
                <div class="battery-bar-track">
                  <div class="battery-bar-fill ${batClass}" style="width: ${Math.min(100, Math.max(0, bot.battery))}%;"></div>
                </div>
              </div>

              <!-- Detailed Spec & Spatial Grid -->
              <div class="robot-spec-grid">
                <div class="robot-spec-item">
                  <span class="robot-spec-label">Payload Module</span>
                  <span class="robot-spec-val" style="color: var(--synq-status-cbs);">${bot.payload}</span>
                </div>
                <div class="robot-spec-item">
                  <span class="robot-spec-label">Velocity / Heading</span>
                  <span class="robot-spec-val">${bot.speed.toFixed(2)} m/s · ${bot.heading.toFixed(0)}°</span>
                </div>
                <div class="robot-spec-item">
                  <span class="robot-spec-label">Coordinates</span>
                  <span class="robot-spec-val">(${bot.x.toFixed(2)}, ${bot.y.toFixed(2)})</span>
                </div>
                <div class="robot-spec-item">
                  <span class="robot-spec-label">Assigned Task</span>
                  <span class="robot-spec-val" style="color: #58a6ff;">${bot.mission || '—'}</span>
                </div>
                <div class="robot-spec-item" style="grid-column: span 2;">
                  <span class="robot-spec-label">ROS 2 Lifecycle State</span>
                  <span class="robot-spec-val" style="font-size: 10px; color: var(--synq-status-online);">${bot.rosNode || '/lifecycle_amr (ACTIVE)'}</span>
                </div>
              </div>

              <div class="robot-card-actions">
                <button class="synq-btn" onclick="playHapticClick('high'); openExpandableRobotModal('${bot.id}');" title="Expand Telemetry & Diagnostics">
                  <span>Expand ↗</span>
                </button>
                <button class="synq-btn" onclick="playHapticClick('high'); inspectRobotFromMatrix('${bot.id}');" title="Focus in Digital Twin">
                  <span>Track</span>
                </button>
                <button class="stateful-btn" onclick="triggerStatefulButton(this, () => dockUnit('${bot.id}'), 'Docked ✓')" title="Return to Charger C1">
                  <span>Dock</span>
                </button>
                <button class="stateful-btn" onclick="triggerStatefulButton(this, () => pauseUnit('${bot.id}'), 'Toggled ✓')" title="Pause / Resume Motion">
                  <span>${bot.status === 'Navigating' ? 'Pause' : 'Resume'}</span>
                </button>
              </div>
            </div>
          `;

          if (isSelected) {
            return `
              <div class="moving-border-card">
                <div class="moving-border-card-inner">
                  ${cardInnerHtml}
                </div>
              </div>
            `;
          }
          return cardInnerHtml;
        }).join('')}
      </div>
    `}
  `;
}

function inspectRobotFromMatrix(id) {
  selectedRobotId = id;
  navigateTo('overview');
  setPanelTab('inspector');
}

/* ==========================================================================
   2. MISSIONS BOARD VIEW (VDA 5050 Orders & Status Filtering)
   ========================================================================== */
const SAMPLE_MISSIONS = [
  { id: "TASK-4821", priority: "HIGH", robot: "synq-amr-01", payload: "SCISSOR_LIFT", from: "N_1_1 (Rack B)", to: "N_2_2 (Drop D2)", status: "IN_TRANSIT", progress: 65, eta: "28s" },
  { id: "TASK-4822", priority: "NORMAL", robot: "synq-amr-02", payload: "ROLLER_CONVEYOR", from: "PICK-1 (Dock P1)", to: "N_1_2 (Rack C)", status: "QUEUED", progress: 0, eta: "1m 15s" },
  { id: "TASK-4820", priority: "URGENT", robot: "synq-amr-03", payload: "TOTE_GRIPPER", from: "N_0_1 (Rack A)", to: "DROP-1 (Out D1)", status: "COMPLETED", progress: 100, eta: "0s" },
  { id: "TASK-4819", priority: "NORMAL", robot: "synq-amr-01", payload: "SCISSOR_LIFT", from: "CHG-1 (Dock C1)", to: "PICK-2 (Dock P2)", status: "COMPLETED", progress: 100, eta: "0s" },
  { id: "TASK-4818", priority: "LOW", robot: "synq-amr-02", payload: "ROLLER_CONVEYOR", from: "N_2_1 (Rack E)", to: "DROP-2 (Out D2)", status: "COMPLETED", progress: 100, eta: "0s" }
];

function renderMissionsView(filter = currentMissionsFilter) {
  currentMissionsFilter = filter;
  const container = document.getElementById('missionsViewContainer');
  if (!container) return;

  const filteredMissions = SAMPLE_MISSIONS.filter(m => {
    if (filter === 'ACTIVE') return m.status === 'IN_TRANSIT';
    if (filter === 'QUEUED') return m.status === 'QUEUED';
    if (filter === 'COMPLETED') return m.status === 'COMPLETED';
    return true;
  });

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Missions & VDA 5050 Orders</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>CBS COORDINATION ACTIVE</span>
      </div>
      <div style="display: flex; gap: 8px; align-items:center;">
        <div class="filter-btn-group">
          <button class="filter-pill ${filter === 'ALL' ? 'active' : ''}" onclick="playHapticClick('high'); renderMissionsView('ALL');">All (${SAMPLE_MISSIONS.length})</button>
          <button class="filter-pill ${filter === 'ACTIVE' ? 'active' : ''}" onclick="playHapticClick('high'); renderMissionsView('ACTIVE');">In Transit (1)</button>
          <button class="filter-pill ${filter === 'QUEUED' ? 'active' : ''}" onclick="playHapticClick('high'); renderMissionsView('QUEUED');">Queued (1)</button>
          <button class="filter-pill ${filter === 'COMPLETED' ? 'active' : ''}" onclick="playHapticClick('high'); renderMissionsView('COMPLETED');">Completed (3)</button>
        </div>
        <button class="synq-btn" style="background: var(--synq-status-active); color: #fff; border-color: var(--synq-status-active);" onclick="playHapticClick('high'); openQuickOrderModal();">
          <span>+ Dispatch Mission</span>
        </button>
      </div>
    </div>

    <!-- Top Mission KPIs with Aceternity Spotlight Cards -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
      <div class="synq-card spotlight-card" style="padding: 12px;">
        <span style="font-size: 9px; font-weight:700; text-transform:uppercase; color: var(--synq-text-muted);">Active Missions</span>
        <div style="font-size: 20px; font-weight:700; font-family:var(--synq-font-mono); color:#ffffff; margin-top:4px;">1</div>
        <span style="font-size: 10px; color: var(--synq-status-online);">In Progress (100% On-Time)</span>
      </div>
      <div class="synq-card spotlight-card" style="padding: 12px;">
        <span style="font-size: 9px; font-weight:700; text-transform:uppercase; color: var(--synq-text-muted);">Queued Buffer</span>
        <div style="font-size: 20px; font-weight:700; font-family:var(--synq-font-mono); color:#ffffff; margin-top:4px;">1</div>
        <span style="font-size: 10px; color: var(--synq-text-muted);">Allocated to synq-amr-02</span>
      </div>
      <div class="synq-card spotlight-card" style="padding: 12px;">
        <span style="font-size: 9px; font-weight:700; text-transform:uppercase; color: var(--synq-text-muted);">Completed Today</span>
        <div style="font-size: 20px; font-weight:700; font-family:var(--synq-font-mono); color:#ffffff; margin-top:4px;">148</div>
        <span style="font-size: 10px; color: var(--synq-status-online);">+12 vs Target SLA</span>
      </div>
      <div class="synq-card spotlight-card" style="padding: 12px;">
        <span style="font-size: 9px; font-weight:700; text-transform:uppercase; color: var(--synq-text-muted);">CBS Collision Resolves</span>
        <div style="font-size: 20px; font-weight:700; font-family:var(--synq-font-mono); color:#ffffff; margin-top:4px;">34</div>
        <span style="font-size: 10px; color: var(--synq-status-cbs);">0 Near-Misses</span>
      </div>
    </div>

    <!-- Missions Table -->
    ${filteredMissions.length === 0 ? `
      <div class="empty-state-box">
        <div class="empty-state-title">No Missions in Category</div>
        <div class="empty-state-sub">There are currently no tasks matching the selected filter state.</div>
      </div>
    ` : `
      <div class="synq-table-wrap">
        <table class="synq-table">
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Priority</th>
              <th>AMR Unit</th>
              <th>Required Payload</th>
              <th>Origin Node</th>
              <th>Destination</th>
              <th>Progress / ETA</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filteredMissions.map(m => {
              const prioClass = m.priority === 'URGENT' ? 'critical' : (m.priority === 'HIGH' ? 'warning' : 'neutral');
              const stClass = m.status === 'IN_TRANSIT' ? 'active' : (m.status === 'COMPLETED' ? 'online' : 'idle');
              return `
                <tr>
                  <td class="table-mono" style="color: #58a6ff; font-weight:700;">${m.id}</td>
                  <td><span class="synq-badge ${prioClass}">${m.priority}</span></td>
                  <td class="table-mono">${m.robot}</td>
                  <td><span class="synq-badge cbs" style="font-size:9px;">${m.payload}</span></td>
                  <td>${m.from}</td>
                  <td>${m.to}</td>
                  <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <div class="battery-bar-track" style="width: 60px; height: 5px;">
                        <div class="battery-bar-fill nominal" style="width: ${m.progress}%;"></div>
                      </div>
                      <span class="table-mono" style="font-size: 10px;">${m.eta}</span>
                    </div>
                  </td>
                  <td><span class="synq-badge ${stClass}"><span class="synq-badge-dot ${m.status === 'IN_TRANSIT' ? 'radar-ping' : ''}"></span>${m.status}</span></td>
                  <td>
                    <button class="synq-btn" style="padding: 3px 8px; font-size: 10px;" onclick="playHapticClick('high'); inspectRobotFromMatrix('${m.robot}');">
                      <span>Inspect</span>
                    </button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `}
  `;
}

function openQuickOrderModal() {
  navigateTo('overview');
  setPanelTab('dispatch');
}

/* ==========================================================================
   3. WAREHOUSE TOPOLOGY VIEW (Storage Bays & Stations)
   ========================================================================== */
function renderWarehouseView() {
  const container = document.getElementById('warehouseViewContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Warehouse Topology & Spatio-Temporal Graph</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>TOPOLOGICAL GRAPH COMPILED</span>
      </div>
      <div style="font-size: 11px; color: var(--synq-text-muted);">
        Grid Size: <strong>15.0m × 15.0m</strong> · Nodes: <strong>16</strong> · Edges: <strong>24</strong> · Racks: <strong>6</strong>
      </div>
    </div>

    <!-- Storage Bays & Zones Grid with Spotlight Cards -->
    <div class="synq-grid-3">
      ${WAREHOUSE.racks.map(rack => `
        <div class="synq-card spotlight-card" style="padding: 14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
            <span style="font-size: 12px; font-weight: 700; color: #ffffff;">${rack.name}</span>
            <span class="synq-badge neutral" style="font-size: 9px;">BAY ${rack.id}</span>
          </div>
          <div class="robot-spec-grid" style="margin-bottom: 8px;">
            <div class="robot-spec-item">
              <span class="robot-spec-label">Footprint</span>
              <span class="robot-spec-val">${rack.w}m × ${rack.h}m</span>
            </div>
            <div class="robot-spec-item">
              <span class="robot-spec-label">Position (X, Y)</span>
              <span class="robot-spec-val">(${rack.x.toFixed(1)}, ${rack.y.toFixed(1)})</span>
            </div>
            <div class="robot-spec-item">
              <span class="robot-spec-label">Storage Capacity</span>
              <span class="robot-spec-val">64 Pallets</span>
            </div>
            <div class="robot-spec-item">
              <span class="robot-spec-label">Access Lanes</span>
              <span class="robot-spec-val">North / South</span>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between; font-size: 10px; color: var(--synq-text-muted);">
            <span>Slot Occupancy: 87.5%</span>
            <span style="color: var(--synq-status-online); font-weight:600;">Clear Headway</span>
          </div>
        </div>
      `).join('')}
    </div>

    <!-- Zones Specifications -->
    <div class="synq-table-wrap">
      <div style="padding: 10px 14px; background: var(--synq-bg-elevated); border-bottom: 1px solid var(--synq-border-default); font-size: 11px; font-weight: 700;">
        Specialized Facility Stations & Kinetic Rules
      </div>
      <table class="synq-table">
        <thead>
          <tr>
            <th>Zone ID</th>
            <th>Type</th>
            <th>Location</th>
            <th>Dimensions</th>
            <th>Speed Cap</th>
            <th>Safety Protocol</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${WAREHOUSE.zones.map(z => `
            <tr>
              <td class="table-mono" style="font-weight:700; color:#58a6ff;">${z.id}</td>
              <td><span class="synq-badge ${z.type === 'PICK' ? 'online' : (z.type === 'DROP' ? 'active' : 'warning')}">${z.type}</span></td>
              <td class="table-mono">(${z.x.toFixed(1)}, ${z.y.toFixed(1)})</td>
              <td>${z.w}m × ${z.h}m</td>
              <td class="table-mono">${z.type === 'CHARGE' ? '0.3 m/s' : '0.5 m/s'}</td>
              <td>LiDAR Slowdown & Ultrasonic Precision Alignment</td>
              <td><span class="synq-badge online"><span class="synq-badge-dot"></span>READY</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

/* ==========================================================================
   4. MODULAR PAYLOAD SPECIFICATIONS VIEW (Visual SVG Schematics & Calibration)
   ========================================================================== */
function renderPayloadsView() {
  const container = document.getElementById('payloadsViewContainer');
  if (!container) return;

  const payloads = [
    {
      name: "Scissor Lift Mechanism",
      code: "synQ-PL-LIFT-26",
      type: "SCISSOR_LIFT",
      rating: "500 kg Payload Capacity",
      svgDiagram: `
        <svg width="100%" height="70" viewBox="0 0 200 70" style="background:#0b0d10; border-radius:4px; border:1px solid #222935;">
          <!-- Base Plate -->
          <rect x="20" y="58" width="160" height="6" fill="#1f242d" stroke="#38bdf8" stroke-width="0.8"/>
          <!-- Top Deck -->
          <rect x="20" y="8" width="160" height="6" fill="#1f242d" stroke="#a371f7" stroke-width="0.8"/>
          <!-- Pantograph Linkage -->
          <line x1="30" y1="58" x2="100" y2="14" stroke="#a371f7" stroke-width="2.5"/>
          <line x1="100" y1="58" x2="30" y2="14" stroke="#a371f7" stroke-width="2.5"/>
          <line x1="100" y1="58" x2="170" y2="14" stroke="#a371f7" stroke-width="2.5"/>
          <line x1="170" y1="58" x2="100" y2="14" stroke="#a371f7" stroke-width="2.5"/>
          <!-- Central Pivot Pin -->
          <circle cx="65" cy="36" r="3" fill="#ffffff"/>
          <circle cx="135" cy="36" r="3" fill="#ffffff"/>
        </svg>
      `,
      description: "Dual-pantograph electro-mechanical scissor lift engineered for standard Euro and GMA pallets. Features twin synchronized 48V brushless linear drive screws.",
      specs: [
        ["Max Lift Stroke", "450 mm (Vertical)"],
        ["Lifting Speed", "35 mm/s (Nominal)"],
        ["Actuator Power", "650 W Twin BLDC"],
        ["Tare Weight", "42.5 kg"],
        ["Interlock Safety", "Dual optical top-dead-center limit switches"],
        ["Equipped Units", "synq-amr-01"]
      ]
    },
    {
      name: "Powered Roller Conveyor Deck",
      code: "synQ-PL-CONV-12",
      type: "ROLLER_CONVEYOR",
      rating: "300 kg Payload Capacity",
      svgDiagram: `
        <svg width="100%" height="70" viewBox="0 0 200 70" style="background:#0b0d10; border-radius:4px; border:1px solid #222935;">
          <!-- Bed Frame -->
          <rect x="20" y="44" width="160" height="18" fill="#1f242d" stroke="#222935" stroke-width="1"/>
          <!-- Rollers -->
          <circle cx="35" cy="32" r="10" fill="#14181f" stroke="#38bdf8" stroke-width="1.8"/>
          <circle cx="65" cy="32" r="10" fill="#14181f" stroke="#38bdf8" stroke-width="1.8"/>
          <circle cx="95" cy="32" r="10" fill="#14181f" stroke="#38bdf8" stroke-width="1.8"/>
          <circle cx="125" cy="32" r="10" fill="#14181f" stroke="#38bdf8" stroke-width="1.8"/>
          <circle cx="155" cy="32" r="10" fill="#14181f" stroke="#38bdf8" stroke-width="1.8"/>
          <!-- Drive Belt Line -->
          <line x1="35" y1="42" x2="155" y2="42" stroke="#2ea043" stroke-width="1.5" stroke-dasharray="4,2"/>
        </svg>
      `,
      description: "Bidirectional motorized roller deck with photoelectric tote presence detection. Connects seamlessly to fixed warehouse gravity and automated conveyors.",
      specs: [
        ["Roller Width", "620 mm"],
        ["Roller Pitch", "75 mm Center-to-Center"],
        ["Transfer Speed", "0.40 m/s (Adjustable)"],
        ["Tare Weight", "34.0 kg"],
        ["Interlock Safety", "Pneumatic end-stop tote gate"],
        ["Equipped Units", "synq-amr-02"]
      ]
    },
    {
      name: "Precision Tote Clamping Gripper",
      code: "synQ-PL-GRIP-04",
      type: "TOTE_GRIPPER",
      rating: "80 kg Payload Capacity",
      svgDiagram: `
        <svg width="100%" height="70" viewBox="0 0 200 70" style="background:#0b0d10; border-radius:4px; border:1px solid #222935;">
          <!-- Linear Guide Bar -->
          <rect x="25" y="16" width="150" height="8" fill="#1f242d" stroke="#222935"/>
          <!-- Left Jaw -->
          <rect x="45" y="16" width="12" height="42" rx="2" fill="#2ea043" stroke="#3fb950" stroke-width="1"/>
          <!-- Right Jaw -->
          <rect x="143" y="16" width="12" height="42" rx="2" fill="#2ea043" stroke="#3fb950" stroke-width="1"/>
          <!-- Clamping arrows -->
          <line x1="65" y1="36" x2="85" y2="36" stroke="#ffffff" stroke-width="1.5"/>
          <polyline points="75,32 85,36 75,40" fill="none" stroke="#ffffff" stroke-width="1.5"/>
          <line x1="135" y1="36" x2="115" y2="36" stroke="#ffffff" stroke-width="1.5"/>
          <polyline points="125,32 115,36 125,40" fill="none" stroke="#ffffff" stroke-width="1.5"/>
        </svg>
      `,
      description: "Servo-driven parallel clamping jaws with high-friction silicone grippers and continuous load-cell force feedback for KLT and plastic container transfer.",
      specs: [
        ["Clamping Stroke", "280 mm to 650 mm"],
        ["Grip Force", "50 N to 400 N (Closed-loop)"],
        ["Actuation Time", "1.2 s (Full Stroke)"],
        ["Tare Weight", "22.8 kg"],
        ["Interlock Safety", "Spring-loaded mechanical lock on power loss"],
        ["Equipped Units", "synq-amr-03"]
      ]
    }
  ];

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Modular Payload Architecture</span>
        <span class="synq-badge cbs"><span class="synq-badge-dot radar-ping"></span>VDA 5050 EXTENSION MODULE</span>
      </div>
      <div style="font-size: 11px; color: var(--synq-text-secondary);">
        Standardized quick-release mechanical interface with CANopen / EtherCAT safety bus.
      </div>
    </div>

    <div class="synq-grid-3">
      ${payloads.map(p => `
        <div class="payload-card spotlight-card">
          <div class="payload-hero-header">
            <div>
              <div class="payload-model-name">${p.name}</div>
              <div class="payload-code">${p.code}</div>
            </div>
            <span class="synq-badge cbs">${p.type}</span>
          </div>

          <!-- Schematic Wireframe -->
          ${p.svgDiagram}

          <div style="font-size: 11px; color: var(--synq-status-online); font-weight: 600;">
            ${p.rating}
          </div>

          <p style="font-size: 11px; color: var(--synq-text-secondary); line-height: 1.4;">
            ${p.description}
          </p>

          <table class="payload-specs-table">
            <tbody>
              ${p.specs.map(([k, v]) => `
                <tr>
                  <td>${k}</td>
                  <td>${v}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>

          <div style="display: flex; gap: 6px; margin-top: auto;">
            <button class="synq-btn" id="btnCalib-${p.type}" style="flex: 1;" onclick="playHapticClick('high'); runPayloadCalibration('${p.type}');">
              <span>Calibrate Actuator</span>
            </button>
            <button class="synq-btn" onclick="playHapticClick('high'); testPayloadDiagnostics('${p.type}');">
              <span>Diagnostics</span>
            </button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function runPayloadCalibration(type) {
  const btn = document.getElementById(`btnCalib-${type}`);
  if (btn) {
    btn.innerHTML = '<span>Calibrating...</span>';
    btn.disabled = true;
  }
  showToast(`Calibrating ${type} actuator zero-reference point via CANopen encoder...`);

  setTimeout(() => {
    if (btn) {
      btn.innerHTML = '<span>Calibrated ✓</span>';
      btn.disabled = false;
      setTimeout(() => { btn.innerHTML = '<span>Calibrate Actuator</span>'; }, 2500);
    }
    showToast(`${type} Calibration Verified: Offset 0.00mm, Current Draw Nominal.`);
    logEvent('Payload FMS', `${type} completed zero-point encoder calibration.`);
  }, 1200);
}

function testPayloadDiagnostics(type) {
  showToast(`Diagnostics for ${type}: Motor current nominal (1.4A), Thermals 32°C.`);
  logEvent('Payload FMS', `${type} self-test passed with zero faults.`);
}

/* ==========================================================================
   5. SIMULATION & WHAT-IF SCENARIOS (Interactive Stress-Testing Suite)
   ========================================================================== */
function renderSimulationView() {
  const container = document.getElementById('simulationViewContainer');
  if (!container) return;

  const scenarios = [
    {
      title: "Corridor Head-on Conflict (CBS)",
      desc: "Dispatches two AMRs into the same narrow transit aisle to demonstrate Conflict-Based Search spatio-temporal branch deconfliction.",
      risk: "MEDIUM",
      btnText: "Inject Vertex Collision",
      action: "triggerCbsConflictScenario()"
    },
    {
      title: "Sudden Human / Pallet Obstacle",
      desc: "Simulates an unmapped physical obstacle appearing directly in an AMR's active trajectory, triggering Nav2 MPPI emergency stop and SmacPlanner replanning.",
      risk: "HIGH",
      btnText: "Inject Path Obstacle",
      action: "injectSimObstacle()"
    },
    {
      title: "Battery Critical Dropout",
      desc: "Forces an AMR's State of Charge down to 5%, triggering immediate dynamic mission cancellation, load dropoff, and priority emergency charging routing.",
      risk: "HIGH",
      btnText: "Drop AMR-02 SoC to 5%",
      action: "triggerLowBatteryScenario()"
    },
    {
      title: "Payload Actuator Jam",
      desc: "Simulates a scissor lift motor stall during pallet transfer, testing fault isolation, safety interlock tripping, and task reallocation.",
      risk: "CRITICAL",
      btnText: "Trip Actuator Fault",
      action: "triggerActuatorJamScenario()"
    },
    {
      title: "Station Congestion Bottleneck",
      desc: "Injects 5 concurrent pickup requests at Pick Station P1 to verify FMS automated waiting queue and buffer staging logic.",
      risk: "LOW",
      btnText: "Flood Station P1",
      action: "triggerStationCongestion()"
    },
    {
      title: "Global Safety Bus E-Stop",
      desc: "Trips the facility-wide ISO 13849 Category 4 hardware safety loop, verifying zero-lag kinematic deceleration to a full stop.",
      risk: "CRITICAL",
      btnText: "Engage Facility E-Stop",
      action: "toggleGlobalEstop()"
    }
  ];

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Simulation Sandbox & "Break the Facility" Suite</span>
        <span class="synq-badge warning"><span class="synq-badge-dot radar-ping"></span>SYNTHETIC TEST ENVIRONMENT</span>
      </div>
      <div style="font-size: 11px; color: var(--synq-text-muted);">
        Non-destructive stress-testing for autonomy, routing robustness, and fault recovery.
      </div>
    </div>

    <!-- Realtime Simulation Controls Ribbon (Phase 5) -->
    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:16px; padding:10px 14px; background:var(--synq-bg-panel); border:1px solid var(--synq-border-subtle); border-radius:6px;">
      <span style="font-size:11px; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:0.5px; margin-right:6px;">Autonomous Simulation Controls:</span>
      <button class="synq-btn" onclick="playHapticClick('high'); promptSpawnAMR(); renderSimulationView();"><span>+ Spawn AMR</span></button>
      <button class="synq-btn" onclick="playHapticClick('low'); promptRemoveAMR(); renderSimulationView();"><span>− Remove AMR</span></button>
      <button class="synq-btn" onclick="playHapticClick('high'); navigateTo('overview'); toggleObstaclePlacement();"><span>Inject Obstacle</span></button>
      <button class="synq-btn" onclick="playHapticClick('high'); navigateTo('overview'); triggerCbsConflictScenario();"><span>Simulate CBS Crossing</span></button>
      <button class="synq-btn" id="simViewPauseBtn" onclick="playHapticClick('high'); toggleSimPause(); const b=document.getElementById('simViewPauseBtn'); if(b) b.querySelector('span').textContent = (window.synqStore && window.synqStore.system.isPaused) ? 'Resume Sim' : 'Pause Sim';">
        <span>${(window.synqStore && window.synqStore.system.isPaused) ? 'Resume Sim' : 'Pause Sim'}</span>
      </button>
      <button class="synq-btn" onclick="playHapticClick('high'); resetSimulationState(); renderSimulationView();"><span>Reset Simulation</span></button>
    </div>

    <!-- Scenarios Grid with Spotlight Cards -->
    <div class="synq-grid-3">
      ${scenarios.map(s => `
        <div class="scenario-card spotlight-card">
          <div>
            <div class="scenario-title">
              <span>${s.title}</span>
              <span class="synq-badge ${s.risk === 'CRITICAL' ? 'critical' : (s.risk === 'HIGH' ? 'warning' : 'neutral')}" style="font-size:9px;">
                ${s.risk}
              </span>
            </div>
            <p class="scenario-desc" style="margin-top: 8px;">${s.desc}</p>
          </div>
          <button class="synq-btn" onclick="playHapticClick('high'); ${s.action};" style="margin-top: 10px;">
            <span>${s.btnText}</span>
          </button>
        </div>
      `).join('')}
    </div>

    <!-- Capacity Simulator Box -->
    <div class="synq-card spotlight-card" style="padding: 16px;">
      <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 6px;">
        Facility Throughput & Scaling Simulator ("What-If" Analysis)
      </div>
      <p style="font-size: 11px; color: var(--synq-text-secondary); margin-bottom: 14px;">
        Adjust operational variables to evaluate fleet bottleneck points and estimated picks-per-hour (PPH).
      </p>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;">
        <div>
          <label style="font-size: 10px; color: var(--synq-text-muted); font-weight: 700; text-transform: uppercase;">Active Fleet Size: <strong id="simFleetSizeVal" style="color: #58a6ff;">3 AMRs</strong></label>
          <input type="range" min="1" max="16" value="3" style="width: 100%; margin-top: 6px;" oninput="document.getElementById('simFleetSizeVal').textContent = this.value + ' AMRs'; updateWhatIfStats();">
        </div>
        <div>
          <label style="font-size: 10px; color: var(--synq-text-muted); font-weight: 700; text-transform: uppercase;">Order Inflow Rate: <strong id="simOrderRateVal" style="color: #58a6ff;">60 orders/hr</strong></label>
          <input type="range" min="10" max="200" step="10" value="60" style="width: 100%; margin-top: 6px;" oninput="document.getElementById('simOrderRateVal').textContent = this.value + ' orders/hr'; updateWhatIfStats();">
        </div>
        <div>
          <label style="font-size: 10px; color: var(--synq-text-muted); font-weight: 700; text-transform: uppercase;">Aisle Speed Cap: <strong id="simSpeedVal" style="color: #58a6ff;">1.2 m/s</strong></label>
          <input type="range" min="0.5" max="2.5" step="0.1" value="1.2" style="width: 100%; margin-top: 6px;" oninput="document.getElementById('simSpeedVal').textContent = this.value + ' m/s'; updateWhatIfStats();">
        </div>
      </div>

      <div style="margin-top: 14px; padding: 12px; background: var(--synq-bg-canvas); border: 1px solid var(--synq-border-default); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <span style="font-size: 10px; color: var(--synq-text-muted);">PROJECTED FACILITY THROUGHPUT:</span>
          <span id="whatIfThroughput" style="font-size: 14px; font-weight: 700; font-family: var(--synq-font-mono); color: var(--synq-status-online); margin-left: 8px;">142 Picks / Hour</span>
        </div>
        <div>
          <span style="font-size: 10px; color: var(--synq-text-muted);">ESTIMATED CONFLICT RATE:</span>
          <span id="whatIfConflicts" style="font-size: 14px; font-weight: 700; font-family: var(--synq-font-mono); color: var(--synq-status-cbs); margin-left: 8px;">1.4 resolves / hr</span>
        </div>
        <button class="synq-btn" onclick="playHapticClick('high'); applyWhatIfScenario();">
          <span>Run Simulation Benchmark</span>
        </button>
      </div>
    </div>
  `;
}

function injectSimObstacle() {
  navigateTo('overview');
  toggleObstaclePlacement();
}

function triggerLowBatteryScenario() {
  ROBOTS["synq-amr-02"].battery = 5.0;
  ROBOTS["synq-amr-02"].status = "Navigating";
  ROBOTS["synq-amr-02"].destination = "Fast Charger C1";
  ROBOTS["synq-amr-02"].route = ["N_3_3", "N_2_3", "N_1_3", "N_0_3", "N_0_2", "N_0_1", "N_0_0"];
  showToast("BATTERY ALERT: synq-amr-02 SoC dropped to 5.0%! Auto-docking route dispatched.");
  logEvent("Battery Guard", "synq-amr-02 SoC at 5.0%. Emergency mission preempt engaged.");
  navigateTo('overview');
  setPanelTab('inspector');
}

function triggerActuatorJamScenario() {
  showToast("ACTUATOR INTERLOCK: synq-amr-01 Scissor Lift motor stall detected. Interlock tripped.");
  logEvent("Payload Safety", "synq-amr-01 Scissor Lift overcurrent limit reached (12.4A > 8.0A max).");
  navigateTo('overview');
  setPanelTab('autonomy');
}

function triggerStationCongestion() {
  showToast("Station P1 Congestion: 5 orders queued. CBS Space-Time routing buffer bays engaged.");
  logEvent("FMS", "Station P1 ingress saturated. Dynamic buffer queue active.");
}

function updateWhatIfStats() {
  const fleet = parseInt(document.getElementById('simFleetSizeVal').textContent) || 3;
  const pph = Math.round(fleet * 46.8);
  const conf = (fleet * 0.45).toFixed(1);
  const tpEl = document.getElementById('whatIfThroughput');
  const confEl = document.getElementById('whatIfConflicts');
  if (tpEl) tpEl.textContent = `${pph} Picks / Hour`;
  if (confEl) confEl.textContent = `${conf} resolves / hr`;
}

function applyWhatIfScenario() {
  showToast("Monte-Carlo Benchmark completed: 10,000 iterations evaluated. Facility stable.");
  logEvent("Simulation", "What-If Monte-Carlo capacity test finished with zero gridlock conditions.");
}

/* ==========================================================================
   6. TELEMETRY & SPARKLINE CHARTS VIEW
   ========================================================================== */
function renderTelemetryView() {
  const container = document.getElementById('telemetryViewContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Real-Time Telemetry & Hardware Sparklines</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>50 Hz HIGH RESOLUTION</span>
      </div>
      <div style="font-size: 11px; color: var(--synq-text-muted);">
        Streaming via WebSockets & FastDDS RTPS
      </div>
    </div>

    <!-- Charts Grid with Spotlight Cards -->
    <div class="synq-grid-2">
      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color:#fff;">Fleet Aggregate Velocity</div>
            <div style="font-size: 10px; color: var(--synq-text-muted);">Instantaneous speed across all active drives (m/s)</div>
          </div>
          <span class="synq-badge online">0.85 m/s PEAK</span>
        </div>
        <canvas id="canvasSpeedTelemetry" height="140" style="width: 100%; display:block;"></canvas>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color:#fff;">CBS Solver Latency</div>
            <div style="font-size: 10px; color: var(--synq-text-muted);">Space-Time Constraint Tree solve time (ms)</div>
          </div>
          <span class="synq-badge cbs">4.2 ms AVG</span>
        </div>
        <canvas id="canvasCbsTelemetry" height="140" style="width: 100%; display:block;"></canvas>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color:#fff;">LiFePO4 Discharge Profile</div>
            <div style="font-size: 10px; color: var(--synq-text-muted);">Voltage vs SoC degradation curve</div>
          </div>
          <span class="synq-badge active">52.8 V NOMINAL</span>
        </div>
        <canvas id="canvasBatteryTelemetry" height="140" style="width: 100%; display:block;"></canvas>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color:#fff;">ROS 2 DDS Network Jitter</div>
            <div style="font-size: 10px; color: var(--synq-text-muted);">Packet latency and micro-second round-trip time</div>
          </div>
          <span class="synq-badge online">0.38 ms JITTER</span>
        </div>
        <canvas id="canvasJitterTelemetry" height="140" style="width: 100%; display:block;"></canvas>
      </div>
    </div>
  `;

  // Draw procedural synthetic telemetry sparklines
  setTimeout(() => {
    drawSyntheticSparkline("canvasSpeedTelemetry", "#2f81f7", [0.2, 0.4, 0.85, 0.85, 0.82, 0.85, 0.70, 0.85, 0.85, 0.4, 0.0, 0.3, 0.85, 0.85]);
    drawSyntheticSparkline("canvasCbsTelemetry", "#a371f7", [3.2, 4.1, 8.5, 14.2, 5.0, 4.2, 3.8, 4.0, 6.2, 3.9, 4.2, 4.0]);
    drawSyntheticSparkline("canvasBatteryTelemetry", "#2ea043", [95, 94.8, 94.5, 94.2, 93.9, 93.5, 93.0, 92.4, 91.8, 91.2]);
    drawSyntheticSparkline("canvasJitterTelemetry", "#38bdf8", [0.4, 0.38, 0.42, 0.35, 0.39, 0.52, 0.38, 0.37, 0.36, 0.38]);
  }, 60);
}

function drawSyntheticSparkline(canvasId, strokeColor, points) {
  const c = document.getElementById(canvasId);
  if (!c) return;
  c.width = c.clientWidth * (window.devicePixelRatio || 1);
  c.height = c.clientHeight * (window.devicePixelRatio || 1);
  const ctx = c.getContext('2d');
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

  const w = c.clientWidth;
  const h = c.clientHeight;

  ctx.clearRect(0, 0, w, h);

  // Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  ctx.lineWidth = 1;
  for (let y = 20; y < h; y += 30) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  const min = Math.min(...points) * 0.9;
  const max = Math.max(...points) * 1.1;
  const step = w / (points.length - 1);

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((val, idx) => {
    const x = idx * step;
    const y = h - ((val - min) / (max - min)) * (h - 20) - 10;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Area fill
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = strokeColor + "18";
  ctx.fill();
}

/* ==========================================================================
   7. DIAGNOSTICS & ROS 2 MONITOR (Log Searching & Terminal Diagnostics)
   ========================================================================== */
function renderDiagnosticsView() {
  const container = document.getElementById('diagnosticsViewContainer');
  if (!container) return;

  const nodes = [
    { name: "/synq_amr_01/lifecycle_amr", pkg: "synq_lifecycle", state: "ACTIVE", hz: "50.0 Hz", pid: 28410 },
    { name: "/cbs_coordinator/planner_server", pkg: "synq_cbs_planner", state: "ACTIVE", hz: "20.0 Hz", pid: 28411 },
    { name: "/nav2_mppi_controller", pkg: "nav2_mppi_controller", state: "ACTIVE", hz: "50.0 Hz", pid: 28414 },
    { name: "/perception/lidar_safety_filter", pkg: "synq_safety", state: "ACTIVE", hz: "25.0 Hz", pid: 28416 },
    { name: "/fms/vda5050_ingest_adapter", pkg: "synq_vda5050", state: "ACTIVE", hz: "10.0 Hz", pid: 28420 },
    { name: "/telemetry/websocket_bridge", pkg: "synq_bridge", state: "ACTIVE", hz: "50.0 Hz", pid: 28422 }
  ];

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">System Diagnostics & ROS 2 Core Monitor</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>6 NODES CONVERGED</span>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <button class="synq-btn" onclick="playHapticClick('high'); exportDiagnosticsLog();">
          <span>Export Logs (.txt)</span>
        </button>
      </div>
    </div>

    <!-- Active Nodes Table -->
    <div class="synq-table-wrap">
      <table class="synq-table">
        <thead>
          <tr>
            <th>Node Name</th>
            <th>Package</th>
            <th>Lifecycle State</th>
            <th>Frequency</th>
            <th>Process ID</th>
            <th>Health Check</th>
          </tr>
        </thead>
        <tbody>
          ${nodes.map(n => `
            <tr>
              <td class="table-mono" style="color:#58a6ff; font-weight:600;">${n.name}</td>
              <td>${n.pkg}</td>
              <td><span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>${n.state}</span></td>
              <td class="table-mono">${n.hz}</td>
              <td class="table-mono" style="color:var(--synq-text-muted);">${n.pid}</td>
              <td><span style="color: var(--synq-status-online); font-weight:600;">0 dropped frames</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <!-- ROS 2 Live Topic Frequencies & QoS Profiles (Foxglove Pattern) -->
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
      <!-- Column 1: Live ROS 2 Topic Stream Directory -->
      <div class="spotlight-card" style="background: var(--synq-bg-surface); border: 1px solid var(--synq-border-default); border-radius: 6px; padding: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
          <div style="font-size:12px; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Live ROS 2 Topics & QoS Profiles
          </div>
          <span class="synq-badge online" style="font-size:9px;"><span class="synq-badge-dot radar-ping"></span>8 ACTIVE TOPICS</span>
        </div>
        <div style="overflow-x:auto;">
          <table class="synq-table" style="font-size:10px;">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Type</th>
                <th>Rate</th>
                <th>QoS</th>
              </tr>
            </thead>
            <tbody>
              <tr><td class="table-mono" style="color:#58a6ff;">/scan</td><td>LaserScan</td><td class="table-mono" style="color:#3fb950;">25.0 Hz</td><td>BestEffort</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/odom</td><td>Odometry</td><td class="table-mono" style="color:#3fb950;">50.0 Hz</td><td>BestEffort</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/tf</td><td>TFMessage</td><td class="table-mono" style="color:#3fb950;">100.0 Hz</td><td>BestEffort</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/cmd_vel</td><td>Twist</td><td class="table-mono" style="color:#3fb950;">50.0 Hz</td><td>BestEffort</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/battery_state</td><td>BatteryState</td><td class="table-mono" style="color:#38bdf8;">5.0 Hz</td><td>Reliable</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/safety_status</td><td>SafetyStatus</td><td class="table-mono" style="color:#3fb950;">20.0 Hz</td><td>Reliable</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/fleet/vda5050_order</td><td>Order</td><td class="table-mono" style="color:#a371f7;">10.0 Hz</td><td>Reliable</td></tr>
              <tr><td class="table-mono" style="color:#58a6ff;">/automap/pointcloud</td><td>PointCloud2</td><td class="table-mono" style="color:#38bdf8;">10.0 Hz</td><td>BestEffort</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Column 2: TF2 Coordinate Frame Hierarchy Tree -->
      <div class="spotlight-card" style="background: var(--synq-bg-surface); border: 1px solid var(--synq-border-default); border-radius: 6px; padding: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
          <div style="font-size:12px; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:0.5px; display:flex; align-items:center; gap:6px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a371f7" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
            TF2 Coordinate Frame Hierarchy
          </div>
          <span class="synq-badge online" style="font-size:9px;">TF BROADCASTER: ACTIVE</span>
        </div>
        <div style="background: var(--synq-bg-subtle, #0a0d11); border: 1px solid var(--synq-border-light, #222935); border-radius: 4px; padding: 10px; font-family: var(--synq-font-mono); font-size: 10px; line-height: 1.6; color: #c9d1d9;">
          <div><strong style="color:#38bdf8;">map</strong> <span style="color:var(--text-muted); font-size:9px;">[world origin (0,0,0)]</span></div>
          <div style="padding-left: 14px;">└── <strong style="color:#3fb950;">odom</strong> <span style="color:#a371f7; font-size:9px;">@ 50.0 Hz (FastDDS EKF)</span></div>
          <div style="padding-left: 28px;">└── <strong style="color:#f0f3f6;">base_link</strong> <span style="color:var(--text-muted); font-size:9px;">[chassis center]</span></div>
          <div style="padding-left: 42px;">├── <strong style="color:#38bdf8;">laser_frame</strong> <span style="color:var(--text-secondary); font-size:9px;">[+0.28m, 0.00m, +0.18m] @ 100Hz</span></div>
          <div style="padding-left: 42px;">├── <strong style="color:#d29922;">imu_link</strong> <span style="color:var(--text-secondary); font-size:9px;">[0.00m, 0.00m, +0.10m] @ 100Hz</span></div>
          <div style="padding-left: 42px;">├── <strong style="color:#a371f7;">payload_deck</strong> <span style="color:var(--text-secondary); font-size:9px;">[0.00m, 0.00m, +0.35m] @ 50Hz</span></div>
          <div style="padding-left: 42px;">└── <strong style="color:#c9d1d9;">wheel_[fl,fr,rl,rr]</strong> <span style="color:var(--text-secondary); font-size:9px;">[4WD Mecanum] @ 50Hz</span></div>
        </div>
      </div>
    </div>

    <!-- ACETERNITY TERMINAL: ROS 2 KERNEL & FASTDDS EVENT STREAM -->
    <div class="aceternity-terminal spotlight-card" style="margin-bottom: 16px;">
      <div class="terminal-titlebar">
        <div class="terminal-controls">
          <span class="mac-dot mac-dot-red"></span>
          <span class="mac-dot mac-dot-yellow"></span>
          <span class="mac-dot mac-dot-green"></span>
        </div>
        <div class="terminal-title-text">bash — ros2 run synq_cbs_planner coordinator_node</div>
        <span class="synq-badge active" style="font-size: 9px;"><span class="synq-badge-dot radar-ping"></span>STREAMING (FastDDS)</span>
      </div>

      <div class="terminal-actions-bar">
        <div class="animated-tabs-strip" style="background: rgba(0,0,0,0.3); border:none; padding:2px;">
          <button class="animated-tab-item active" id="termTabAll" onclick="switchTerminalTopic('ALL')">All Topics</button>
          <button class="animated-tab-item" id="termTabNav" onclick="switchTerminalTopic('/cmd_vel')">/cmd_vel & /odom</button>
          <button class="animated-tab-item" id="termTabScan" onclick="switchTerminalTopic('/scan')">/scan (LiDAR)</button>
          <button class="animated-tab-item" id="termTabCbs" onclick="switchTerminalTopic('CBS')">CBS Planner</button>
        </div>
        <div style="margin-left: auto; display:flex; gap:6px; align-items:center;">
          <input type="text" id="logSearchInput" class="select-input" style="width: 150px; margin-bottom:0; font-size:10px; padding:3px 8px;" placeholder="Filter log regex..." oninput="filterTerminalLogs(this.value)">
          <button class="synq-btn" style="padding: 3px 8px; font-size: 10px;" onclick="playHapticClick('high'); clearTerminalLogs();">Clear</button>
          <button class="stateful-btn" style="padding: 3px 10px; font-size: 10px;" onclick="triggerStatefulButton(this, () => copyTerminalOutput(), 'Copied ✓')">
            <span>Copy Terminal</span>
          </button>
        </div>
      </div>

      <div class="terminal-body" id="diagTerminalConsole">
        ${renderLogLines(diagLogFilter)}
      </div>
    </div>

    <!-- ACETERNITY CODE BLOCK: SYSTEM ARCHITECTURE & INTEROP SPECS -->
    <div class="aceternity-code-block spotlight-card">
      <div class="code-block-header">
        <div class="code-block-filename">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
          <span id="codeBlockTabTitle">vda5050_order_dispatch.json</span>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <div class="animated-tabs-strip" style="background: rgba(0,0,0,0.3); border:none; padding:2px;">
            <button class="animated-tab-item active" id="codeTabJson" onclick="switchCodeBlockTab('JSON')">VDA 5050 Order</button>
            <button class="animated-tab-item" id="codeTabYaml" onclick="switchCodeBlockTab('YAML')">CBS Trajectory Plan</button>
          </div>
          <button class="stateful-btn" style="padding: 3px 10px; font-size: 10px;" onclick="triggerStatefulButton(this, () => copyCodeBlock(), 'Copied ✓')">
            <span>Copy Code</span>
          </button>
        </div>
      </div>
      <pre class="code-block-content" id="codeBlockDisplayContent">${getCodeSnippet('JSON')}</pre>
    </div>
  `;
}

let activeTerminalTopic = 'ALL';
function switchTerminalTopic(topic) {
  playHapticClick('high');
  activeTerminalTopic = topic;
  ['termTabAll', 'termTabNav', 'termTabScan', 'termTabCbs'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });
  if (topic === 'ALL') document.getElementById('termTabAll')?.classList.add('active');
  if (topic === '/cmd_vel') document.getElementById('termTabNav')?.classList.add('active');
  if (topic === '/scan') document.getElementById('termTabScan')?.classList.add('active');
  if (topic === 'CBS') document.getElementById('termTabCbs')?.classList.add('active');

  const q = (topic === 'ALL') ? '' : topic;
  filterTerminalLogs(q);
}

let activeCodeTab = 'JSON';
function switchCodeBlockTab(tab) {
  playHapticClick('high');
  activeCodeTab = tab;
  document.getElementById('codeTabJson')?.classList.toggle('active', tab === 'JSON');
  document.getElementById('codeTabYaml')?.classList.toggle('active', tab === 'YAML');
  document.getElementById('codeBlockTabTitle').textContent = tab === 'JSON' ? 'vda5050_order_dispatch.json' : 'cbs_spatio_temporal_constraint.yaml';
  document.getElementById('codeBlockDisplayContent').textContent = getCodeSnippet(tab);
}

function getCodeSnippet(type) {
  if (type === 'YAML') {
    return `# CBS Spatio-Temporal Constraint Tree Export
planner: synq_cbs_v3
facility: austin_hub_01
timestamp: 1789790120.45
reservations:
  - node: "N_1_1"
    robot: "synq-amr-01"
    time_window: [1.0, 3.5]
    status: RESERVED
  - node: "N_1_2"
    robot: "synq-amr-03"
    time_window: [2.0, 4.5]
    status: DETOUR_BYPASS
metrics:
  cost_delta_sec: +1.2
  collision_count: 0
  feasibility: PROVEN`;
  }
  return `{
  "headerId": 14902,
  "timestamp": "2026-09-19T03:52:12Z",
  "version": "3.0.0",
  "manufacturer": "synQ Robotics",
  "orderId": "TASK-4821",
  "orderUpdateId": 0,
  "zoneId": "Austin-Hub-Floor01",
  "nodes": [
    { "nodeId": "N_0_0", "sequenceId": 0, "released": true, "nodePosition": { "x": 0.0, "y": 0.0 } },
    { "nodeId": "N_2_2", "sequenceId": 2, "released": true, "nodePosition": { "x": 10.0, "y": 10.0 } }
  ],
  "edges": [
    { "edgeId": "E_0_0_to_N_2_2", "sequenceId": 1, "startNodeId": "N_0_0", "endNodeId": "N_2_2", "released": true }
  ]
}`;
}

function copyTerminalOutput() {
  const text = ACTIVITIES.map(ev => `[${ev.time}:00] [${ev.robot}] ${ev.msg}`).join('\n');
  navigator.clipboard.writeText(text);
  showToast("Terminal buffer copied to clipboard");
}

function copyCodeBlock() {
  const text = getCodeSnippet(activeCodeTab);
  navigator.clipboard.writeText(text);
  showToast("Code block copied to clipboard");
}

function renderLogLines(filterText = '') {
  const query = filterText.toLowerCase().trim();
  const allLogs = [
    ...ACTIVITIES.map(ev => ({ time: `[${ev.time}:00]`, tag: '[INFO]', tagClass: 'log-tag-info', src: `[${ev.robot}]`, text: ev.msg })),
    { time: '[00:00:00]', tag: '[CBS]', tagClass: 'log-tag-cbs', src: '[Coordinator]', text: 'Space-Time Graph synchronized. Total nodes: 16, Vertices: 24, Reservations: 0' }
  ];

  const matched = allLogs.filter(l => {
    if (!query) return true;
    return l.src.toLowerCase().includes(query) || l.tag.toLowerCase().includes(query) || l.text.toLowerCase().includes(query);
  });

  if (matched.length === 0) {
    return `<div class="log-line"><span class="log-time">[Console]</span><span class="log-text">No log entries match "${filterText}".</span></div>`;
  }

  return matched.map(l => `
    <div class="log-line">
      <span class="log-time">${l.time}</span>
      <span class="${l.tagClass}">${l.tag}</span>
      <span class="log-src">${l.src}</span>
      <span class="log-text">${l.text}</span>
    </div>
  `).join('');
}

function filterTerminalLogs(q) {
  diagLogFilter = q;
  const consoleEl = document.getElementById('diagTerminalConsole');
  if (consoleEl) {
    consoleEl.innerHTML = renderLogLines(q);
  }
}

function exportDiagnosticsLog() {
  const content = ACTIVITIES.map(ev => `[${ev.time}:00] [${ev.robot}] ${ev.msg}`).join('\n');
  const blob = new Blob([content], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `synq-diagnostics-${Date.now()}.txt`;
  a.click();
  showToast("Diagnostic event stream exported to file.");
}

function clearTerminalLogs() {
  const term = document.getElementById('diagTerminalConsole');
  if (term) term.innerHTML = '<div class="log-line"><span class="log-time">[Console]</span><span class="log-text">Logs cleared by operator.</span></div>';
}

/* ==========================================================================
   8. SAFETY & HARDWARE INTERLOCKS VIEW
   ========================================================================== */
function renderSafetyView() {
  const container = document.getElementById('safetyViewContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">Industrial Safety Interlocks & Compliance</span>
        <span class="synq-badge online"><span class="synq-badge-dot radar-ping"></span>ISO 3691-4 / ISO 13849 PL-d CERTIFIED</span>
      </div>
      <button class="synq-btn" onclick="playHapticClick('low'); toggleGlobalEstop();" style="background: rgba(248,81,73,0.15); color:#f85149; border-color: rgba(248,81,73,0.3);">
        <span>${isEstopActive ? 'RESET ALL SAFETY CONTACTORS' : 'TRIGGER SAFETY INTERLOCK TEST'}</span>
      </button>
    </div>

    <!-- Safety Architecture Zones Grid with Spotlight Cards -->
    <div class="synq-grid-3">
      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size: 13px; font-weight: 700; color:#fff;">360° Safety LiDAR Fields</span>
          <span class="synq-badge online">ACTIVE</span>
        </div>
        <div style="margin: 12px 0; display:flex; flex-direction:column; gap: 8px;">
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Normal Field (2.5m)</span>
            <span class="table-mono" style="color:var(--synq-status-online);">Clear (100%)</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Slowdown Field (1.2m)</span>
            <span class="table-mono" style="color:var(--synq-status-online);">Unbroken</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Emergency Stop Field (0.45m)</span>
            <span class="table-mono" style="color:var(--synq-status-online);">Intact</span>
          </div>
        </div>
        <p style="font-size: 10px; color: var(--synq-text-secondary); line-height:1.4;">
          Dual optical safety scanners with hardware watchdog and anti-mute zone override protection.
        </p>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size: 13px; font-weight: 700; color:#fff;">Dual-Channel E-Stop Circuit</span>
          <span class="synq-badge ${isEstopActive ? 'critical' : 'online'}">${isEstopActive ? 'TRIPPED' : 'ARMED'}</span>
        </div>
        <div style="margin: 12px 0; display:flex; flex-direction:column; gap: 8px;">
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Channel A (Physical Relay)</span>
            <span class="table-mono" style="color: ${isEstopActive ? '#f85149' : 'var(--synq-status-online)'};">${isEstopActive ? 'OPEN' : 'CLOSED'}</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Channel B (Safety PLC)</span>
            <span class="table-mono" style="color: ${isEstopActive ? '#f85149' : 'var(--synq-status-online)'};">${isEstopActive ? 'OPEN' : 'CLOSED'}</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Dynamic Motor Braking</span>
            <span class="table-mono" style="color:var(--synq-status-online);">Ready</span>
          </div>
        </div>
        <p style="font-size: 10px; color: var(--synq-text-secondary); line-height:1.4;">
          Zero-speed dynamic braking relays engage mechanically in < 15ms upon line de-energization.
        </p>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size: 13px; font-weight: 700; color:#fff;">Inclinometer & Rollover Protection</span>
          <span class="synq-badge online">CALIBRATED</span>
        </div>
        <div style="margin: 12px 0; display:flex; flex-direction:column; gap: 8px;">
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Roll Angle Threshold</span>
            <span class="table-mono">< 5.0° (Current: 0.1°)</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Pitch Angle Threshold</span>
            <span class="table-mono">< 5.0° (Current: 0.2°)</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:11px;">
            <span style="color:var(--synq-text-muted);">Center of Mass Index</span>
            <span class="table-mono" style="color:var(--synq-status-online);">Optimal (Low)</span>
          </div>
        </div>
        <p style="font-size: 10px; color: var(--synq-text-secondary); line-height:1.4;">
          Inertial measurement unit continuously samples center of gravity during pallet elevations.
        </p>
      </div>
    </div>

    <!-- Safety Incident Log -->
    <div class="synq-table-wrap">
      <div style="padding: 10px 14px; background: var(--synq-bg-elevated); border-bottom: 1px solid var(--synq-border-default); font-size: 11px; font-weight: 700;">
        Recent Safety Watchdog Triggers & Auto-Clears
      </div>
      <table class="synq-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>AMR Unit</th>
            <th>Trigger Type</th>
            <th>Action Taken</th>
            <th>Deceleration Time</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="table-mono">00:09:42</td>
            <td class="table-mono">synq-amr-01</td>
            <td>LiDAR Slowdown Perimeter Breach (0.95m)</td>
            <td>Speed reduced to 0.30 m/s</td>
            <td class="table-mono">110 ms</td>
            <td><span class="synq-badge online">AUTO-CLEARED</span></td>
          </tr>
          <tr>
            <td class="table-mono">00:04:12</td>
            <td class="table-mono">synq-amr-03</td>
            <td>Optical Top-Dead-Center Limit Warning</td>
            <td>Actuator elevation paused</td>
            <td class="table-mono">20 ms</td>
            <td><span class="synq-badge online">RESOLVED</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  `;
}

/* ==========================================================================
   9. SETTINGS & GATEWAY CONFIGURATION VIEW
   ========================================================================== */
function renderSettingsView() {
  const container = document.getElementById('settingsViewContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="view-header-strip">
      <div class="view-title-group">
        <span class="view-title">System Settings & Gateway Configuration</span>
        <span class="synq-badge active"><span class="synq-badge-dot radar-ping"></span>CONFIGURATION ACTIVE</span>
      </div>
      <button class="synq-btn" onclick="playHapticClick('high'); saveSettingsForm();" style="background: var(--synq-status-active); color: #fff;">
        <span>Save & Apply Settings</span>
      </button>
    </div>

    <div class="synq-grid-2">
      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 12px;">
          ROS 2 & Middleware Gateway
        </div>
        <div style="display:flex; flex-direction:column; gap: 10px;">
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">ROS_DOMAIN_ID</label>
            <input type="number" class="select-input" value="42" style="width: 100%; margin-top: 4px;">
          </div>
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">VDA 5050 MQTT Broker Endpoint</label>
            <input type="text" class="select-input" value="mqtt://127.0.0.1:1883" style="width: 100%; margin-top: 4px;">
          </div>
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">DDS Implementation</label>
            <input type="text" class="select-input" value="Eclipse CycloneDDS (rmw_cyclonedds_cpp)" style="width: 100%; margin-top: 4px;" readonly>
          </div>
        </div>
      </div>

      <div class="synq-card spotlight-card" style="padding: 16px;">
        <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 12px;">
          CBS Coordinator & Kinematic Parameters
        </div>
        <div style="display:flex; flex-direction:column; gap: 10px;">
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">Max Fleet Velocity Cap</label>
            <input type="text" class="select-input" value="1.50 m/s" style="width: 100%; margin-top: 4px;">
          </div>
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">Spatial Safety Margin Radius</label>
            <input type="text" class="select-input" value="0.75 meters" style="width: 100%; margin-top: 4px;">
          </div>
          <div>
            <label style="font-size: 10px; color: var(--synq-text-muted); font-weight:700; text-transform:uppercase;">CBS Constraint Tree Depth Limit</label>
            <input type="number" class="select-input" value="64" style="width: 100%; margin-top: 4px;">
          </div>
        </div>
      </div>
    </div>
  `;
}

function saveSettingsForm() {
  showToast("System settings applied successfully. Gateway parameters re-broadcasted.");
  logEvent("Admin", "Gateway and CBS kinematic configuration updated.");
}

/* ==========================================================================
   11. OPERATE COMMAND CENTER COCKPIT CONTROLLERS & TIMELINE ENGINE
   Matches Screenshot 2 (Operate Command Center) & Technical Cockpit UX
   ========================================================================== */

let activeInspectorTab = 'state';
let timelinePlaying = true;
let timelineSpeed = 1;
let timelineInterval = null;
let simulatedClockOffsetMs = 0;

function setInspectorTab(tab) {
  activeInspectorTab = tab;
  ['tabState', 'tabSensors', 'tabMission', 'tabDiag'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.classList.remove('active');
  });
  const activeBtn = document.getElementById(tab === 'state' ? 'tabState' : tab === 'sensors' ? 'tabSensors' : tab === 'mission' ? 'tabMission' : 'tabDiag');
  if (activeBtn) activeBtn.classList.add('active');
  renderInspectorState();
}

function selectRobot(robotId) {
  window.selectedRobotId = robotId;
  if (window.synqStore) {
    window.synqStore.updateSystem({ selectedRobotId: robotId });
  }

  const selectEl = document.getElementById('canvasRobotSelect');
  if (selectEl) selectEl.value = robotId;

  const shortName = robotId.toUpperCase().replace('SYNQ-', '');
  const feedTitle = document.getElementById('camFeedTitle');
  if (feedTitle) feedTitle.textContent = `Camera Feed ${shortName}`;

  const inspTitle = document.getElementById('inspectorBotTitle');
  if (inspTitle) inspTitle.textContent = `Robot Inspector ${shortName}`;

  renderInspectorState();
  renderCockpitFleet();
  render2DMinimap();

  if (window.twin3D && window.twin3D.followSelected) {
    const bot = window.synqStore ? window.synqStore.amrs[robotId] : null;
    if (bot && window.twin3D.controls) {
      window.twin3D.controls.target.set(bot.x, 0, bot.y);
    }
  }
}
window.selectRobot = selectRobot;

function renderInspectorState() {
  const container = document.getElementById('inspectorContent');
  if (!container) return;

  const rawBots = window.synqStore ? window.synqStore.amrs : (window.ROBOTS || {});
  const botId = window.selectedRobotId || 'synq-amr-01';
  const bot = rawBots[botId] || rawBots['synq-amr-01'] || {
    id: botId,
    status: 'Navigating',
    x: 4.82,
    y: 7.15,
    heading: 84,
    speed: 1.18,
    battery: 64,
    payload: 'Pallet P-104',
    mission: 'MSN-1042'
  };

  const badge = document.getElementById('inspectorBotBadge');
  if (badge) {
    const isNav = bot.status === 'Navigating';
    badge.className = `synq-badge ${isNav ? 'online' : bot.status === 'Charging' ? 'warning' : 'neutral'}`;
    badge.textContent = bot.status.toUpperCase();
  }

  const batColor = bot.battery > 50 ? '#3fb950' : bot.battery > 20 ? '#d29922' : '#f85149';

  if (activeInspectorTab === 'state') {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">World Pose</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">X: ${Number(bot.x).toFixed(2)}m, Y: ${Number(bot.y).toFixed(2)}m</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Orientation (θ)</span>
          <span style="font-family:var(--synq-font-mono); color:#38bdf8;">${Math.round(bot.heading || 0)}° heading</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Linear Velocity</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">${Number(bot.speed || 0.0).toFixed(2)} m/s (Cap: 1.50)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Battery SoC</span>
          <div style="display:flex; align-items:center; gap:6px;">
            <div style="width:40px; height:6px; background:#1e2633; border-radius:3px; overflow:hidden;">
              <div style="width:${Math.round(bot.battery)}%; height:100%; background:${batColor};"></div>
            </div>
            <span style="font-family:var(--synq-font-mono); color:${batColor}; font-weight:700;">${Math.round(bot.battery)}%</span>
          </div>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Payload Carrier</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">${bot.payload || 'SCISSOR_LIFT'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Safety Clearance</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">3.2m (CLEAR)</span>
        </div>
      </div>
    `;
  } else if (activeInspectorTab === 'sensors') {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">LiDAR Ouster OS1-128</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">10.2 Hz (NOMINAL)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Depth RealSense D455</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">29.8 fps (LOCKED)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">IMU 6-DOF (BNO085)</span>
          <span style="font-family:var(--synq-font-mono); color:#38bdf8;">200 Hz (CALIBRATED)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Wheel Encoders (4x)</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">50 Hz (SYNCED)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Ultrasonic Bumper</span>
          <span style="font-family:var(--synq-font-mono); color:#8c96a5;">4 Channels Armed</span>
        </div>
      </div>
    `;
  } else if (activeInspectorTab === 'mission') {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Active Mission ID</span>
          <span style="font-family:var(--synq-font-mono); color:#38bdf8; font-weight:700;">${bot.mission || 'MSN-1042'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Current Waypoint</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">${bot.currentNode || 'N_1_2'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Target Destination</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">${bot.destination || 'Rack Bay B'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Route Progress</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">72% (Step 3/4)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Estimated Remaining</span>
          <span style="font-family:var(--synq-font-mono); color:#d29922;">01:24 remaining</span>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">ROS 2 Node</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">/${bot.id}/nav2_mppi</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">EKF Covariance</span>
          <span style="font-family:var(--synq-font-mono); color:#f0f3f6;">0.014 m² (CONVERGED)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Comm Ping / DDS</span>
          <span style="font-family:var(--synq-font-mono); color:#3fb950;">4 ms (CycloneDDS)</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:3px;">
          <span style="color:#8c96a5;">Motor Thermals</span>
          <span style="font-family:var(--synq-font-mono); color:#8c96a5;">FL:38° FR:39° RL:37° RR:40°</span>
        </div>
      </div>
    `;
  }
}

function renderCockpitFleet() {
  const container = document.getElementById('cockpitFleetList');
  if (!container) return;

  const rawBots = window.synqStore ? window.synqStore.amrs : (window.ROBOTS || {});
  const bots = Object.values(rawBots);
  const selId = window.selectedRobotId || 'synq-amr-01';

  let html = `
    <table class="cockpit-table">
      <thead>
        <tr>
          <th>AMR</th>
          <th>Status</th>
          <th>Battery</th>
          <th>Node</th>
          <th>Task</th>
        </tr>
      </thead>
      <tbody>
  `;

  bots.forEach(bot => {
    const isSel = (bot.id === selId);
    const shortId = bot.id.toUpperCase().replace('SYNQ-', '');
    const isNav = (bot.status === 'Navigating');
    const isChg = (bot.status === 'Charging');
    const badgeCls = isNav ? 'online' : isChg ? 'warning' : 'neutral';
    const statusText = isNav ? 'ACTIVE' : isChg ? 'CHARGING' : 'IDLE';
    const batColor = bot.battery > 50 ? '#3fb950' : bot.battery > 20 ? '#d29922' : '#f85149';

    html += `
      <tr onclick="selectRobot('${bot.id}')" style="cursor:pointer; ${isSel ? 'background:rgba(56,189,248,0.12);' : ''}">
        <td style="font-weight:700; color:${isSel ? '#38bdf8' : '#f0f3f6'};">${shortId}</td>
        <td><span class="synq-badge ${badgeCls}" style="font-size:8px; padding:1px 4px;">${statusText}</span></td>
        <td>
          <div style="display:flex; align-items:center; gap:4px;">
            <div style="width:28px; height:4px; background:#1e2633; border-radius:2px; overflow:hidden;">
              <div style="width:${Math.round(bot.battery)}%; height:100%; background:${batColor};"></div>
            </div>
            <span style="color:${batColor};">${Math.round(bot.battery)}%</span>
          </div>
        </td>
        <td>${bot.currentNode || 'N_0_1'}</td>
        <td style="color:#58a6ff;">${bot.mission || '—'}</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

function renderCockpitMissions() {
  const container = document.getElementById('cockpitMissionList');
  if (!container) return;

  const missions = [
    { id: 'MSN-1042', desc: 'Pallet Relocation A-04 → B-12', bot: 'AMR-01', prog: 72, eta: '01:24', status: 'ACTIVE' },
    { id: 'MSN-1043', desc: 'Inventory Restock Bay-08', bot: 'AMR-04', prog: 44, eta: '03:10', status: 'ACTIVE' },
    { id: 'MSN-1044', desc: 'Quality Inspection C-02', bot: '—', prog: 0, eta: 'QUEUED', status: 'QUEUED' },
    { id: 'MSN-1045', desc: 'Battery Fast-Charge Cycle', bot: 'AMR-03', prog: 88, eta: '00:45', status: 'CHARGING' }
  ];

  let html = `
    <div style="display:flex; flex-direction:column; gap:5px;">
  `;

  missions.forEach(m => {
    const isAct = m.status === 'ACTIVE';
    html += `
      <div style="background:#121720; border:1px solid #1e2633; border-radius:4px; padding:5px 8px; font-size:9.5px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
          <strong style="color:#38bdf8; font-family:var(--synq-font-mono);">${m.id}</strong>
          <span style="font-size:8.5px; color:${isAct ? '#3fb950' : '#8c96a5'}; font-weight:600;">${m.eta}</span>
        </div>
        <div style="color:#c9d1d9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${m.desc}</div>
        <div style="display:flex; align-items:center; gap:6px; margin-top:4px;">
          <div style="flex:1; height:3px; background:#1e2633; border-radius:2px; overflow:hidden;">
            <div style="width:${m.prog}%; height:100%; background:#1f6feb;"></div>
          </div>
          <span style="font-size:8.5px; color:#8c96a5; font-family:var(--synq-font-mono);">${m.bot}</span>
        </div>
      </div>
    `;
  });

  html += '</div>';
  container.innerHTML = html;
}

function renderCockpitDiagLogs() {
  const container = document.getElementById('cockpitDiagLogs');
  if (!container) return;

  const logs = [
    { t: '12:28:54', tag: 'NAV2', bot: 'AMR-01', text: 'MPPI trajectory optimal: cost=0.014, v=1.18 m/s', col: '#38bdf8' },
    { t: '12:28:53', tag: 'CBS', bot: 'FLEET', text: 'Space-Time Conflict free across 5 active agent trajectories', col: '#3fb950' },
    { t: '12:28:52', tag: 'SLAM', bot: 'AMR-01', text: 'Scan matching score: 0.984 | Keyframe #412 committed', col: '#d2a8ff' },
    { t: '12:28:50', tag: 'TASK', bot: 'AMR-01', text: 'Task MSN-1042 assigned to AMR-01 via Auction Protocol', col: '#58a6ff' },
    { t: '12:28:47', tag: 'SAFETY', bot: 'AMR-02', text: 'LIDAR scan clear, dynamic obstacle threshold nominal', col: '#3fb950' },
    { t: '12:28:42', tag: 'VDA5050', bot: 'AMR-04', text: 'Ingested orderUpdate headerId: 4812, sequence: 14', col: '#e3b341' }
  ];

  let html = '';
  logs.forEach(l => {
    html += `
      <div style="padding:1px 0; border-bottom:1px solid rgba(255,255,255,0.02);">
        <span style="color:#64748b;">[${l.t}]</span>
        <span style="color:${l.col}; font-weight:700;">[${l.tag}]</span>
        <span style="color:#f0f3f6;">${l.text}</span>
      </div>
    `;
  });
  container.innerHTML = html;
}

function render2DMinimap() {
  const canvas = document.getElementById('minimapCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const rect = canvas.getBoundingClientRect();
  if (canvas.width !== rect.width || canvas.height !== rect.height) {
    canvas.width = rect.width || 300;
    canvas.height = rect.height || 140;
  }

  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Background
  ctx.fillStyle = '#07090c';
  ctx.fillRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = '#121720';
  ctx.lineWidth = 1;
  const stepX = w / 8;
  const stepY = h / 6;
  for (let x = 0; x < w; x += stepX) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y < h; y += stepY) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  // Scale map from 15m x 15m
  const pad = 12;
  const scale = Math.min((w - pad * 2) / 15.0, (h - pad * 2) / 15.0);
  const ox = (w - 15.0 * scale) / 2;
  const oy = (h - 15.0 * scale) / 2;

  // Draw Racks
  const racks = [
    { x: 2.0, y: 1.8, w: 4.5, h: 1.4 },
    { x: 8.5, y: 1.8, w: 4.5, h: 1.4 },
    { x: 2.0, y: 6.8, w: 4.5, h: 1.4 },
    { x: 8.5, y: 6.8, w: 4.5, h: 1.4 },
    { x: 2.0, y: 11.8, w: 4.5, h: 1.4 },
    { x: 8.5, y: 11.8, w: 4.5, h: 1.4 }
  ];

  ctx.fillStyle = 'rgba(210, 153, 34, 0.25)';
  ctx.strokeStyle = '#d29922';
  ctx.lineWidth = 1;
  racks.forEach(r => {
    ctx.fillRect(ox + r.x * scale, oy + r.y * scale, r.w * scale, r.h * scale);
    ctx.strokeRect(ox + r.x * scale, oy + r.y * scale, r.w * scale, r.h * scale);
  });

  // Charging Stations
  ctx.fillStyle = '#e3b341';
  ctx.beginPath();
  ctx.arc(ox + 0.5 * scale, oy + 0.5 * scale, 4, 0, Math.PI * 2);
  ctx.fill();

  // Draw 5 AMRs
  const rawBots = window.synqStore ? window.synqStore.amrs : (window.ROBOTS || {});
  const bots = Object.values(rawBots);
  const selId = window.selectedRobotId || 'synq-amr-01';

  bots.forEach(bot => {
    const bx = ox + (bot.x || 0) * scale;
    const by = oy + (bot.y || 0) * scale;
    const isSel = (bot.id === selId);

    if (isSel) {
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(bx, by, 9, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.fillStyle = isSel ? '#38bdf8' : '#1f6feb';
    ctx.beginPath();
    ctx.arc(bx, by, 5, 0, Math.PI * 2);
    ctx.fill();

    // Direction vector
    const rad = ((bot.heading || 0) * Math.PI) / 180;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx + Math.cos(rad) * 9, by + Math.sin(rad) * 9);
    ctx.stroke();
  });
}

function renderCockpitLidarPcd() {
  const canvas = document.getElementById('cockpitLidarPcdCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const rect = canvas.getBoundingClientRect();
  if (canvas.width !== rect.width || canvas.height !== rect.height) {
    canvas.width = rect.width || 150;
    canvas.height = rect.height || 85;
  }

  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#040608';
  ctx.fillRect(0, 0, w, h);

  const numPoints = 140;
  const time = Date.now() * 0.002;

  for (let i = 0; i < numPoints; i++) {
    const angle = (i / numPoints) * Math.PI * 2;
    const depth = 20 + 25 * Math.sin(angle * 3 + time) + (Math.random() * 4);
    const px = w / 2 + Math.cos(angle) * (depth * 1.2);
    const py = h / 2 + Math.sin(angle) * (depth * 0.7);

    // Rainbow depth coloring
    const hue = Math.floor((depth / 50) * 240); // 0 (red) to 240 (blue)
    ctx.fillStyle = `hsl(${hue}, 85%, 60%)`;
    ctx.fillRect(px, py, 2, 2);
  }
}

function toggleTwinLayer(key) {
  if (window.twin3D) {
    window.twin3D.toggleLayer(key);
  }
}

function toggleCanvasLayerPill(btn, key) {
  if (btn) btn.classList.toggle('active');
  toggleTwinLayer(key);
}

function promptNewMission() {
  playHapticClick('high');
  showToast("Dispatch Modal: Queuing new pallet transfer MSN-1046");
}

function focusCameraFeed() {
  const card = document.getElementById('camFeedTitle');
  if (card) {
    card.scrollIntoView({ behavior: 'smooth' });
    showToast("Camera Feeds Focused");
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

function initTimelineScrubber() {
  const clockTime = document.getElementById('headerClockTime');
  const clockDate = document.getElementById('headerClockDate');
  const timeClock = document.getElementById('timelineClockDisplay');

  function tickClocks() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const pad3 = (n) => String(n).padStart(3, '0');

    const hh = pad(now.getHours());
    const mm = pad(now.getMinutes());
    const ss = pad(now.getSeconds());
    const ms = pad3(now.getMilliseconds());

    if (clockTime) clockTime.textContent = `${hh}:${mm}:${ss}`;
    if (clockDate) {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      clockDate.textContent = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
    }
    if (timeClock) timeClock.textContent = `${hh}:${mm}:${ss}.${ms}`;
  }

  setInterval(tickClocks, 60);
  tickClocks();

  // Periodic updates for mini-map, pcd canvas, and cockpit lists
  setInterval(() => {
    render2DMinimap();
    renderCockpitLidarPcd();
    renderCockpitFleet();
  }, 100);
}

function toggleTimelinePlay() {
  timelinePlaying = !timelinePlaying;
  const btn = document.getElementById('timelinePlayPauseBtn');
  if (btn) btn.textContent = timelinePlaying ? '❚❚' : '▶';
  showToast(timelinePlaying ? 'Timeline Live Stream Resumed' : 'Timeline Playback Paused');
}

function timelineStepStart() {
  showToast('Seek to Timeline Origin: 12:00:00');
}

function timelineRewind() {
  showToast('Rewinding Timeline (-15s)');
}

function timelineFastForward() {
  const chip = document.getElementById('timelineSpeedChip');
  timelineSpeed = timelineSpeed === 1 ? 2 : timelineSpeed === 2 ? 5 : 1;
  if (chip) chip.textContent = `${timelineSpeed}x`;
  showToast(`Timeline Playback Speed: ${timelineSpeed}x`);
}

function onTimelineScrub(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const pct = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  showToast(`Seeked Timeline to ${(pct * 100).toFixed(1)}%`);
}

// Ensure initialization on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
  initTimelineScrubber();
  renderCockpitFleet();
  renderCockpitMissions();
  renderCockpitDiagLogs();
  renderInspectorState();
  render2DMinimap();
  renderCockpitLidarPcd();
});


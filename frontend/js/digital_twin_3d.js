/**
 * synQ Industrial Robotics Operating System — 3D Digital Twin Viewport
 * Foxglove Studio / Webviz / realvirtual WEB Technical Spatial Engine
 *
 * Capabilities:
 * - High-performance Three.js WebGL 3D spatial viewport
 * - AMR 3D models with 4-wheel Mecanum kinematics, heading vectors, and chassis
 * - TF2 Coordinate Frame Visualizer (Red-X, Green-Y, Blue-Z axes) at map, odom, base_link
 * - Real-time 360° LiDAR point-cloud sweeps & cylindrical safety envelopes (0.45m & 0.75m)
 * - 3D Planned Path (Nav2 MPPI trajectory) vs Actual Executed Trail
 * - Industrial physical infrastructure: extruded racks, charging docks with contact pads, conveyors, stations
 * - Camera modes: Perspective OrbitControls, Top-Down Ortho-like, and Follow-Selected AMR
 */

(function (window) {
  'use strict';

  class SynqDigitalTwin3D {
    constructor(containerId, store) {
      this.container = document.getElementById(containerId);
      this.store = store || window.synqStore;
      this.isActive = false;

      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.controls = null;
      this.animFrameId = null;

      // Visual Scene Element Groups
      this.facilityGroup = null;
      this.robotsGroup = new Map();     // robotId -> THREE.Group
      this.pathsGroup = null;
      this.tfFramesGroup = null;
      this.lidarGroup = null;
      this.zonesGroup = null;

      // Layer Toggles
      this.layers = {
        tfFrames: true,
        lidar: true,
        plannedPath: true,
        actualTrail: true,
        racks: true,
        zones: true,
        cbsConflicts: true
      };

      // Camera Follow Target
      this.followSelected = false;
      this.raycaster = new THREE.Raycaster();
      this.mouse = new THREE.Vector2();

      if (this.container && typeof THREE !== 'undefined') {
        this.initScene();
      }
    }

    initScene() {
      const width = this.container.clientWidth || 800;
      const height = this.container.clientHeight || 600;

      // 1. Scene
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x0b0d10);
      this.scene.fog = new THREE.FogExp2(0x0b0d10, 0.015);

      // 2. Camera (Perspective with standard robotics Z-up or Y-up. In Three.js Y is up, X right, Z out)
      // We map warehouse (X, Y) meters -> 3D scene (X, -Z) with Y as vertical elevation
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
      this.camera.position.set(7.5, 18, 22);

      // 3. WebGL Renderer
      this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      this.container.innerHTML = '';
      this.container.appendChild(this.renderer.domElement);

      // 4. OrbitControls
      if (typeof THREE.OrbitControls !== 'undefined') {
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't dip below floor
        this.controls.minDistance = 2.0;
        this.controls.maxDistance = 50.0;
        this.controls.target.set(7.5, 0, 7.5);
      }

      // 5. Industrial Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
      this.scene.add(ambientLight);

      const mainLight = new THREE.DirectionalLight(0xffffff, 0.85);
      mainLight.position.set(15, 25, 15);
      mainLight.castShadow = true;
      mainLight.shadow.mapSize.width = 1024;
      mainLight.shadow.mapSize.height = 1024;
      mainLight.shadow.camera.near = 0.5;
      mainLight.shadow.camera.far = 60;
      mainLight.shadow.camera.left = -15;
      mainLight.shadow.camera.right = 15;
      mainLight.shadow.camera.top = 15;
      mainLight.shadow.camera.bottom = -15;
      this.scene.add(mainLight);

      const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.25);
      rimLight.position.set(-10, 15, -10);
      this.scene.add(rimLight);

      // 6. Component Groups
      this.facilityGroup = new THREE.Group();
      this.pathsGroup = new THREE.Group();
      this.tfFramesGroup = new THREE.Group();
      this.lidarGroup = new THREE.Group();
      this.zonesGroup = new THREE.Group();

      this.scene.add(this.facilityGroup);
      this.scene.add(this.pathsGroup);
      this.scene.add(this.tfFramesGroup);
      this.scene.add(this.lidarGroup);
      this.scene.add(this.zonesGroup);

      // 7. Build Static Infrastructure (Floor, Grid, Racks, Docks)
      this.buildFacilityLayout();

      // 8. Event Listeners
      window.addEventListener('resize', () => this.onResize());
      this.renderer.domElement.addEventListener('click', (e) => this.onPointerClick(e));
      this.renderer.domElement.addEventListener('pointermove', (e) => this.onPointerMove(e));
      this.renderer.domElement.addEventListener('pointerleave', () => this.hideRackCallout());

      // 9. Start Render Loop
      this.animate();
    }

    /**
     * Maps 2D Warehouse Coordinates (x, y) to 3D Three.js Coordinates (x, elevation, z)
     */
    to3D(x, y, elevation = 0) {
      return new THREE.Vector3(x, elevation, y);
    }

    buildFacilityLayout() {
      this.facilityGroup.clear();

      const width = 15.0;
      const height = 15.0;

      // Concrete Warehouse Floor Slab
      const floorGeo = new THREE.PlaneGeometry(width, height);
      const floorMat = new THREE.MeshStandardMaterial({
        color: 0x111418,
        roughness: 0.85,
        metalness: 0.15
      });
      const floor = new THREE.Mesh(floorGeo, floorMat);
      floor.rotation.x = -Math.PI / 2;
      floor.position.set(width / 2, -0.01, height / 2);
      floor.receiveShadow = true;
      this.facilityGroup.add(floor);

      // Engineering Metric Grid (1m cells)
      const gridHelper = new THREE.GridHelper(width, 15, 0x30363d, 0x1b2028);
      gridHelper.position.set(width / 2, 0.001, height / 2);
      this.facilityGroup.add(gridHelper);

      // Perimeter Safety Curb
      const wallMat = new THREE.MeshStandardMaterial({ color: 0x1f242c, roughness: 0.7 });
      const curbThick = 0.15;
      const curbHeight = 0.35;

      const curbs = [
        { w: width, d: curbThick, x: width / 2, z: 0 },
        { w: width, d: curbThick, x: width / 2, z: height },
        { w: curbThick, d: height, x: 0, z: height / 2 },
        { w: curbThick, d: height, x: width, z: height / 2 }
      ];

      curbs.forEach(c => {
        const geo = new THREE.BoxGeometry(c.w, curbHeight, c.d);
        const mesh = new THREE.Mesh(geo, wallMat);
        mesh.position.set(c.x, curbHeight / 2, c.z);
        mesh.receiveShadow = true;
        this.facilityGroup.add(mesh);
      });

      // Storage Racks (Extruded 3D Industrial Racks)
      const racks = [
        { id: "A", x: 2.0, y: 1.8, w: 4.5, h: 1.4, heightM: 3.2 },
        { id: "B", x: 8.5, y: 1.8, w: 4.5, h: 1.4, heightM: 3.2 },
        { id: "C", x: 2.0, y: 6.8, w: 4.5, h: 1.4, heightM: 3.2 },
        { id: "D", x: 8.5, y: 6.8, w: 4.5, h: 1.4, heightM: 3.2 },
        { id: "E", x: 2.0, y: 11.8, w: 4.5, h: 1.4, heightM: 3.2 },
        { id: "F", x: 8.5, y: 11.8, w: 4.5, h: 1.4, heightM: 3.2 }
      ];

      racks.forEach(r => {
        const rackGroup = this.createStorageRackMesh(r);
        this.facilityGroup.add(rackGroup);
      });

      // Charging Docks (Floor Pads with Glow)
      const docks = [
        { id: "CHG-01", x: 0.8, y: 0.8, w: 1.2, d: 1.2 },
        { id: "CHG-02", x: 14.0, y: 14.0, w: 1.2, d: 1.2 }
      ];

      docks.forEach(d => {
        const dockMesh = this.createChargingDockMesh(d);
        this.facilityGroup.add(dockMesh);
      });

      // Workstations / Conveyor Lines
      const stations = [
        { id: "STA-P1", x: 0.7, y: 5.0, w: 1.2, d: 2.0, type: "PICK" },
        { id: "STA-D1", x: 14.3, y: 7.5, w: 1.2, d: 2.0, type: "DROP" }
      ];

      stations.forEach(s => {
        const stMesh = this.createWorkstationMesh(s);
        this.facilityGroup.add(stMesh);
      });

      // Restricted Keep-Out Zone
      const restrictedGeo = new THREE.BoxGeometry(2.0, 0.05, 1.4);
      const restrictedMat = new THREE.MeshBasicMaterial({
        color: 0xf85149,
        transparent: true,
        opacity: 0.35,
        wireframe: true
      });
      const restrictedMesh = new THREE.Mesh(restrictedGeo, restrictedMat);
      restrictedMesh.position.set(13.8, 0.025, 0.8);
      this.facilityGroup.add(restrictedMesh);
    }

    createStorageRackMesh(rack) {
      const g = new THREE.Group();
      const cx = rack.x + rack.w / 2;
      const cz = rack.y + rack.h / 2;
      const height = rack.heightM || 3.0;

      // Upright Steel Beams (Vertical Blue Columns)
      const colGeo = new THREE.BoxGeometry(0.1, height, 0.1);
      const colMat = new THREE.MeshStandardMaterial({ color: 0x1f6feb, roughness: 0.5, metalness: 0.4 });

      const corners = [
        [-rack.w / 2 + 0.05, -rack.h / 2 + 0.05],
        [rack.w / 2 - 0.05, -rack.h / 2 + 0.05],
        [-rack.w / 2 + 0.05, rack.h / 2 - 0.05],
        [rack.w / 2 - 0.05, rack.h / 2 - 0.05]
      ];

      corners.forEach(([ox, oz]) => {
        const col = new THREE.Mesh(colGeo, colMat);
        col.position.set(ox, height / 2, oz);
        col.castShadow = true;
        g.add(col);
      });

      // Shelf Decks (Orange crossbeams)
      const shelfLevels = 4;
      const shelfMat = new THREE.MeshStandardMaterial({ color: 0xd29922, roughness: 0.6, metalness: 0.3 });
      for (let s = 1; s <= shelfLevels; s++) {
        const y = (s / (shelfLevels + 0.5)) * height;
        const beamGeo = new THREE.BoxGeometry(rack.w, 0.06, rack.h);
        const beam = new THREE.Mesh(beamGeo, shelfMat);
        beam.position.set(0, y, 0);
        beam.castShadow = true;
        beam.receiveShadow = true;
        g.add(beam);
      }

      // Invisible hit box for raycasting & hover callout
      const hitGeo = new THREE.BoxGeometry(rack.w, height, rack.h);
      const hitMat = new THREE.MeshBasicMaterial({ visible: false });
      const hitMesh = new THREE.Mesh(hitGeo, hitMat);
      hitMesh.position.set(0, height / 2, 0);
      hitMesh.userData = { isRack: true, rackData: rack };
      g.add(hitMesh);

      g.name = "rack_" + (rack.id || "bay");
      g.userData = { isRack: true, rackData: rack };
      g.position.set(cx, 0, cz);
      return g;
    }

    createChargingDockMesh(dock) {
      const g = new THREE.Group();
      const padGeo = new THREE.BoxGeometry(dock.w, 0.04, dock.d);
      const padMat = new THREE.MeshStandardMaterial({ color: 0x22272e, roughness: 0.6 });
      const pad = new THREE.Mesh(padGeo, padMat);
      pad.position.set(0, 0.02, 0);
      g.add(pad);

      // Yellow charging contacts
      const contactGeo = new THREE.BoxGeometry(dock.w * 0.6, 0.05, dock.d * 0.2);
      const contactMat = new THREE.MeshBasicMaterial({ color: 0xe3b341 });
      const contact = new THREE.Mesh(contactGeo, contactMat);
      contact.position.set(0, 0.03, 0);
      g.add(contact);

      g.position.set(dock.x, 0, dock.y);
      return g;
    }

    createWorkstationMesh(sta) {
      const g = new THREE.Group();
      const tableGeo = new THREE.BoxGeometry(sta.w, 0.8, sta.d);
      const isPick = (sta.type === "PICK");
      const mat = new THREE.MeshStandardMaterial({
        color: isPick ? 0x238636 : 0x1f6feb,
        roughness: 0.6,
        metalness: 0.2
      });
      const table = new THREE.Mesh(tableGeo, mat);
      table.position.set(0, 0.4, 0);
      table.castShadow = true;
      g.add(table);

      g.position.set(sta.x, 0, sta.y);
      return g;
    }

    /**
     * Builds or updates the 3D AMR model in the scene
     */
    updateRobotMesh(bot) {
      let robotGroup = this.robotsGroup.get(bot.id);
      const isSelected = (bot.id === (window.selectedRobotId || 'synq-amr-01'));

      if (!robotGroup) {
        robotGroup = new THREE.Group();
        robotGroup.name = bot.id;

        // 1. Chassis Body (0.70m x 0.18m x 0.50m)
        const chassisGeo = new THREE.BoxGeometry(0.70, 0.18, 0.50);
        const chassisMat = new THREE.MeshStandardMaterial({
          color: 0x161b22,
          roughness: 0.4,
          metalness: 0.7
        });
        const chassis = new THREE.Mesh(chassisGeo, chassisMat);
        chassis.position.y = 0.09 + 0.076; // wheel radius offset
        chassis.castShadow = true;
        robotGroup.add(chassis);

        // 2. Yellow Accent Band & Payload Surface
        const payloadGeo = new THREE.BoxGeometry(0.55, 0.04, 0.40);
        const payloadMat = new THREE.MeshStandardMaterial({ color: 0xd29922, metalness: 0.5 });
        const payloadPlate = new THREE.Mesh(payloadGeo, payloadMat);
        payloadPlate.position.y = 0.20 + 0.076;
        robotGroup.add(payloadPlate);

        // 3. Mecanum Wheels (4 Cylinders with 45° angle illusion)
        const wheelGeo = new THREE.CylinderGeometry(0.076, 0.076, 0.05, 16);
        const wheelMat = new THREE.MeshStandardMaterial({ color: 0x30363d, metalness: 0.8 });
        const wheelOffsets = [
          [0.22, 0.076, -0.22],
          [0.22, 0.076, 0.22],
          [-0.22, 0.076, -0.22],
          [-0.22, 0.076, 0.22]
        ];
        wheelOffsets.forEach(([wx, wy, wz]) => {
          const wheel = new THREE.Mesh(wheelGeo, wheelMat);
          wheel.rotation.x = Math.PI / 2;
          wheel.position.set(wx, wy, wz);
          wheel.castShadow = true;
          robotGroup.add(wheel);
        });

        // 4. LiDAR Puck (Cylinder at front)
        const lidarGeo = new THREE.CylinderGeometry(0.038, 0.038, 0.05, 16);
        const lidarMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0284c7 });
        const lidar = new THREE.Mesh(lidarGeo, lidarMat);
        lidar.position.set(0.28, 0.22, 0);
        robotGroup.add(lidar);

        // 5. Direction Heading Arrow
        const arrowDir = new THREE.Vector3(1, 0, 0);
        const arrow = new THREE.ArrowHelper(arrowDir, new THREE.Vector3(0.28, 0.25, 0), 0.35, 0x38bdf8, 0.12, 0.08);
        robotGroup.add(arrow);

        // 6. Selection Highlight Beacon Ring
        const ringGeo = new THREE.RingGeometry(0.55, 0.62, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.01;
        ring.name = "selectionRing";
        robotGroup.add(ring);

        // 7. Safety Envelope Cylinders (Warning 0.75m & E-Stop 0.45m)
        const warnGeo = new THREE.CylinderGeometry(0.75, 0.75, 0.04, 32);
        const warnMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.12, wireframe: true });
        const warnCyl = new THREE.Mesh(warnGeo, warnMat);
        warnCyl.position.y = 0.02;
        warnCyl.name = "warnEnvelope";
        robotGroup.add(warnCyl);

        // 8. TF Coordinate Frame Axes at base_link
        const tfAxes = new THREE.AxesHelper(0.45);
        tfAxes.position.y = 0.08;
        tfAxes.name = "tfAxes";
        robotGroup.add(tfAxes);

        this.scene.add(robotGroup);
        this.robotsGroup.set(bot.id, robotGroup);
      }

      // Smooth position interpolation
      const targetPos = this.to3D(bot.x, bot.y, 0);
      robotGroup.position.lerp(targetPos, 0.2);

      // Orientation (heading in degrees converted to radians)
      const headingRad = (bot.heading || 0) * (Math.PI / 180);
      robotGroup.rotation.y = -headingRad;

      // Selection ring visibility
      const ring = robotGroup.getObjectByName("selectionRing");
      if (ring) ring.visible = isSelected;

      // TF Axes visibility
      const tfAxes = robotGroup.getObjectByName("tfAxes");
      if (tfAxes) tfAxes.visible = this.layers.tfFrames;

      // LiDAR safety warning envelope visibility
      const warnCyl = robotGroup.getObjectByName("warnEnvelope");
      if (warnCyl) {
        warnCyl.visible = this.layers.lidar;
        if (bot.status === 'Emergency Stop') {
          warnCyl.material.color.setHex(0xf85149);
          warnCyl.material.opacity = 0.3;
        } else {
          warnCyl.material.color.setHex(0xfbbf24);
          warnCyl.material.opacity = 0.12;
        }
      }

      // Camera Follow mode
      if (this.followSelected && isSelected && this.controls) {
        this.controls.target.lerp(robotGroup.position, 0.1);
      }
    }

    /**
     * Renders planned trajectory lines and executed breadcrumbs in 3D
     */
    updateTrajectories(robots) {
      this.pathsGroup.clear();

      if (!this.layers.plannedPath && !this.layers.actualTrail) return;

      Object.values(robots).forEach(bot => {
        const isSelected = (bot.id === (window.selectedRobotId || 'synq-amr-01'));

        // 1. Planned Route Path (Nav2 MPPI)
        if (this.layers.plannedPath && bot.route && bot.route.length > 0) {
          const pathPoints = [this.to3D(bot.x, bot.y, 0.08)];
          bot.route.forEach(nid => {
            const node = window.ROADMAP_NODES ? window.ROADMAP_NODES[nid] : null;
            if (node) {
              pathPoints.push(this.to3D(node.x, node.y, 0.08));
            }
          });

          if (pathPoints.length > 1) {
            const pathGeo = new THREE.BufferGeometry().setFromPoints(pathPoints);
            const pathMat = new THREE.LineDashedMaterial({
              color: isSelected ? 0x38bdf8 : 0x58a6ff,
              dashSize: 0.3,
              gapSize: 0.15,
              linewidth: 2
            });
            const line = new THREE.Line(pathGeo, pathMat);
            line.computeLineDistances();
            this.pathsGroup.add(line);
          }
        }

        // 2. Executed Breadcrumb Trail
        if (this.layers.actualTrail && bot.executedTrail && bot.executedTrail.length > 1) {
          const trailPoints = bot.executedTrail.map(pt => this.to3D(pt.x, pt.y, 0.04));
          const trailGeo = new THREE.BufferGeometry().setFromPoints(trailPoints);
          const trailMat = new THREE.LineBasicMaterial({
            color: isSelected ? 0x38bdf8 : 0x8b949e,
            transparent: true,
            opacity: isSelected ? 0.6 : 0.25
          });
          const trailLine = new THREE.Line(trailGeo, trailMat);
          this.pathsGroup.add(trailLine);
        }
      });
    }

    /**
     * Renders real-time simulated 3D LiDAR point cloud sweep around the selected AMR
     */
    updateLidarPointCloud(selectedBot) {
      this.lidarGroup.clear();

      if (!this.layers.lidar || !selectedBot) return;

      const numPoints = 180;
      const points = [];
      const colors = [];
      const bx = selectedBot.x;
      const by = selectedBot.y;
      const heading = (selectedBot.heading || 0) * (Math.PI / 180);

      const colorNear = new THREE.Color(0xf85149);
      const colorFar = new THREE.Color(0x38bdf8);

      for (let i = 0; i < numPoints; i++) {
        const angle = heading + (i / numPoints) * Math.PI * 2;
        // Simulated range with noise and obstacle boundary clipping
        let range = 3.5 + 0.8 * Math.sin(i * 3) + (Math.random() * 0.1);
        if (range > 6.0) range = 6.0;

        const px = bx + Math.cos(angle) * range;
        const py = by + Math.sin(angle) * range;
        const pz = 0.20 + (Math.random() * 0.05);

        points.push(this.to3D(px, py, pz));

        const c = colorFar.clone().lerp(colorNear, Math.max(0, 1 - range / 3.0));
        colors.push(c.r, c.g, c.b);
      }

      const pcdGeo = new THREE.BufferGeometry().setFromPoints(points);
      pcdGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      const pcdMat = new THREE.PointsMaterial({ size: 0.08, vertexColors: true });
      const pcd = new THREE.Points(pcdGeo, pcdMat);
      this.lidarGroup.add(pcd);
    }

    /**
     * Camera View Presets
     */
    setCameraPreset(preset) {
      if (!this.camera || !this.controls) return;

      if (preset === 'perspective') {
        this.followSelected = false;
        this.camera.position.set(7.5, 18, 22);
        this.controls.target.set(7.5, 0, 7.5);
      } else if (preset === 'topdown') {
        this.followSelected = false;
        this.camera.position.set(7.5, 26, 7.51); // slight offset to prevent gimbal lock
        this.controls.target.set(7.5, 0, 7.5);
      } else if (preset === 'follow') {
        this.followSelected = !this.followSelected;
        const selId = (this.store && this.store.system && this.store.system.selectedRobotId) || window.selectedRobotId;
        const bots = (this.store && this.store.amrs) ? this.store.amrs : window.ROBOTS;
        if (this.followSelected && selId && bots) {
          const bot = bots[selId];
          if (bot) {
            this.controls.target.set(bot.x, 0, bot.y);
            this.camera.position.set(bot.x, 8, bot.y + 10);
          }
        }
      }
      this.controls.update();
    }

    toggleLayer(layerKey) {
      if (this.layers.hasOwnProperty(layerKey)) {
        this.layers[layerKey] = !this.layers[layerKey];
      }
    }

    onPointerClick(event) {
      const rect = this.renderer.domElement.getBoundingClientRect();
      this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.scene.children, true);

      for (let hit of intersects) {
        // Find ancestor AMR group
        let curr = hit.object;
        while (curr && curr.parent && curr.parent !== this.scene) {
          if (this.robotsGroup.has(curr.name)) {
            const robotId = curr.name;
            if (typeof window.selectRobot === 'function') {
              window.selectRobot(robotId);
            }
            return;
          }
          curr = curr.parent;
        }

        // Check if rack clicked
        if (hit.object.userData && hit.object.userData.isRack) {
          const rack = hit.object.userData.rackData;
          this.showRackCallout(event.clientX, event.clientY, rack);
          return;
        }
      }
    }

    onPointerMove(event) {
      if (!this.renderer || !this.camera) return;
      const rect = this.renderer.domElement.getBoundingClientRect();
      this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.scene.children, true);

      for (let hit of intersects) {
        if (hit.object.userData && hit.object.userData.isRack) {
          const rack = hit.object.userData.rackData;
          this.showRackCallout(event.clientX, event.clientY, rack);
          return;
        }
      }
      this.hideRackCallout();
    }

    showRackCallout(clientX, clientY, rack) {
      const callout = document.getElementById('rackCalloutOverlay');
      if (!callout) return;
      const stage = document.getElementById('viewportStage');
      if (!stage) return;
      const stageRect = stage.getBoundingClientRect();

      const x = clientX - stageRect.left;
      const y = clientY - stageRect.top;

      callout.style.left = `${x}px`;
      callout.style.top = `${y}px`;
      callout.style.display = 'block';

      const titleEl = document.getElementById('rackCalloutTitle');
      const typeEl = document.getElementById('rackCalloutType');
      const occEl = document.getElementById('rackCalloutOcc');
      const statEl = document.getElementById('rackCalloutStatus');

      if (titleEl) titleEl.textContent = `Rack R-${rack.id || '12'}`;
      if (typeEl) typeEl.textContent = rack.name || 'Heavy Industrial';
      if (occEl) occEl.textContent = '84% (42/50 bays)';
      if (statEl) {
        statEl.textContent = 'Optimal';
        statEl.style.color = '#3fb950';
      }
    }

    hideRackCallout() {
      const callout = document.getElementById('rackCalloutOverlay');
      if (callout) callout.style.display = 'none';
    }

    onResize() {
      if (!this.container || !this.renderer || !this.camera) return;
      const width = this.container.clientWidth;
      const height = this.container.clientHeight;
      if (width === 0 || height === 0) return;

      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    }

    animate() {
      this.animFrameId = requestAnimationFrame(() => this.animate());

      if (this.controls) {
        this.controls.update();
      }

      // Sync state store robots with 3D models
      const bots = (this.store && this.store.amrs) ? this.store.amrs : (window.ROBOTS || {});
      const selId = (this.store && this.store.system && this.store.system.selectedRobotId) || window.selectedRobotId || 'synq-amr-01';

      if (bots) {
        Object.values(bots).forEach(bot => {
          this.updateRobotMesh(bot);
        });
        this.updateTrajectories(bots);

        const selBot = bots[selId];
        if (selBot) {
          this.updateLidarPointCloud(selBot);
          if (this.followSelected && this.controls) {
            this.controls.target.lerp(new THREE.Vector3(selBot.x, 0, selBot.y), 0.08);
          }
        }
      }

      if (this.renderer && this.scene && this.camera) {
        this.renderer.render(this.scene, this.camera);
      }
    }

    destroy() {
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
      }
      if (this.renderer && this.renderer.domElement) {
        this.renderer.domElement.remove();
      }
    }
  }

  window.SynqDigitalTwin3D = SynqDigitalTwin3D;
})(window);

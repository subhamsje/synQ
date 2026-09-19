/**
 * synQ Industrial Robotics Operating System — Centralized State Store
 * Phase 1: High-Performance Reactive State Architecture
 *
 * Models:
 * - AMRs: pose (x, y, theta), velocity, battery SoC/cells, status, payload, mission, safety, source
 * - Missions: id, status, priority, assignedRobot, currentStep, route, progress
 * - Warehouse: racks, stations, charging points, dynamic obstacles, restricted zones, topology graph
 * - Autonomy: candidate evaluations, decision factors, CBS conflict resolution, obstacle recovery
 */

(function (window) {
  'use strict';

  class SynqStateStore {
    constructor() {
      // 1. Core Event Bus & Subscriptions
      this.listeners = new Map();

      // 2. System Status & Simulation Clock
      this.system = {
        isEstopActive: false,
        isPaused: false,
        timeAcceleration: 1.0,
        simTimeSeconds: 0,
        sourceMode: 'HYBRID', // 'ROS2_LIVE' | 'SIMULATION' | 'HYBRID'
        ros2Connected: true,
        fastDdsDomain: 42,
        nav2RateHz: 50,
        selectedRobotId: 'synq-amr-01',
        activeTab: 'autonomy',
        layers: {
          lanes: true,
          racks: true,
          evaluations: true,
          routes: true,
          trails: true,
          conflicts: true
        }
      };

      // 3. Navigation Topology Graph (15m x 15m Hub)
      const nodes = {};
      const edges = [];
      const nodeTypes = {
        '0,0': 'CHARGE', '3,3': 'CHARGE',
        '1,0': 'PICK', '1,1': 'PICK', '1,2': 'PICK', '1,3': 'PICK',
        '2,0': 'DROP', '2,1': 'DROP', '2,2': 'DROP', '2,3': 'DROP'
      };

      for (let r = 0; r < 4; r++) {
        for (let c = 0; c < 4; c++) {
          const id = `N_${r}_${c}`;
          nodes[id] = {
            id: id,
            r: r,
            c: c,
            x: c * 5.0,
            y: r * 5.0,
            node_type: nodeTypes[`${r},${c}`] || 'TRANSIT'
          };
          if (c < 3) edges.push({ u: id, v: `N_${r}_${c + 1}`, distance: 5.0, max_speed: 1.5 });
          if (r < 3) edges.push({ u: id, v: `N_${r + 1}_${c}`, distance: 5.0, max_speed: 1.5 });
        }
      }

      // 4. Warehouse Physical Layout & Digital Twin Grounding
      this.warehouse = {
        width: 15.0,
        height: 15.0,
        widthMeters: 15.0,
        heightMeters: 15.0,
        navigationGraph: { nodes, edges },
        racks: [
          { id: "A", x: 2.0, y: 1.8, w: 4.5, h: 1.4, name: "Rack Bay A (Pallets)", label: "Rack Bay A" },
          { id: "B", x: 8.5, y: 1.8, w: 4.5, h: 1.4, name: "Rack Bay B (Overstock)", label: "Rack Bay B" },
          { id: "C", x: 2.0, y: 6.8, w: 4.5, h: 1.4, name: "Rack Bay C (Fast Pick)", label: "Rack Bay C" },
          { id: "D", x: 8.5, y: 6.8, w: 4.5, h: 1.4, name: "Rack Bay D (Cartons)", label: "Rack Bay D" },
          { id: "E", x: 2.0, y: 11.8, w: 4.5, h: 1.4, name: "Rack Bay E (ASRS Infeed)", label: "Rack Bay E" },
          { id: "F", x: 8.5, y: 11.8, w: 4.5, h: 1.4, name: "Rack Bay F (Staging)", label: "Rack Bay F" }
        ],
        zones: [
          { id: "PICK-1", type: "PICK", x: 0.0, y: 4.0, w: 1.8, h: 2.0, label: "Inbound P1" },
          { id: "PICK-2", type: "PICK", x: 0.0, y: 9.0, w: 1.8, h: 2.0, label: "Inbound P2" },
          { id: "DROP-1", type: "DROP", x: 13.2, y: 4.0, w: 1.8, h: 2.0, label: "Outbound D1" },
          { id: "DROP-2", type: "DROP", x: 13.2, y: 9.0, w: 1.8, h: 2.0, label: "Outbound D2" },
          { id: "CHG-1", type: "CHARGE", x: 0.2, y: 0.2, w: 1.6, h: 1.6, label: "Fast Charger C1" },
          { id: "CHG-2", type: "CHARGE", x: 13.2, y: 13.2, w: 1.6, h: 1.6, label: "Fast Charger C2" }
        ],
        restrictedZones: [
          { id: "ZONE-RESTRICTED-01", x: 13.0, y: 0.2, w: 1.8, h: 1.8, label: "High Voltage Enclosure", reason: "NFPA 70E Arc Flash Boundary" }
        ],
        obstacles: []
      };

      // 5. Typed AMR Fleet State
      this.amrs = {
        'synq-amr-01': {
          id: 'synq-amr-01',
          name: 'AMR Unit 01',
          serial: 'SN-SYNQ-2026-001',
          status: 'Idle',
          pose: { x: 0.0, y: 0.0, theta: 0 },
          x: 0.0,
          y: 0.0,
          renderX: 0.0,
          renderY: 0.0,
          heading: 0,
          velocity: { linear: 0.0, angular: 0.0, speed: 0.0 },
          speed: 0.0,
          battery: 94.5,
          cells: [4.14, 4.13, 4.14, 4.13],
          temperatureC: 28.4,
          payload: 'SCISSOR_LIFT',
          payloadPosition: 0.0,
          payloadCurrentA: 0.2,
          mission: '—',
          missionId: null,
          pickup: '—',
          destination: '—',
          eta: '—',
          currentNode: 'N_0_0',
          targetNode: null,
          route: [],
          executedTrail: [],
          isSimulated: true,
          safetyState: {
            eStopEngaged: false,
            lidarWarningZone: false,
            lidarStopZone: false,
            watchdogOk: true,
            clearanceMeters: 2.8,
            interlocksHealthy: true
          },
          rosNode: '/synq_amr_01/lifecycle_amr (ACTIVE)',
          ekfCovariance: '0.012 m² (CONVERGED)',
          lastHeartbeat: Date.now()
        },
        'synq-amr-02': {
          id: 'synq-amr-02',
          name: 'AMR Unit 02',
          serial: 'SN-SYNQ-2026-002',
          status: 'Idle',
          pose: { x: 15.0, y: 15.0, theta: 180 },
          x: 15.0,
          y: 15.0,
          renderX: 15.0,
          renderY: 15.0,
          heading: 180,
          velocity: { linear: 0.0, angular: 0.0, speed: 0.0 },
          speed: 0.0,
          battery: 88.0,
          cells: [4.02, 4.01, 4.03, 4.02],
          temperatureC: 31.0,
          payload: 'ROLLER_CONVEYOR',
          payloadPosition: 0.0,
          payloadCurrentA: 0.0,
          mission: '—',
          missionId: null,
          pickup: '—',
          destination: '—',
          eta: '—',
          currentNode: 'N_3_3',
          targetNode: null,
          route: [],
          executedTrail: [],
          isSimulated: true,
          safetyState: {
            eStopEngaged: false,
            lidarWarningZone: false,
            lidarStopZone: false,
            watchdogOk: true,
            clearanceMeters: 3.5,
            interlocksHealthy: true
          },
          rosNode: '/synq_amr_02/lifecycle_amr (ACTIVE)',
          ekfCovariance: '0.018 m² (CONVERGED)',
          lastHeartbeat: Date.now()
        },
        'synq-amr-03': {
          id: 'synq-amr-03',
          name: 'AMR Unit 03',
          serial: 'SN-SYNQ-2026-003',
          status: 'Idle',
          pose: { x: 15.0, y: 0.0, theta: 90 },
          x: 15.0,
          y: 0.0,
          renderX: 15.0,
          renderY: 0.0,
          heading: 90,
          velocity: { linear: 0.0, angular: 0.0, speed: 0.0 },
          speed: 0.0,
          battery: 91.2,
          cells: [4.10, 4.09, 4.10, 4.09],
          temperatureC: 27.6,
          payload: 'TOTE_GRIPPER',
          payloadPosition: 0.0,
          payloadCurrentA: 0.1,
          mission: '—',
          missionId: null,
          pickup: '—',
          destination: '—',
          eta: '—',
          currentNode: 'N_0_3',
          targetNode: null,
          route: [],
          executedTrail: [],
          isSimulated: true,
          safetyState: {
            eStopEngaged: false,
            lidarWarningZone: false,
            lidarStopZone: false,
            watchdogOk: true,
            clearanceMeters: 3.1,
            interlocksHealthy: true
          },
          rosNode: '/synq_amr_03/lifecycle_amr (ACTIVE)',
          ekfCovariance: '0.011 m² (CONVERGED)',
          lastHeartbeat: Date.now()
        }
      };

      // 6. Mission Management State
      this.missions = [
        {
          id: 'TASK-4821',
          status: 'ASSIGNED',
          priority: 1,
          assignedRobot: 'synq-amr-01',
          currentStep: 'Transit to Pick Station N_1_1',
          route: ['N_0_0', 'N_0_1', 'N_1_1'],
          progress: 42,
          pickNode: 'N_1_1',
          dropNode: 'N_2_2',
          payloadRequired: 'SCISSOR_LIFT',
          startedAt: Date.now() - 34000,
          slaDeadline: Date.now() + 180000
        }
      ];

      // 7. Autonomy & Decision Reasoning State ("Why FLTX Made This Decision")
      this.autonomy = {
        currentStage: 'EXECUTION',
        latestTask: {
          orderId: 'TASK-4821',
          pickup: 'N_1_1 (Rack Bay B)',
          destination: 'N_2_2 (Packing Station D2)',
          payloadRequired: 'SCISSOR_LIFT',
          priority: 1,
          weightKg: 240
        },
        latestDecision: {
          selectedRobot: 'synq-amr-01',
          rationale: 'Assigned synq-amr-01: Optimal composite cost score (5.0) with matching SCISSOR_LIFT payload and 94.5% battery reserve.',
          decisionFactors: {
            weightDistance: 0.40,
            weightBattery: 0.20,
            weightPayloadMatch: 0.40
          },
          candidates: [
            {
              id: 'synq-amr-01',
              payload: 'SCISSOR_LIFT',
              match: true,
              dist: 5.0,
              battery: 94.5,
              costScore: 5.0,
              outcome: 'SELECTED',
              reason: 'Optimal transit distance with physical payload match'
            },
            {
              id: 'synq-amr-02',
              payload: 'ROLLER_CONVEYOR',
              match: false,
              dist: 15.0,
              battery: 88.0,
              costScore: 15.0,
              outcome: 'REJECTED',
              reason: 'Payload mismatch: Equipped with Conveyor, requires Scissor Lift'
            },
            {
              id: 'synq-amr-03',
              payload: 'TOTE_GRIPPER',
              match: false,
              dist: 18.2,
              battery: 91.2,
              costScore: 18.2,
              outcome: 'REJECTED',
              reason: 'Payload mismatch: Equipped with Gripper; higher travel distance'
            }
          ]
        },
        cbsConflicts: [
          {
            conflictId: 'CONF-01',
            type: 'VERTEX_CONFLICT',
            locationNode: 'N_0_1',
            timeStep: 1.0,
            robotsInvolved: ['synq-amr-01', 'synq-amr-03'],
            description: 'Vertex collision at intersection N_0_1 at t=1.0s between synq-amr-01 and synq-amr-03'
          }
        ],
        cbsBranches: [
          {
            branch: 'Branch A (Constrain synq-amr-01)',
            action: 'Delay synq-amr-01 by 1 time-step at N_0_0',
            costDelta: '+2.0s',
            outcome: 'REJECTED (Higher fleet mission delay)'
          },
          {
            branch: 'Branch B (Constrain synq-amr-03)',
            action: 'Route synq-amr-03 via bypass corridor N_1_2',
            costDelta: '+1.0s',
            outcome: 'SELECTED (Minimal sum-of-costs delta; zero headway loss)'
          }
        ],
        selectedResolution: {
          chosenBranch: 'Branch B',
          whyChosen: 'Branch B chosen: Lower sum-of-costs delta (+1.0s vs +2.0s). synq-amr-03 yields corridor while high-priority task on synq-amr-01 proceeds uninterrupted.',
          routes: {
            'synq-amr-01': ['N_0_0', 'N_0_1', 'N_0_2'],
            'synq-amr-03': ['N_0_3', 'N_1_2', 'N_1_1', 'N_0_1']
          }
        },
        obstacleRecovery: {
          active: false,
          location: null,
          steps: [
            { step: 'Detection', detail: '360° LiDAR threshold breach at range 0.65m (< 1.0m warning field)' },
            { step: 'Risk Assessment', detail: 'Active velocity vector intersects physical obstacle in 1.2s' },
            { step: 'Action', detail: 'Commanded velocity zeroed (SAFETY_SLOWDOWN -> SAFETY_ESTOP)' },
            { step: 'Recovery', detail: 'Costmap clearance service invoked -> SmacPlanner2D local grid replan' },
            { step: 'Verification', detail: 'Zero footprint overlap verified along bypass route -> Mission resumed' }
          ]
        }
      };

      // 8. Event Log Activity History
      this.activities = [
        { id: 'evt-1', time: '10:41:02', source: 'FLTX Core', msg: 'System initialized. 3 AMRs registered on FastDDS Domain 42.' },
        { id: 'evt-2', time: '10:41:15', source: 'CBS Engine', msg: 'Space-time roadmap graph compiled. 16 nodes, 24 edges ready.' },
        { id: 'evt-3', time: '10:41:20', source: 'Dispatch', msg: 'Dispatched order TASK-4821 to synq-amr-01.' }
      ];

      // Auto-bind aliases for backward compatibility
      this._bindAliases();
    }

    /* ------------------------------------------------------------- */
    /* REACTIVE SUBSCRIPTIONS & EVENT BUS                            */
    /* ------------------------------------------------------------- */

    subscribe(event, callback) {
      if (!this.listeners.has(event)) {
        this.listeners.set(event, new Set());
      }
      this.listeners.get(event).add(callback);
      return () => {
        if (this.listeners.has(event)) {
          this.listeners.get(event).delete(callback);
        }
      };
    }

    notify(event, payload) {
      if (this.listeners.has(event)) {
        this.listeners.get(event).forEach(cb => {
          try {
            cb(payload);
          } catch (err) {
            console.error(`[SynqStateStore] Error in listener for ${event}:`, err);
          }
        });
      }
      // Also notify wildcards
      if (this.listeners.has('*')) {
        this.listeners.get('*').forEach(cb => {
          try {
            cb({ event, payload });
          } catch (err) {}
        });
      }
    }

    /* ------------------------------------------------------------- */
    /* BACKWARD COMPATIBILITY BRIDGE                                 */
    /* ------------------------------------------------------------- */

    _bindAliases() {
      window.ROBOTS = this.amrs;
      window.WAREHOUSE = this.warehouse;
      window.ROADMAP_NODES = this.warehouse.navigationGraph.nodes;
      window.ROADMAP_EDGES = this.warehouse.navigationGraph.edges;
      window.AUTONOMY_REASONING = this.autonomy;
      window.ACTIVITIES = this.activities;
    }

    /* ------------------------------------------------------------- */
    /* MUTATIONS & AUTONOMY ACTIONS                                  */
    /* ------------------------------------------------------------- */

    selectRobot(robotId) {
      if (this.amrs[robotId]) {
        this.system.selectedRobotId = robotId;
        window.selectedRobotId = robotId;
        this.notify('amr_selected', this.amrs[robotId]);
        this.notify('state_changed', { type: 'select_robot', robotId });
      }
    }

    getSelectedAMR() {
      return this.amrs[this.system.selectedRobotId] || Object.values(this.amrs)[0] || null;
    }

    spawnAMR(id, payloadType = 'SCISSOR_LIFT', initialNode = 'N_3_0') {
      if (!id) {
        const count = Object.keys(this.amrs).length + 1;
        id = `synq-amr-${String(count).padStart(2, '0')}`;
      }

      if (this.amrs[id]) {
        console.warn(`[SynqStateStore] Robot ${id} already exists`);
        return this.amrs[id];
      }

      const node = this.warehouse.navigationGraph.nodes[initialNode] || { x: 5.0, y: 15.0 };
      const newBot = {
        id: id,
        name: `AMR Unit ${id.split('-').pop()}`,
        serial: `SN-SYNQ-2026-0${Object.keys(this.amrs).length + 1}`,
        status: 'Idle',
        pose: { x: node.x, y: node.y, theta: 0 },
        x: node.x,
        y: node.y,
        renderX: node.x,
        renderY: node.y,
        heading: 0,
        velocity: { linear: 0.0, angular: 0.0, speed: 0.0 },
        speed: 0.0,
        battery: 100.0,
        cells: [4.20, 4.19, 4.20, 4.19],
        temperatureC: 25.0,
        payload: payloadType,
        payloadPosition: 0.0,
        payloadCurrentA: 0.0,
        mission: '—',
        missionId: null,
        pickup: '—',
        destination: '—',
        eta: '—',
        currentNode: initialNode,
        targetNode: null,
        route: [],
        executedTrail: [],
        isSimulated: true,
        safetyState: {
          eStopEngaged: false,
          lidarWarningZone: false,
          lidarStopZone: false,
          watchdogOk: true,
          clearanceMeters: 4.0,
          interlocksHealthy: true
        },
        rosNode: `/${id.replace(/-/g, '_')}/lifecycle_amr (ACTIVE)`,
        ekfCovariance: '0.010 m² (CONVERGED)',
        lastHeartbeat: Date.now()
      };

      this.amrs[id] = newBot;
      this.logActivity('Fleet Manager', `Dynamic AMR spawned: ${id} [${payloadType}] at node ${initialNode}`);
      this.notify('amr_spawned', newBot);
      this.notify('fleet_changed', this.amrs);
      return newBot;
    }

    removeAMR(id) {
      if (!this.amrs[id]) return false;
      const bot = this.amrs[id];
      delete this.amrs[id];
      if (this.system.selectedRobotId === id) {
        this.system.selectedRobotId = Object.keys(this.amrs)[0] || null;
        window.selectedRobotId = this.system.selectedRobotId;
      }
      this.logActivity('Fleet Manager', `AMR decommissioned from active topology: ${id}`);
      this.notify('amr_removed', { id });
      this.notify('fleet_changed', this.amrs);
      return true;
    }

    injectObstacle(x, y, radius = 0.85, label = 'Dynamic Pallet') {
      const obstacle = {
        id: `OBS-${Date.now() % 10000}`,
        x: Math.round(x * 100) / 100,
        y: Math.round(y * 100) / 100,
        radius: radius,
        label: label,
        createdTime: Date.now()
      };

      this.warehouse.obstacles.push(obstacle);
      this.logActivity('Safety LiDAR', `Unmapped obstacle injected at (${obstacle.x}m, ${obstacle.y}m)`);

      this.autonomy.obstacleRecovery.active = true;
      this.autonomy.obstacleRecovery.location = { x: obstacle.x, y: obstacle.y };
      this.autonomy.currentStage = 'RECOVERY';

      Object.values(this.amrs).forEach(bot => {
        if (bot.status === 'Navigating') {
          const dist = Math.hypot(bot.x - obstacle.x, bot.y - obstacle.y);
          if (dist < 2.5) {
            bot.safetyState.lidarWarningZone = true;
            if (dist < 1.2) {
              bot.safetyState.lidarStopZone = true;
              bot.speed = 0.0;
              this.logActivity(bot.id, `Emergency obstacle stop: LiDAR breach at ${dist.toFixed(2)}m`);
            }
          }
        }
      });

      this.notify('obstacle_added', obstacle);
      this.notify('autonomy_updated', this.autonomy);
      return obstacle;
    }

    clearObstacles() {
      this.warehouse.obstacles = [];
      this.autonomy.obstacleRecovery.active = false;
      this.autonomy.obstacleRecovery.location = null;
      Object.values(this.amrs).forEach(bot => {
        bot.safetyState.lidarWarningZone = false;
        bot.safetyState.lidarStopZone = false;
      });
      this.logActivity('Safety LiDAR', 'All dynamic obstacles cleared from local costmap');
      this.notify('obstacles_cleared', {});
    }

    simulateCBSCrossing() {
      const bot1 = this.amrs['synq-amr-01'];
      const bot3 = this.amrs['synq-amr-03'];

      if (!bot1 || !bot3) {
        console.warn('[SynqStateStore] Requires synq-amr-01 and synq-amr-03 for crossing test');
        return;
      }

      this.logActivity('CBS Engine', 'INITIATING CBS HEAD-ON SCENARIO: AMRs 01 & 03 in corridor N_0_0 <-> N_0_3');

      bot1.status = 'Navigating';
      bot1.x = 0.0;
      bot1.y = 0.0;
      bot1.renderX = 0.0;
      bot1.renderY = 0.0;
      bot1.heading = 0;
      bot1.route = ['N_0_1', 'N_0_2'];
      bot1.mission = 'TASK-4821';
      bot1.destination = 'Drop D2';

      bot3.status = 'Navigating';
      bot3.x = 15.0;
      bot3.y = 0.0;
      bot3.renderX = 15.0;
      bot3.renderY = 0.0;
      bot3.heading = 180;
      bot3.route = ['N_0_2', 'N_0_1', 'N_0_0'];
      bot3.mission = 'TASK-9104';
      bot3.destination = 'Infeed P1';

      this.autonomy.currentStage = 'CONFLICT';
      this.notify('autonomy_updated', this.autonomy);

      setTimeout(() => {
        this.logActivity('CBS Engine', 'CBS Conflict Detected at N_0_1! Evaluating Constraint Tree...');
        this.autonomy.cbsConflicts = [
          {
            conflictId: 'CONF-HEADON',
            type: 'VERTEX_CONFLICT',
            locationNode: 'N_0_1',
            timeStep: 1.0,
            robotsInvolved: ['synq-amr-01', 'synq-amr-03'],
            description: 'Vertex collision at intersection N_0_1 at t=1.0s between synq-amr-01 and synq-amr-03'
          }
        ];
        this.notify('autonomy_updated', this.autonomy);

        setTimeout(() => {
          this.logActivity('CBS Engine', 'Branch B Chosen: Route synq-amr-03 via bypass corridor [N_0_2 -> N_1_2 -> N_1_1 -> N_0_1]');
          if (this.amrs['synq-amr-03']) {
            this.amrs['synq-amr-03'].route = ['N_0_2', 'N_1_2', 'N_1_1', 'N_0_1'];
          }
          this.autonomy.currentStage = 'ROUTE';
          this.notify('autonomy_updated', this.autonomy);

          setTimeout(() => {
            this.autonomy.currentStage = 'EXECUTION';
            this.notify('autonomy_updated', this.autonomy);
          }, 1000);
        }, 1200);
      }, 1200);
    }

    togglePauseSimulation() {
      this.system.isPaused = !this.system.isPaused;
      this.logActivity('Simulation', this.system.isPaused ? 'Simulation clock PAUSED' : 'Simulation clock RESUMED');
      this.notify('pause_changed', this.system.isPaused);
      return this.system.isPaused;
    }

    resetSimulation() {
      this.clearObstacles();
      this.system.isPaused = false;
      this.system.isEstopActive = false;

      if (this.amrs['synq-amr-01']) {
        const b = this.amrs['synq-amr-01'];
        b.status = 'Idle';
        b.x = 0.0;
        b.y = 0.0;
        b.renderX = 0.0;
        b.renderY = 0.0;
        b.heading = 0;
        b.speed = 0.0;
        b.route = [];
        b.mission = '—';
        b.destination = '—';
        b.battery = 94.5;
        b.executedTrail = [];
      }

      if (this.amrs['synq-amr-02']) {
        const b = this.amrs['synq-amr-02'];
        b.status = 'Idle';
        b.x = 15.0;
        b.y = 15.0;
        b.renderX = 15.0;
        b.renderY = 15.0;
        b.heading = 180;
        b.speed = 0.0;
        b.route = [];
        b.mission = '—';
        b.destination = '—';
        b.battery = 88.0;
        b.executedTrail = [];
      }

      if (this.amrs['synq-amr-03']) {
        const b = this.amrs['synq-amr-03'];
        b.status = 'Idle';
        b.x = 15.0;
        b.y = 0.0;
        b.renderX = 15.0;
        b.renderY = 0.0;
        b.heading = 90;
        b.speed = 0.0;
        b.route = [];
        b.mission = '—';
        b.destination = '—';
        b.battery = 91.2;
        b.executedTrail = [];
      }

      this.autonomy.currentStage = 'TASK';
      this.logActivity('Simulation', 'Facility digital-twin state reset to pristine baseline');
      this.notify('simulation_reset', {});
    }

    toggleGlobalEstop() {
      this.system.isEstopActive = !this.system.isEstopActive;
      const isEstop = this.system.isEstopActive;
      window.isEstopActive = isEstop;

      Object.values(this.amrs).forEach(b => {
        b.safetyState.eStopEngaged = isEstop;
        if (isEstop) {
          b.status = 'Emergency Stop';
          b.speed = 0.0;
          b.velocity.speed = 0.0;
          b.route = [];
        } else {
          b.status = 'Idle';
        }
      });

      this.logActivity('Safety Bus', isEstop ? 'GLOBAL EMERGENCY STOP ENGAGED (ALL DRIVES KINEMATICALLY TRIPPED)' : 'Emergency stop reset. Drives armed in Standby.');
      this.notify('estop_changed', isEstop);
      return isEstop;
    }

    dispatchMission(order) {
      const { pickup, payloadRequired, destination } = order;

      let candidate = Object.values(this.amrs).find(b => b.status !== 'Emergency Stop' && b.payload === payloadRequired);
      if (!candidate) candidate = Object.values(this.amrs)[0];

      if (!candidate) {
        console.error('[SynqStateStore] No AMRs available for dispatch');
        return null;
      }

      const orderId = `TASK-${Math.floor(1000 + Math.random() * 9000)}`;
      const route = [pickup, destination];

      candidate.status = 'Navigating';
      candidate.mission = orderId;
      candidate.missionId = orderId;
      candidate.pickup = pickup;
      candidate.destination = destination;
      candidate.eta = '12s';
      candidate.route = [...route];
      candidate.targetNode = destination;

      this.autonomy.latestTask = {
        orderId: orderId,
        pickup: pickup,
        destination: destination,
        payloadRequired: payloadRequired,
        priority: 1
      };

      this.autonomy.latestDecision = {
        selectedRobot: candidate.id,
        rationale: `Assigned ${candidate.id}: Payload ${payloadRequired} matched with lowest travel cost.`,
        candidates: Object.values(this.amrs).map(b => ({
          id: b.id,
          payload: b.payload,
          match: b.payload === payloadRequired,
          dist: Math.round(Math.hypot(b.x - 5.0, b.y - 5.0) * 10) / 10,
          battery: b.battery,
          costScore: b.id === candidate.id ? 5.0 : 15.0,
          outcome: b.id === candidate.id ? 'SELECTED' : 'REJECTED',
          reason: b.id === candidate.id ? 'Optimal match' : (b.payload !== payloadRequired ? 'Payload mismatch' : 'Higher transit cost')
        }))
      };

      this.autonomy.currentStage = 'EXECUTION';
      this.logActivity('Dispatch', `Order ${orderId} dispatched to ${candidate.id} (${pickup} -> ${destination})`);

      this.notify('mission_dispatched', { orderId, robotId: candidate.id });
      this.notify('autonomy_updated', this.autonomy);
      return orderId;
    }

    stepTick(deltaSeconds = 0.05) {
      if (this.system.isPaused) return;

      this.system.simTimeSeconds += deltaSeconds;

      Object.values(this.amrs).forEach(bot => {
        if (bot.status === 'Navigating' && bot.route && bot.route.length > 0) {
          if (bot.safetyState.lidarStopZone) {
            bot.speed = 0.0;
            return;
          }

          const targetId = bot.route[0];
          const node = this.warehouse.navigationGraph.nodes[targetId];
          if (node) {
            const dx = node.x - bot.x;
            const dy = node.y - bot.y;
            const dist = Math.hypot(dx, dy);

            if (!bot.executedTrail) bot.executedTrail = [];
            const lastTrail = bot.executedTrail[bot.executedTrail.length - 1];
            if (!lastTrail || Math.hypot(lastTrail.x - bot.x, lastTrail.y - bot.y) > 0.4) {
              bot.executedTrail.push({ x: bot.x, y: bot.y, t: Date.now() });
              if (bot.executedTrail.length > 30) bot.executedTrail.shift();
            }

            if (dist < 0.15) {
              bot.x = node.x;
              bot.y = node.y;
              bot.currentNode = targetId;
              bot.route.shift();

              if (bot.route.length === 0) {
                bot.status = 'Idle';
                bot.mission = '—';
                bot.missionId = null;
                bot.pickup = '—';
                bot.destination = '—';
                bot.eta = '—';
                bot.speed = 0.0;
                bot.targetNode = null;
                this.logActivity(bot.id, `Arrived at destination (${targetId}). Task complete.`);
                this.autonomy.currentStage = 'VERIFIED';
                this.notify('autonomy_updated', this.autonomy);
              }
            } else {
              bot.speed = 0.85;
              bot.velocity.speed = 0.85;
              const step = Math.min(dist, 0.06 * (this.system.timeAcceleration || 1.0));
              bot.x += (dx / dist) * step;
              bot.y += (dy / dist) * step;
              bot.heading = Math.atan2(dy, dx) * 180 / Math.PI;
              bot.pose.x = bot.x;
              bot.pose.y = bot.y;
              bot.pose.theta = bot.heading;
            }
          }
        }
      });

      this.notify('simulation_tick', { simTime: this.system.simTimeSeconds });
    }

    ingestTelemetry(data) {
      if (!data) return;

      if (data.fleet && Array.isArray(data.fleet)) {
        data.fleet.forEach(remoteBot => {
          const local = this.amrs[remoteBot.robot_id];
          if (local) {
            local.battery = remoteBot.battery_pct !== undefined ? remoteBot.battery_pct : local.battery;
            if (remoteBot.is_busy) {
              local.status = 'Navigating';
              local.missionId = remoteBot.current_mission_id || local.missionId;
            }
            if (remoteBot.trajectory && remoteBot.trajectory.length > 0 && local.route.length === 0) {
              local.route = [...remoteBot.trajectory];
            }
          }
        });
      }

      if (data.recent_events && Array.isArray(data.recent_events)) {
        data.recent_events.forEach(evt => {
          const exists = this.activities.some(a => a.msg === evt.message);
          if (!exists) {
            this.logActivity(evt.source, evt.message);
          }
        });
      }
    }

    logActivity(source, msg) {
      const now = new Date();
      const timeStr = now.toTimeString().split(' ')[0];
      const entry = {
        id: `evt-${Date.now() % 100000}`,
        time: timeStr,
        source: source || 'FLTX',
        msg: msg
      };
      this.activities.unshift(entry);
      if (this.activities.length > 50) this.activities.pop();
      this.notify('activity_logged', entry);
    }
  }

  // Attach to window
  window.SynqStateStore = SynqStateStore;
  window.synqStore = new SynqStateStore();

})(window);

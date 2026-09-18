import heapq
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set, Any

from fms.topology.warehouse_graph import WarehouseGraph


class ConflictType(Enum):
    VERTEX = 1
    EDGE = 2


@dataclass
class Conflict:
    agent_1: str
    agent_2: str
    conflict_type: ConflictType
    time_step: int
    node: Optional[str] = None
    edge: Optional[Tuple[str, str]] = None


@dataclass
class AgentPlan:
    agent_id: str
    start_node: str
    goal_node: str
    path: List[str] = field(default_factory=list)


@dataclass(order=True)
class CTNode:
    cost: int
    constraints: Dict[str, Set[Tuple]] = field(compare=False)
    paths: Dict[str, List[str]] = field(compare=False)


class CBSRouter:
    """
    Conflict-Based Search (CBS) Multi-Agent Pathfinding (MAPF) Router
    for Warehouse AMRs. Guarantees conflict-free, deadlock-free trajectories.
    """

    def __init__(self, graph: WarehouseGraph, max_time_horizon: int = 60):
        self.graph = graph
        self.max_time_horizon = max_time_horizon

    def space_time_a_star(
        self,
        agent_id: str,
        start_node: str,
        goal_node: str,
        constraints: Set[Tuple]
    ) -> Optional[List[str]]:
        """
        Low-level Space-Time A* search with vertex and edge constraints.
        constraints format:
          ('VERTEX', node_id, t)
          ('EDGE', u, v, t)
        """
        # Priority queue entry: (f, g, current_node, t, path)
        h_start = self._heuristic(start_node, goal_node)
        open_set = [(h_start, 0, start_node, 0, [start_node])]
        visited: Set[Tuple[str, int]] = set()

        while open_set:
            f, g, u, t, path = heapq.heappop(open_set)

            if u == goal_node:
                # Goal reached! Check if any future constraints prevent staying at goal
                stay_blocked = any(
                    ('VERTEX', goal_node, t_future) in constraints
                    for t_future in range(t + 1, min(t + 5, self.max_time_horizon))
                )
                if not stay_blocked:
                    return path

            if t >= self.max_time_horizon:
                continue

            state_key = (u, t)
            if state_key in visited:
                continue
            visited.add(state_key)

            # Generate neighbors: moves + wait action
            actions = [(u, 1.0)] + [(v, 1.0) for v, _ in self.graph.get_neighbors(u)]

            for v, _ in actions:
                next_t = t + 1

                # Check vertex constraint at next_t
                if ('VERTEX', v, next_t) in constraints:
                    continue

                # Check edge constraint from u -> v at t
                if u != v and ('EDGE', u, v, t) in constraints:
                    continue

                if (v, next_t) not in visited:
                    next_g = g + 1
                    next_h = self._heuristic(v, goal_node)
                    heapq.heappush(
                        open_set,
                        (next_g + next_h, next_g, v, next_t, path + [v])
                    )

        return None

    def plan(self, agents: List[AgentPlan]) -> Optional[Dict[str, List[str]]]:
        """
        High-level Conflict-Based Search.
        Takes a list of AgentPlans with start and goal nodes,
        returns conflict-free trajectories for each agent.
        """
        # Root CT node
        root_constraints: Dict[str, Set[Tuple]] = {a.agent_id: set() for a in agents}
        root_paths: Dict[str, List[str]] = {}

        for a in agents:
            path = self.space_time_a_star(a.agent_id, a.start_node, a.goal_node, root_constraints[a.agent_id])
            if path is None:
                return None  # Unreachable
            root_paths[a.agent_id] = path

        root_cost = sum(len(p) for p in root_paths.values())
        open_tree = [CTNode(cost=root_cost, constraints=root_constraints, paths=root_paths)]

        iterations = 0
        max_iterations = 200

        while open_tree and iterations < max_iterations:
            iterations += 1
            curr_node: CTNode = heapq.heappop(open_tree)

            conflict = self._find_first_conflict(curr_node.paths)
            if conflict is None:
                # No conflicts: found optimal conflict-free solution!
                return curr_node.paths

            # Branch on the conflict
            for agent_id in [conflict.agent_1, conflict.agent_2]:
                new_constraints = {
                    aid: set(cons) for aid, cons in curr_node.constraints.items()
                }

                if conflict.conflict_type == ConflictType.VERTEX:
                    new_constraints[agent_id].add(('VERTEX', conflict.node, conflict.time_step))
                elif conflict.conflict_type == ConflictType.EDGE:
                    u, v = conflict.edge
                    if agent_id == conflict.agent_1:
                        new_constraints[agent_id].add(('EDGE', u, v, conflict.time_step))
                    else:
                        new_constraints[agent_id].add(('EDGE', v, u, conflict.time_step))

                # Replan for this agent
                agent_obj = next(a for a in agents if a.agent_id == agent_id)
                new_path = self.space_time_a_star(
                    agent_id,
                    agent_obj.start_node,
                    agent_obj.goal_node,
                    new_constraints[agent_id]
                )

                if new_path is not None:
                    new_paths = dict(curr_node.paths)
                    new_paths[agent_id] = new_path
                    new_cost = sum(len(p) for p in new_paths.values())
                    heapq.heappush(
                        open_tree,
                        CTNode(cost=new_cost, constraints=new_constraints, paths=new_paths)
                    )

        return None

    def plan_with_trace(self, agents: List[AgentPlan]) -> Tuple[Optional[Dict[str, List[str]]], Dict[str, Any]]:
        """
        High-level Conflict-Based Search with full decision tree tracing.
        Exposes conflicts detected, candidate branches evaluated, and resolution rationale.
        """
        trace = {
            "initial_unconstrained_paths": {},
            "conflicts_detected": [],
            "branches_explored": [],
            "resolved": False,
            "resolution_summary": "Zero initial conflicts detected. Paths are collision-free."
        }

        root_constraints: Dict[str, Set[Tuple]] = {a.agent_id: set() for a in agents}
        root_paths: Dict[str, List[str]] = {}

        for a in agents:
            path = self.space_time_a_star(a.agent_id, a.start_node, a.goal_node, root_constraints[a.agent_id])
            if path is None:
                trace["resolution_summary"] = f"Agent {a.agent_id} could not find a path to {a.goal_node}."
                return None, trace
            root_paths[a.agent_id] = path

        trace["initial_unconstrained_paths"] = {k: list(v) for k, v in root_paths.items()}
        root_cost = sum(len(p) for p in root_paths.values())
        open_tree = [CTNode(cost=root_cost, constraints=root_constraints, paths=root_paths)]

        iterations = 0
        max_iterations = 200

        while open_tree and iterations < max_iterations:
            iterations += 1
            curr_node: CTNode = heapq.heappop(open_tree)

            conflict = self._find_first_conflict(curr_node.paths)
            if conflict is None:
                trace["resolved"] = True
                if trace["conflicts_detected"]:
                    trace["resolution_summary"] = (
                        f"Resolved {len(trace['conflicts_detected'])} conflict(s) by branching constraint tree. "
                        f"Final trajectories deconflict with minimal sum-of-costs delta."
                    )
                return curr_node.paths, trace

            conflict_info = {
                "iteration": iterations,
                "agent_1": conflict.agent_1,
                "agent_2": conflict.agent_2,
                "conflict_type": conflict.conflict_type.name,
                "time_step": conflict.time_step,
                "location": conflict.node if conflict.conflict_type == ConflictType.VERTEX else f"{conflict.edge[0]} <-> {conflict.edge[1]}"
            }
            trace["conflicts_detected"].append(conflict_info)

            # Branch on the conflict
            branch_records = []
            for agent_id in [conflict.agent_1, conflict.agent_2]:
                new_constraints = {
                    aid: set(cons) for aid, cons in curr_node.constraints.items()
                }

                if conflict.conflict_type == ConflictType.VERTEX:
                    new_constraints[agent_id].add(('VERTEX', conflict.node, conflict.time_step))
                elif conflict.conflict_type == ConflictType.EDGE:
                    u, v = conflict.edge
                    if agent_id == conflict.agent_1:
                        new_constraints[agent_id].add(('EDGE', u, v, conflict.time_step))
                    else:
                        new_constraints[agent_id].add(('EDGE', v, u, conflict.time_step))

                agent_obj = next(a for a in agents if a.agent_id == agent_id)
                new_path = self.space_time_a_star(
                    agent_id,
                    agent_obj.start_node,
                    agent_obj.goal_node,
                    new_constraints[agent_id]
                )

                if new_path is not None:
                    new_paths = dict(curr_node.paths)
                    new_paths[agent_id] = new_path
                    new_cost = sum(len(p) for p in new_paths.values())
                    branch_cost_delta = new_cost - root_cost

                    branch_rec = {
                        "constrained_agent": agent_id,
                        "constraint": f"Cannot occupy {conflict_info['location']} at t={conflict.time_step}",
                        "resulting_path": new_path,
                        "cost_delta": branch_cost_delta
                    }
                    branch_records.append(branch_rec)

                    heapq.heappush(
                        open_tree,
                        CTNode(cost=new_cost, constraints=new_constraints, paths=new_paths)
                    )
            
            trace["branches_explored"].append({
                "conflict": conflict_info,
                "branches": branch_records
            })

        trace["resolution_summary"] = "CBS exceeded maximum iterations without convergence."
        return None, trace


    def _find_first_conflict(self, paths: Dict[str, List[str]]) -> Optional[Conflict]:
        """Detects the earliest vertex or edge conflict between any two agents."""
        agent_ids = list(paths.keys())
        max_len = max(len(p) for p in paths.values())

        for t in range(max_len):
            # 1. Vertex Conflicts
            occupied: Dict[str, str] = {}  # node -> agent_id
            for aid in agent_ids:
                node = paths[aid][min(t, len(paths[aid]) - 1)]
                if node in occupied:
                    return Conflict(
                        agent_1=occupied[node],
                        agent_2=aid,
                        conflict_type=ConflictType.VERTEX,
                        time_step=t,
                        node=node
                    )
                occupied[node] = aid

            # 2. Edge Conflicts (swap between t and t+1)
            if t + 1 < max_len:
                for i in range(len(agent_ids)):
                    for j in range(i + 1, len(agent_ids)):
                        a1, a2 = agent_ids[i], agent_ids[j]
                        p1, p2 = paths[a1], paths[a2]

                        u1 = p1[min(t, len(p1) - 1)]
                        v1 = p1[min(t + 1, len(p1) - 1)]

                        u2 = p2[min(t, len(p2) - 1)]
                        v2 = p2[min(t + 1, len(p2) - 1)]

                        # If a1 moved u1 -> v1 and a2 moved v1 -> u1 simultaneously
                        if u1 == v2 and v1 == u2 and u1 != v1:
                            return Conflict(
                                agent_1=a1,
                                agent_2=a2,
                                conflict_type=ConflictType.EDGE,
                                time_step=t,
                                edge=(u1, v1)
                            )

        return None

    def _heuristic(self, u: str, goal: str) -> int:
        n1 = self.graph.nodes[u]
        n2 = self.graph.nodes[goal]
        dist = math.hypot(n2.x - n1.x, n2.y - n1.y)
        # Assuming nominal grid step of 5.0m
        return int(math.ceil(dist / 5.0))

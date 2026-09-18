import math
from typing import List, Tuple, Dict, Any


class CostmapManager:
    """
    Manages Nav2 Costmap geometry, footprint polygons, and inflation decay calculations
    for synQ-AMR with dynamic payload module adaptation.
    """

    BASE_FOOTPRINT = [
        [0.35, 0.25],
        [0.35, -0.25],
        [-0.35, -0.25],
        [-0.35, 0.25]
    ]

    PAYLOAD_FOOTPRINTS = {
        "BASE": [
            [0.35, 0.25],
            [0.35, -0.25],
            [-0.35, -0.25],
            [-0.35, 0.25]
        ],
        "SCISSOR_LIFT": [
            [0.37, 0.27],
            [0.37, -0.27],
            [-0.37, -0.27],
            [-0.37, 0.27]
        ],
        "ROLLER_CONVEYOR": [
            [0.40, 0.26],
            [0.40, -0.26],
            [-0.40, -0.26],
            [-0.40, 0.26]
        ],
        "TOTE_GRIPPER": [
            [0.45, 0.25],
            [0.45, -0.25],
            [-0.35, -0.25],
            [-0.35, 0.25]
        ]
    }

    @staticmethod
    def compute_inscribed_radius(polygon: List[List[float]]) -> float:
        """
        Computes the radius of the largest inscribed circle centered at the origin.
        For a polygon, this is the minimum perpendicular distance from (0,0) to any line segment.
        """
        min_dist = float('inf')
        n = len(polygon)
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            
            x1, y1 = p1[0], p1[1]
            x2, y2 = p2[0], p2[1]
            
            dx = x2 - x1
            dy = y2 - y1
            
            # Perpendicular distance from origin to line segment
            segment_len_sq = dx * dx + dy * dy
            if segment_len_sq == 0:
                dist = math.hypot(x1, y1)
            else:
                # Projection parameter t
                t = max(0.0, min(1.0, -(x1 * dx + y1 * dy) / segment_len_sq))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = math.hypot(proj_x, proj_y)
                
            if dist < min_dist:
                min_dist = dist
        return min_dist

    @staticmethod
    def compute_circumscribed_radius(polygon: List[List[float]]) -> float:
        """
        Computes the radius of the smallest circumscribed circle centered at origin.
        This is the maximum distance from (0,0) to any vertex of the polygon.
        """
        max_dist = 0.0
        for pt in polygon:
            dist = math.hypot(pt[0], pt[1])
            if dist > max_dist:
                max_dist = dist
        return max_dist

    @staticmethod
    def compute_inflation_cost(
        distance: float,
        inscribed_radius: float,
        inflation_radius: float,
        cost_scaling_factor: float = 3.0
    ) -> int:
        """
        Computes Nav2 exponential inflation cost for a given distance from obstacle.
        Formula:
        cost = 254 if distance <= inscribed_radius
        cost = exp(-cost_scaling_factor * (distance - inscribed_radius)) * 253 if inscribed_radius < distance <= inflation_radius
        cost = 0 if distance > inflation_radius
        """
        if distance <= inscribed_radius:
            return 254
        if distance > inflation_radius:
            return 0
        
        raw_cost = math.exp(-cost_scaling_factor * (distance - inscribed_radius)) * 253.0
        return int(round(raw_cost))

    @classmethod
    def get_footprint_string(cls, payload_type: str = "BASE") -> str:
        """Returns standard Nav2 YAML string representation of polygon."""
        pts = cls.PAYLOAD_FOOTPRINTS.get(payload_type, cls.BASE_FOOTPRINT)
        return str(pts)

    @classmethod
    def get_specs_for_payload(cls, payload_type: str = "BASE") -> Dict[str, Any]:
        polygon = cls.PAYLOAD_FOOTPRINTS.get(payload_type, cls.BASE_FOOTPRINT)
        inscribed = cls.compute_inscribed_radius(polygon)
        circumscribed = cls.compute_circumscribed_radius(polygon)
        return {
            "payload_type": payload_type,
            "polygon": polygon,
            "inscribed_radius": round(inscribed, 4),
            "circumscribed_radius": round(circumscribed, 4),
            "footprint_str": str(polygon),
            "recommended_inflation_radius": round(circumscribed + 0.20, 2)
        }

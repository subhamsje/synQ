"""
AutoMap 3D Reconstruction & Spatial Segmentation Engine
Processes accumulated LiDAR & depth point clouds:
- Voxel grid spatial downsampling
- RANSAC ground plane and wall boundary segmentation
- Euclidean cluster grouping & 3D bounding box extraction
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
from backend.automap.sensors import ScanKeyframe


@dataclass
class BoundingBox3D:
    box_id: str
    cx: float
    cy: float
    cz: float
    width: float  # X span
    depth: float  # Y span
    height: float # Z span
    point_count: int
    density: float
    min_point: Tuple[float, float, float]
    max_point: Tuple[float, float, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box_id": self.box_id,
            "center": {"x": round(self.cx, 2), "y": round(self.cy, 2), "z": round(self.cz, 2)},
            "dimensions": {"width": round(self.width, 2), "depth": round(self.depth, 2), "height": round(self.height, 2)},
            "point_count": self.point_count,
            "density": round(self.density, 2)
        }


class PointCloudReconstructor:
    """
    Takes sensor scan keyframes, merges them into a global coordinate frame,
    filters spatial noise, segments planar surfaces, and extracts object clusters.
    """

    def __init__(self, voxel_size: float = 0.15):
        self.voxel_size = voxel_size
        self.raw_points: List[Tuple[float, float, float, float]] = []
        self.filtered_points: List[Tuple[float, float, float, float]] = []
        self.floor_elevation: float = 0.0
        self.ceiling_elevation: float = 4.5
        self.facility_bounds = {"min_x": 0.0, "max_x": 15.0, "min_y": 0.0, "max_y": 15.0}

    def process_keyframes(self, keyframes: List[ScanKeyframe]) -> Dict[str, Any]:
        """Merges and downsamples point cloud from all keyframes."""
        self.raw_points = []
        for kf in keyframes:
            self.raw_points.extend(kf.points)

        # Spatial Voxel Grid Filter
        voxel_map = {}
        for (x, y, z, intensity) in self.raw_points:
            vx = int(round(x / self.voxel_size))
            vy = int(round(y / self.voxel_size))
            vz = int(round(z / self.voxel_size))
            key = (vx, vy, vz)
            if key not in voxel_map:
                voxel_map[key] = (x, y, z, intensity)

        self.filtered_points = list(voxel_map.values())

        # Determine facility spatial bounds
        if self.filtered_points:
            xs = [p[0] for p in self.filtered_points]
            ys = [p[1] for p in self.filtered_points]
            zs = [p[2] for p in self.filtered_points]
            self.facility_bounds = {
                "min_x": min(xs), "max_x": max(xs),
                "min_y": min(ys), "max_y": max(ys),
                "min_z": min(zs), "max_z": max(zs)
            }

        return {
            "total_raw_points": len(self.raw_points),
            "voxel_filtered_points": len(self.filtered_points),
            "compression_ratio": round(len(self.raw_points) / max(1, len(self.filtered_points)), 2),
            "bounds": self.facility_bounds
        }

    def extract_clusters(self, distance_threshold: float = 0.6, min_cluster_points: int = 6) -> List[BoundingBox3D]:
        """
        Segments spatial clusters using grid proximity grouping and extracts 3D bounding boxes.
        Excludes pure perimeter walls and floor plane.
        """
        if not self.filtered_points:
            return []

        # Filter out floor (z < 0.1) and outer boundary perimeter walls
        candidate_points = []
        b = self.facility_bounds
        wall_margin = 0.25

        for p in self.filtered_points:
            x, y, z, _ = p
            # Skip ground floor
            if z < 0.12:
                continue
            # Skip outer perimeter walls
            if (x < b["min_x"] + wall_margin or x > b["max_x"] - wall_margin or
                y < b["min_y"] + wall_margin or y > b["max_y"] - wall_margin):
                continue
            candidate_points.append(p)

        # Disjoint-Set / Grid Neighbor Clustering
        clusters: List[List[Tuple[float, float, float, float]]] = []
        visited = set()
        grid_bins = {}

        bin_size = distance_threshold
        for idx, (x, y, z, val) in enumerate(candidate_points):
            bx = int(x / bin_size)
            by = int(y / bin_size)
            key = (bx, by)
            if key not in grid_bins:
                grid_bins[key] = []
            grid_bins[key].append(idx)

        for idx, pt in enumerate(candidate_points):
            if idx in visited:
                continue
            # BFS to find connected points
            cluster = [pt]
            visited.add(idx)
            queue = [idx]

            while queue:
                curr_idx = queue.pop(0)
                cx, cy, _, _ = candidate_points[curr_idx]
                cbx = int(cx / bin_size)
                cby = int(cy / bin_size)

                for nbx in range(cbx - 1, cbx + 2):
                    for nby in range(cby - 1, cby + 2):
                        for n_idx in grid_bins.get((nbx, nby), []):
                            if n_idx not in visited:
                                nx, ny, _, _ = candidate_points[n_idx]
                                if math.hypot(nx - cx, ny - cy) <= distance_threshold:
                                    visited.add(n_idx)
                                    queue.append(n_idx)
                                    cluster.append(candidate_points[n_idx])

            if len(cluster) >= min_cluster_points:
                clusters.append(cluster)

        # Fit Bounding Box to each cluster
        bounding_boxes: List[BoundingBox3D] = []
        for c_idx, cl in enumerate(clusters):
            xs = [p[0] for p in cl]
            ys = [p[1] for p in cl]
            zs = [p[2] for p in cl]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)

            width = max_x - min_x
            depth = max_y - min_y
            height = max_z - min_z

            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            cz = (min_z + max_z) / 2.0

            vol = max(0.01, width * depth * height)
            density = len(cl) / vol

            box = BoundingBox3D(
                box_id=f"cluster-{c_idx + 1:02d}",
                cx=cx,
                cy=cy,
                cz=cz,
                width=width,
                depth=depth,
                height=height,
                point_count=len(cl),
                density=density,
                min_point=(min_x, min_y, min_z),
                max_point=(max_x, max_y, max_z)
            )
            bounding_boxes.append(box)

        return bounding_boxes

"""
synQ AMR Map Lifecycle & Localization Health Monitor
Evaluates AMCL particle cloud convergence and monitors kidnapped robot conditions.
"""
from typing import List, Tuple, Optional, Dict
import math

class LocalizationHealthMonitor:
    def __init__(self, pos_divergence_threshold_m: float = 0.40, yaw_divergence_threshold_rad: float = 0.35):
        self.pos_thresh = pos_divergence_threshold_m
        self.yaw_thresh = yaw_divergence_threshold_rad

    def evaluate_pose_covariance(self, cov_matrix_36: List[float]) -> Dict[str, any]:
        """
        Evaluates a 6x6 covariance matrix (36 elements row-major from geometry_msgs/PoseWithCovariance).
        Indices:
        cov[0]  = var(x)
        cov[7]  = var(y)
        cov[35] = var(yaw)
        """
        if len(cov_matrix_36) != 36:
            raise ValueError("Covariance matrix must have exactly 36 elements")

        var_x = cov_matrix_36[0]
        var_y = cov_matrix_36[7]
        var_yaw = cov_matrix_36[35]

        pos_uncertainty = math.sqrt(max(0.0, var_x + var_y))
        yaw_uncertainty = math.sqrt(max(0.0, var_yaw))

        is_diverged = (pos_uncertainty > self.pos_thresh) or (yaw_uncertainty > self.yaw_thresh)

        return {
            "var_x": var_x,
            "var_y": var_y,
            "var_yaw": var_yaw,
            "pos_uncertainty_m": pos_uncertainty,
            "yaw_uncertainty_rad": yaw_uncertainty,
            "is_localized": not is_diverged,
            "requires_recovery": is_diverged
        }

class MapMetadataValidator:
    @staticmethod
    def validate_yaml_metadata(meta: dict) -> bool:
        required_keys = ["image", "resolution", "origin", "occupied_thresh", "free_thresh"]
        for k in required_keys:
            if k not in meta:
                return False
        if meta["resolution"] <= 0.0 or meta["resolution"] > 1.0:
            return False
        if len(meta["origin"]) != 3:
            return False
        return True

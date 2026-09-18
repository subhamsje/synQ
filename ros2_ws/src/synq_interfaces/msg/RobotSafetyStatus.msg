std_msgs/Header header
uint8 SAFETY_NORMAL=0
uint8 SAFETY_SLOWDOWN=1
uint8 SAFETY_ESTOP=2

uint8 safety_state
bool lidar_blindzone_active
bool imu_tilt_warning
bool localization_lost
float32 min_obstacle_distance

from glob import glob
import os
from setuptools import setup

package_name = 'autonomous_ground_robot'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ros2-sysmlv2 bridge',
    maintainer_email='generated@ros2-sysmlv2.dev',
    description='Auto-generated from SysML v2 model: AutonomousGroundRobot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lidar_driver = autonomous_ground_robot.lidar_driver_node:main',
            'imu_driver = autonomous_ground_robot.imu_driver_node:main',
            'camera_driver = autonomous_ground_robot.camera_driver_node:main',
            'obstacle_detector = autonomous_ground_robot.obstacle_detector_node:main',
            'e_k_f_localizer = autonomous_ground_robot.e_k_f_localizer_node:main',
            'path_planner = autonomous_ground_robot.path_planner_node:main',
            'trajectory_tracker = autonomous_ground_robot.trajectory_tracker_node:main',
            'a_g_r_velocity_smoother = autonomous_ground_robot.a_g_r_velocity_smoother_node:main',
            'collision_guard = autonomous_ground_robot.collision_guard_node:main',
            'static_map_server = autonomous_ground_robot.static_map_server_node:main',
            'mission_coordinator = autonomous_ground_robot.mission_coordinator_node:main',
            'conformance_monitor = autonomous_ground_robot.conformance_monitor:main',
            'activate_nodes = autonomous_ground_robot.activate_nodes:main',
        ],
    },
)

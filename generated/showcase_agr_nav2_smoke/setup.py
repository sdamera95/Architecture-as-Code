from glob import glob
import os
from setuptools import setup

package_name = 'ground_robot_with_nav2'

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
    description='Auto-generated from SysML v2 model: GroundRobotWithNav2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'nav2_lidar_driver = ground_robot_with_nav2.nav2_lidar_driver_node:main',
            'depth_camera_driver = ground_robot_with_nav2.depth_camera_driver_node:main',
            'nav2_imu_driver = ground_robot_with_nav2.nav2_imu_driver_node:main',
            'point_cloud_filter = ground_robot_with_nav2.point_cloud_filter_node:main',
            'nav2_e_k_f_localizer = ground_robot_with_nav2.nav2_e_k_f_localizer_node:main',
            'conformance_monitor = ground_robot_with_nav2.conformance_monitor:main',
            'activate_nodes = ground_robot_with_nav2.activate_nodes:main',
        ],
    },
)

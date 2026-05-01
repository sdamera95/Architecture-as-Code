from glob import glob
import os
from setuptools import setup

package_name = 'test_robot'

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
    description='Auto-generated from SysML v2 model: TestRobot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'my_lidar_driver = test_robot.my_lidar_driver_node:main',
            'my_controller = test_robot.my_controller_node:main',
            'conformance_monitor = test_robot.conformance_monitor:main',
            'activate_nodes = test_robot.activate_nodes:main',
        ],
    },
)

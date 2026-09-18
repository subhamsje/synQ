from setuptools import find_packages, setup

package_name = 'synq_sensors'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Team synQ',
    maintainer_email='subhamsagar282006@gmail.com',
    description='Sensor processing and health watchdog nodes for synQ-AMR',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lidar_processor = synq_sensors.lidar_processor:main',
            'imu_processor = synq_sensors.imu_processor:main',
        ],
    },
)

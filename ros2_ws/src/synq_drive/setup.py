from setuptools import find_packages, setup

package_name = 'synq_drive'

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
    description='synQ AMR Mecanum Kinematics Solver and Odometry Node',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mecanum_controller = synq_drive.mecanum_controller_node:main',
        ],
    },
)

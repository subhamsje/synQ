from setuptools import setup

package_name = 'synq_vda5050'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Team synQ',
    maintainer_email='subhamsagar282006@gmail.com',
    description='VDA 5050 v2.0.0 MQTT bridge for synQ-AMR',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vda5050_adapter = synq_vda5050.vda5050_adapter:main',
        ],
    },
)

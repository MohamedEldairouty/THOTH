from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'simulate_robot_pkg'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'maps'),
            glob('maps/*')),
        (os.path.join('share', package_name, 'urdf'),
            glob(os.path.join('urdf', '*.urdf'))),
        (os.path.join('share', package_name, 'rviz'),
            glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='saged',
    maintainer_email='sagedelsawy@gmail.com',
    description='THOTH museum tour guide robot simulation package',
    license='MIT',
    entry_points={
        'console_scripts': [
            'exhibit_markers = simulate_robot_pkg.exhibit_markers_node:main',
            'llm_narration   = simulate_robot_pkg.llm_narration_node:main',
        ],
    },
)

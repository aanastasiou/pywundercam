from distutils.core import setup

setup(
    name='pywundercam',
    version='0.1',
    author='Athanasios Anastasiou',
    author_email='athanastasiou@gmail.com',
    packages=['pywundercam'],
    scripts=[],
    url='http://www.github.com/',
    license='LICENSE.txt',
    description='PyWunderCam is a Python interface to Wunder360 S1 panoramic cameras',
    long_description=open('README.txt').read(),
    install_requires=[
        "Django >= 1.1.1",
        "caldav == 0.1.4",
    ],
)

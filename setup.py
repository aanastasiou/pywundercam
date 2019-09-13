import sys

from setuptools import setup, find_packages

setup(
    name="pywundercam",
    version="0.0.1",
    description="Python interface to the Wunder 360 S1 panoramic camera.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Athanasios Anastasiou",
    author_email="athanastasiou@gmail.com",
    zip_safe=True,
    url="",
    license="License :: OSI Approved :: Apache Software License",
    packages=find_packages(exclude=("test", "test.*")),
    keywords="image camera panoramic 360",
    install_requires=['requests', 'pillow'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics :: Capture :: Digital Camera",
    ])

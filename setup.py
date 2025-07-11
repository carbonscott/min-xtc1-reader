#!/usr/bin/env python3
"""
Setup script for xtc1reader - Minimal LCLS1 XTC file reader.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Minimal LCLS1 XTC file reader"

setup(
    name="xtc1reader",
    version="0.1.0",
    description="Minimal LCLS1 XTC file reader",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="LCLS Data Analysis Team",
    author_email="",
    url="https://github.com/carbonscott/min-xtc1-reader",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ],
        "docs": [
            "sphinx>=3.0",
            "sphinx-rtd-theme>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "xtc1reader=xtc1reader.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="lcls xray physics detector xtc psana",
    project_urls={
        "Bug Reports": "https://github.com/carbonscott/min-xtc1-reader/issues",
        "Source": "https://github.com/carbonscott/min-xtc1-reader",
        "Documentation": "https://github.com/carbonscott/min-xtc1-reader/blob/main/README.md",
    },
    include_package_data=True,
    zip_safe=False,
)
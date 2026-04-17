from setuptools import setup, find_packages

setup(
    name="veritas_ai",
    version="0.1.0",
    package_dir={"": "veritas-ai"},
    packages=find_packages(where="veritas-ai"),
)

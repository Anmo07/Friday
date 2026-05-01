from setuptools import setup, find_packages

setup(
    name="friday",
    version="0.2.0",
    package_dir={"": "friday"},
    packages=find_packages(where="friday"),
)

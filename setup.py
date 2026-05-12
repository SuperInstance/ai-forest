from setuptools import setup, find_packages

setup(
    name="plato-ft",
    version="0.2.0",
    description="PLATO compute toolkit — Fortran-native int32 array ops",
    py_modules=["ft"],
    package_dir={"": "fortran"},
    entry_points={"console_scripts": ["ft=ft:main"]},
    python_requires=">=3.8",
)

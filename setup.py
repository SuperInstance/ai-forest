from setuptools import setup
setup(
    name="plato-sdk",
    version="0.3.0",
    description="PLATO SDK — Python client for room-based knowledge systems",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/SuperInstance/ai-forest",
    py_modules=["plato_sdk"],
    package_dir={"": "."},
    entry_points={"console_scripts": ["ft=plato_sdk:main"]},
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

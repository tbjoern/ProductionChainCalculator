from setuptools import find_packages, setup

setup(
    name="production-chain-calculator",
    packages=find_packages(),
    install_requires=["scipy==1.11.4"],
    extras_require={
        "server": [
            "flask",
        ],
        "dev": [
            "pytest==8.1.2",
            "pytest-datadir==1.5.0",
        ],
    },
)

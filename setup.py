from setuptools import setup, find_packages

with open("asyncio_nutclient/version.py", "r") as f:
    exec(f.read())

with open("README.md", "r", encoding="utf-8") as readme_file:
    readme = readme_file.read()

setup(
    name="asyncio_nutclient",
    version=__version__,
    packages=find_packages(),
    package_data={
        "asyncio_nutclient": ["py.typed"],
    },
    url="https://github.com/vincentto13/asyncio_nutclient",
    author="Paweł Rapkiewicz",
    author_email="pawel.rapkiewicz@gmail.com",
    description="Library that talks Network UPS Tools Daemon in AsyncIO way.",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT License",
    license_files = ('LICENSE',),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
    ],
)
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="pawprint",
    version="1.2.0",
    description="A flexible event tracker for rapid analysis.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/qcaudron/pawprint",
    author="Quentin CAUDRON",
    author_email="quentincaudron@gmail.com",
    license="MIT",
    packages=["pawprint"],
    zip_safe=False,
    test_suite="tests",
    install_requires=["pandas>=0.19", "sqlalchemy>=1.0", "psycopg2>=2.4"],
    python_requires=">=3.5",
)

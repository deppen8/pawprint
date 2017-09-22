from setuptools import setup

setup(
    name="pawprint",
    version="1.0.1",
    description="A flexible event tracker for rapid analysis.",
    url="http://github.com/cbredev/pawprint",
    author="Quentin CAUDRON",
    author_email="quentincaudron@gmail.com",
    license="MIT",
    packages=["pawprint"],
    zip_safe=False,
    test_suite="tests",
    install_requires=[
        "pandas>=0.19",
        "sqlalchemy>=1.0",
        "psycopg2>=2.4"
    ]
)

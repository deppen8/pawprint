import pytest
import pawprint
import pandas as pd
from sqlalchemy.exc import ProgrammingError
import logging


@pytest.fixture(scope="session")
def db_string():
    return "postgresql+psycopg2://pawprint_dev:pawprinttest@localhost:5432/pawprint_test_db"


@pytest.fixture(scope="session")
def table_name():
    return "pawprint_test_table"


@pytest.fixture()
def drop_test_table(tmpdir, db_string, table_name):
    yield

    try:
        pd.io.sql.execute("DROP TABLE {}".format(table_name), db_string)
    except ProgrammingError:  # if can't delete table, skip
        pass


@pytest.fixture()
def pawprint_default_db(tmpdir, drop_test_table, db_string, table_name):
    """Set up DB before tests, tear down after

    Parameters
    ----------
    tmpdir : pytest tmpdir
        pytest built in tmpdir fixture
    """
    # TODO: setup DB
    return pawprint.Tracker(db=db_string, table=table_name)


@pytest.fixture()
def pawprint_default_db_with_table(tmpdir, drop_test_table, db_string, table_name):
    """Set up DB before tests, tear down after

    Parameters
    ----------
    tmpdir : pytest tmpdir
        pytest built in tmpdir fixture
    """
    # TODO: setup DB
    tracker = pawprint.Tracker(db=db_string, table=table_name)
    tracker.create_table()
    return tracker

    # drop_test_table fixture will teardown the table


@pytest.fixture()
def error_logger(tmpdir):
    logger = logging.getLogger("pawprint_logger")
    handler = logging.FileHandler("pawprint.log", mode="w")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

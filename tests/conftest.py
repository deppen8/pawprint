from datetime import datetime, timedelta
import pytest
import pawprint
import pandas as pd
from sqlalchemy.exc import ProgrammingError
import logging


# GENERAL-USE FIXTURES


@pytest.fixture(scope="session")
def db_string():
    return "postgresql+psycopg2://pawprint_dev:pawprinttest@localhost:5432/pawprint_test_db"


# FIXTURES FOR test_tracker.py


@pytest.fixture(scope="session")
def tracker_test_table_name():
    return "pawprint_test_tracker_table"


@pytest.fixture()
def drop_tracker_test_table(tmpdir, db_string, tracker_test_table_name):
    yield

    try:
        pd.io.sql.execute("DROP TABLE {}".format(tracker_test_table_name), db_string)
    except ProgrammingError:  # if can't delete table, skip
        pass


@pytest.fixture()
def pawprint_default_tracker_db(
    tmpdir, drop_tracker_test_table, db_string, tracker_test_table_name
):
    """Set up DB before tests, tear down after"""

    return pawprint.Tracker(db=db_string, table=tracker_test_table_name)


@pytest.fixture()
def pawprint_default_tracker_db_with_table(
    tmpdir, drop_tracker_test_table, db_string, tracker_test_table_name
):
    """Set up DB with table before tests"""
    # TODO: setup DB
    tracker = pawprint.Tracker(db=db_string, table=tracker_test_table_name)
    tracker.create_table()
    return tracker

    # drop_tracker_test_table fixture will teardown the table


@pytest.fixture()
def error_logger(tmpdir):
    logger = logging.getLogger("pawprint_logger")
    handler = logging.FileHandler("pawprint.log", mode="w")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


# FIXTURES FOR test_statistics.py


@pytest.fixture(scope="session")
def statistics_test_table_names():
    return {
        "tracker_table": "pawprint_test_statistics_table",
        "sessions_table": "pawprint_test_statistics_table__sessions",
        "engagement_table": "pawprint_test_statistics_table__engagement",
    }


@pytest.fixture()
def drop_statistics_test_table(tmpdir, db_string, statistics_test_table_names):
    yield

    for _, table in statistics_test_table_names.items():
        try:
            pd.io.sql.execute("DROP TABLE {}".format(table), db_string)
        except ProgrammingError:  # if can't delete table, skip
            pass


@pytest.fixture()
def pawprint_default_statistics_tracker(
    tmpdir, drop_statistics_test_table, db_string, statistics_test_table_names
):
    """Set up DB with table before tests"""
    # List of users who performed events
    users = [
        "Frodo",
        "Frodo",
        "Frodo",
        "Frodo",
        "Frodo",
        "Frodo",
        "Gandalf",
        "Gandalf",
        "Frodo",
        "Gandalf",
        "Gandalf",
        "Frodo",
        "Frodo",
        "Frodo",
        "Frodo",
        "Frodo",
    ]

    # List of times ( minutes ) between any event and the first events
    timedeltas = [0, 1, 2, 3, 4, 5, 100, 110, 120, 130, 140, 1000, 1001, 1002, 1003, 1004]

    # Create a tracker
    tracker = pawprint.Tracker(db=db_string, table=statistics_test_table_names["tracker_table"])
    tracker.create_table()

    # Yesterday morning
    today = datetime.now()
    yesterday = datetime(today.year, today.month, today.day, 9, 0) - timedelta(days=1)

    # Write all events
    for user, delta in zip(users, timedeltas):
        tracker.write(user_id=user, timestamp=yesterday + timedelta(minutes=delta))

    # Save the tracker
    return tracker

    # drop_statistics_test_table fixture will teardown the table

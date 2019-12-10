import os
import json
import pytest

from datetime import datetime
from collections import OrderedDict

import numpy as np
import pandas as pd
from sqlalchemy.exc import ProgrammingError

import pawprint


def test_create_table_with_default_options(pawprint_default_db):
    """Ensure the table is correctly created with the default schema."""

    tracker = pawprint_default_db

    # The table shouldn't exist. Assert it's correct created.
    assert tracker.create_table() is None

    # Try creating it again. This should raise an error.
    with pytest.raises(ProgrammingError):
        tracker.create_table()

    # Assert the table is empty when created
    assert pd.io.sql.execute(
        "SELECT COUNT(*) FROM {}".format(tracker.table), tracker.db
    ).fetchall() == [(0,)]

    # Ensure its schema is correct
    schema = pd.io.sql.execute(
        "SELECT column_name, data_type, character_maximum_length "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE table_name = '{}'".format(tracker.table),
        tracker.db,
    ).fetchall()
    expected_schema = [
        (u"id", u"integer", None),
        (u"timestamp", u"timestamp without time zone", None),
        (u"user_id", u"text", None),
        (u"event", u"text", None),
        (u"metadata", u"jsonb", None),
    ]
    assert schema == expected_schema


def test_drop_table(pawprint_default_db_with_table):
    """Ensure that tables are deleted successfully."""

    tracker = pawprint_default_db_with_table

    # make sure table exists
    with pytest.raises(ProgrammingError):
        tracker.create_table()

    tracker.drop_table()

    with pytest.raises(ProgrammingError):
        tracker.drop_table()


def test_instantiate_tracker_from_dot_file(drop_test_table):
    """Test instantiating a Tracker with a dotfile instead of using db and table strings."""

    # Write a dotfile to disk
    dotfile = {
        "db": "postgresql:///little_bean_toes",
        "json_field": "such_fuzzy",
    }

    with open(".pawprint", "w") as f:
        json.dump(dotfile, f)

    # Create a tracker from this dotfile
    tracker = pawprint.Tracker(dotfile=".pawprint", json_field="boop")

    # Ensure all the entries are as they should be
    assert tracker.db == "postgresql:///little_bean_toes"
    assert tracker.table is None
    assert tracker.logger is None
    assert tracker.json_field == "boop"  # field present in dotfile but overwritten in init

    os.remove(".pawprint")


def test_create_table_with_other_options(drop_test_table, db_string, table_name):
    """Ensure the table is correctly created with an alternative schema."""

    schema = OrderedDict([("pk", "SERIAL PRIMARY KEY"), ("infofield", "TEXT")])
    tracker = pawprint.Tracker(db=db_string, table=table_name, schema=schema)
    tracker.create_table()

    # Ensure its schema is correct
    schema = pd.io.sql.execute(
        "SELECT column_name, data_type, character_maximum_length "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE table_name = '{}'".format(tracker.table),
        tracker.db,
    ).fetchall()

    assert schema == [("pk", "integer", None), ("infofield", "text", None)]


def test_write(drop_test_table, db_string, table_name):
    """Test the tracking of an event."""

    tracker = pawprint.Tracker(db=db_string, table=table_name, schema={"id": "INT"})
    tracker.create_table()

    # Check the table's empty
    assert pd.io.sql.execute(
        "SELECT COUNT(*) FROM {}".format(tracker.table), tracker.db
    ).fetchall() == [(0,)]

    # Add some data and check if the row count increases by one
    tracker.write(id=1337)
    assert pd.io.sql.execute(
        "SELECT COUNT(*) FROM {}".format(tracker.table), tracker.db
    ).fetchall() == [(1,)]

    # Pull the data and ensure it's correct
    data = pd.read_sql("SELECT * FROM {}".format(tracker.table), tracker.db)
    assert isinstance(data, pd.DataFrame)
    assert len(data.columns) == 1
    assert data.columns[0] == "id"
    assert data.id[0] == 1337


def test_read(pawprint_default_db_with_table):
    """Test pulling the data into a dataframe according to various simple filters."""

    tracker = pawprint_default_db_with_table

    # Ensure the table is empty to begin with
    assert len(tracker.read()) == 0

    # Add some data
    tracker.write(user_id="Pawprint", event="Testing !")
    tracker.write(user_id="Pawprint")
    tracker.write(event="No user")
    tracker.write(
        user_id="import this",
        event="very zen",
        metadata={
            "better": "forgiveness",
            "worse": "permission",
            "ordered": ["simple", "complex", "complicated"],
        },
    )

    all_data = tracker.read()
    pawprint_events = tracker.read(user_id="Pawprint")
    id_gt_events = tracker.read(id__gt=10)
    id_gte_lt_events = tracker.read(id__gte=1, id__lt=3)
    field_events = tracker.read("event", id__lte=100, event="very zen")
    contains_events = tracker.read(metadata__contains="better")
    not_contains_events = tracker.read(metadata__contains="whisky")

    assert len(all_data) == 4
    assert len(pawprint_events) == 2
    assert len(id_gt_events) == 0
    assert len(id_gte_lt_events) == 2
    assert len(field_events) == 1
    assert len(contains_events) == 1
    assert len(not_contains_events) == 0

    assert set(all_data.columns) == set(["id", "user_id", "event", "metadata", "timestamp"])
    assert set(field_events.columns) == set(["event"])


def test_counts(pawprint_default_db_with_table):
    """Test counting a specific event, with date ranges and time resolutions."""

    tracker = pawprint_default_db_with_table

    # Add a bunch of events
    query = (
        """
        INSERT INTO {} (timestamp, user_id, event) VALUES
        ('2016-01-01 12:30', 'alice', 'logged_in'),
        ('2016-01-01 12:40', 'bob', 'logged_in'),
        ('2016-01-01 16:00', 'charlotte', 'logged_in'),
        ('2016-01-02 00:00', 'dan', 'logged_in'),
        ('2016-01-02 00:00', 'elizabeth', 'logged_in'),
        ('2016-01-05 00:00', 'frank', 'logged_in'),
        ('2016-01-10 00:00', 'gabrielle', 'logged_in'),
        ('2016-01-20 00:00', 'hans', 'logged_in'),
        ('2016-02-01 00:00', 'iris', 'logged_in'),
        ('2016-02-01 00:00', 'james', 'logged_in'),
        ('2016-03-01 00:00', 'kelly', 'logged_in'),
        ('2016-03-01 00:00', 'laura', 'logged_in'),
        ('2016-03-01 00:00', 'mike', 'not_logged_in')
    """
    ).format(tracker.table)

    pd.io.sql.execute(query, tracker.db)

    logins_hourly = tracker.count(event="logged_in", resolution="hour")
    logins_daily = tracker.count(event="logged_in")
    logins_weekly = tracker.count(event="logged_in", resolution="week")
    logins_monthly = tracker.count(event="logged_in", resolution="month")
    logins_weekly_left_range = tracker.count(
        event="logged_in", resolution="week", start=datetime(2016, 2, 1)
    )
    logins_weekly_right_range = tracker.count(
        event="logged_in", resolution="week", end=datetime(2016, 2, 1)
    )
    logins_daily_full_range = tracker.count(
        event="logged_in", start=datetime(2016, 1, 15), end=datetime(2016, 2, 15)
    )

    # Hourly
    assert len(logins_hourly) == 8
    assert np.all(logins_hourly["count"].values == [2, 1, 2, 1, 1, 1, 2, 2])

    # Daily
    assert len(logins_daily) == 7
    assert np.all(logins_daily["count"].values == [3, 2, 1, 1, 1, 2, 2])

    # Weekly
    assert len(logins_weekly) == 5
    assert np.all(logins_weekly["count"].values == [5, 2, 1, 2, 2])

    # Others
    assert len(logins_monthly) == 3
    assert len(logins_weekly_left_range) == 2  # weeks start on Monday
    assert len(logins_weekly_right_range) == 4  # and not at the start / end dates provided
    assert len(logins_daily_full_range) == 2


def test_sum_and_average(pawprint_default_db_with_table):
    """Test aggregating a specific event, with date ranges and time resolutions."""

    tracker = pawprint_default_db_with_table

    metadata = str('{"val": 1}').replace("'", '"')

    # Add a bunch of events
    query = (
        """
        INSERT INTO {table} (timestamp, user_id, event, metadata) VALUES
        ('2016-01-01 12:30', 'alice', 'logged_in', '{metadata}'),
        ('2016-01-01 12:40', 'bob', 'logged_in', '{metadata}'),
        ('2016-01-01 16:00', 'charlotte', 'logged_in', '{metadata}'),
        ('2016-01-02 00:00', 'dan', 'logged_in', '{metadata}'),
        ('2016-01-02 00:00', 'elizabeth', 'logged_in', '{metadata}'),
        ('2016-01-05 00:00', 'frank', 'logged_in', '{metadata}'),
        ('2016-01-10 00:00', 'gabrielle', 'logged_in', '{metadata}'),
        ('2016-01-20 00:00', 'hans', 'logged_in', '{metadata}'),
        ('2016-02-01 00:00', 'iris', 'logged_in', '{metadata}'),
        ('2016-02-01 00:00', 'james', 'logged_in', '{metadata}'),
        ('2016-03-01 00:00', 'kelly', 'logged_in', '{metadata}'),
        ('2016-03-01 00:00', 'laura', 'logged_in', '{metadata}'),
        ('2016-03-01 00:00', 'mike', 'not_logged_in', '{metadata}')
    """
    ).format(table=tracker.table, metadata=metadata)

    pd.io.sql.execute(query, tracker.db)

    x_sum_daily_all = tracker.sum("metadata__val")
    x_sum_daily = tracker.sum("metadata__val", event="logged_in")

    x_avg_daily_all = tracker.average("metadata__val", event="logged_in")
    x_avg_daily = tracker.average("metadata__val", event="logged_in")

    assert len(x_sum_daily) == 7

    assert np.all(x_sum_daily_all["sum"].values == [3, 2, 1, 1, 1, 2, 3])
    assert np.all(x_sum_daily["sum"].values == [3, 2, 1, 1, 1, 2, 2])

    assert np.all(x_avg_daily_all["avg"].values == [1, 1, 1, 1, 1, 1, 1])
    assert np.all(x_avg_daily["avg"] == x_avg_daily_all["avg"])


def test_parse_fields(pawprint_default_db):
    """Test args passed to read() and _aggregate() are parsed correctly."""

    tracker = pawprint_default_db

    # SELECT * FROM table
    args = ()
    assert tracker._parse_fields(*args) == "*"

    # SELECT event FROM table
    args = ("event",)
    assert tracker._parse_fields(*args) == "event"

    # SELECT user_id, timestamp FROM table
    args = ("user_id", "timestamp")
    assert tracker._parse_fields(*args) == "user_id, timestamp"

    # SELECT metadata #>> '{a, b}' FROM table
    args = ("metadata__a__b",)
    assert tracker._parse_fields(*args) == "metadata #> '{a, b}' AS json_field"


def test_parse_values(pawprint_default_db):
    """Test parsing values for write()."""

    tracker = pawprint_default_db

    # INSERT INTO table (event) VALUES ('logged_in')
    args = ("logged_in",)
    assert tracker._parse_values(*args) == "'logged_in'"

    # INSERT INTO table (event, user_id) VALUES ('logged_in', 'hannah')
    args = ("logged_in", "hannah")
    assert tracker._parse_values(*args) == "'logged_in', 'hannah'"


def test_parse_conditionals(pawprint_default_db):
    """Test kwargs passed to read() and _aggregate() are parsed correctly."""

    tracker = pawprint_default_db

    # SELECT * FROM table
    kwargs = {}
    assert tracker._parse_conditionals(**kwargs) == ""

    # SELECT * FROM table WHERE user_id = 'Quentin'
    kwargs = {"user_id": "Quentin"}
    assert tracker._parse_conditionals(**kwargs) == "WHERE user_id = 'Quentin'"

    # SELECT * FROM table WHERE event = 'logged_in' AND user_id = 'Quentin'
    kwargs = {"event": "logged_in", "user_id": "Quentin"}
    assert tracker._parse_conditionals(**kwargs) in (
        "WHERE event = 'logged_in' AND user_id = 'Quentin'",
        "WHERE user_id = 'Quentin' AND event = 'logged_in'",
    )

    # SELECT * FROM table WHERE event IN ('logged_in', 'logged_out')
    kwargs = {"event__in": ["logged_in", "logged_out"]}
    assert tracker._parse_conditionals(**kwargs) == "WHERE event IN ('logged_in', 'logged_out')"


def test_accessing_json_fields(pawprint_default_db_with_table):
    """Test some structured data pulling."""

    tracker = pawprint_default_db_with_table

    # JSON objects in our tracking database
    simple = {"integral": "derivative"}
    medium = {"montecarlo": {"prior": "likelihood"}}
    difficult = {
        "deepnet": ["mlp", "cnn", "rnn"],
        "ensembles": {"random": "forest", "always": {"cross_validate": ["kfold", "stratified"]},},
    }

    tracker.write(event="maths", metadata=simple)
    tracker.write(event="stats", metadata=medium)
    tracker.write(event="ml", metadata=difficult)

    maths_all = tracker.read("metadata__integral")
    maths_condition = tracker.read("metadata__integral", event="maths")
    assert len(maths_all) == 3
    assert len(maths_condition) == 1
    assert list(maths_all.json_field) == ["derivative", None, None]

    stats = tracker.read("metadata__montecarlo__prior").dropna()
    assert len(stats) == 1
    assert stats.json_field.iloc[0] == "likelihood"

    types_of_nn = tracker.read("metadata__deepnet").dropna()
    best_nn = tracker.read("metadata__deepnet__1").dropna()
    full_depth = tracker.read("metadata__ensembles__always__cross_validate__0").dropna()
    assert len(types_of_nn) == 1
    assert len(best_nn) == 1
    assert best_nn.json_field.iloc[0] == "cnn"
    assert len(full_depth) == 1
    assert full_depth.json_field.iloc[0] == "kfold"


def test_json_maths(pawprint_default_db_with_table):
    """More advanced operations on JSON subfields."""

    tracker = pawprint_default_db_with_table

    tracker.write(event="whisky", metadata={"uigeadail": {"value": 123, "lagavulin": [4, 2]}})
    tracker.write(event="whisky", metadata={"uigeadail": {"value": 456, "lagavulin": [5, 0]}})
    tracker.write(event="whisky", metadata={"uigeadail": {"value": 758, "lagavulin": [7, 10]}})
    tracker.write(event="armagnac", metadata={"age": "XO"})
    tracker.write(event="armagnac", metadata={"age": 15})

    assert len(tracker.read()) == 5
    assert len(tracker.read(metadata__uigeadail__contains="lagavulin")) == 3
    assert len(tracker.read(metadata__uigeadail__value__gt=123)) == 2
    assert len(tracker.read(metadata__uigeadail__value__gte=123)) == 3

    whiskies = tracker.sum("metadata__uigeadail__value")
    assert len(whiskies) == 1
    assert whiskies.iloc[0]["sum"] == 1337

    assert len(tracker.read(metadata__contains="age")) == 2
    assert len(tracker.read(metadata__age="XO")) == 1


def test_silent_write_errors():
    """When a failure occurs in event write, it should fail silently."""

    tracker = pawprint.Tracker(db=None, table=None)

    try:
        tracker.write(event="This will fail silently.")
    except Exception:
        pytest.fail("Failed to fail silently.")


def test_nonsilent_write_errors(error_logger):
    """Test non-silent write errors that should output to the logger or raise exceptions."""

    tracker = pawprint.Tracker(db="postgresql:///fail", logger=error_logger)

    with pytest.raises(Exception):
        tracker.write()
    with pytest.raises(Exception):
        tracker.write(event="going_to_fail")

    with open("pawprint.log", mode="r") as f:
        logs = f.readlines()
        print(logs[3])

    assert len(logs) == 6
    assert logs[0].startswith("pawprint failed to write.")
    assert "Table: None. Query: INSERT INTO None () VALUES ();" in logs[0]
    assert "Query: INSERT INTO None (event) VALUES ('going_to_fail')" in logs[3]


def test_auto_timestamp(db_string):
    """Ensure that timestamps are autopopulated correctly if not passed."""

    # Define a schema where the timestamp doesn't automatically populate through the database
    schema = {"event": "TEXT", "timestamp": "TIMESTAMP"}

    # Put together two trackers, one that autopopulates the timestamp
    no_auto = pawprint.Tracker(db=db_string, table="no_auto", auto_timestamp=False, schema=schema)
    auto = pawprint.Tracker(db=db_string, table="auto", auto_timestamp=True, schema=schema)

    # Create clean tables
    no_auto.create_table()
    auto.create_table()

    # Write events with no timestamp
    no_auto.write(event="foo")
    auto.write(event="bar")

    assert len(no_auto.read()) == 1
    assert len(auto.read()) == 1

    assert len(no_auto.read().dropna()) == 0
    assert len(auto.read().dropna()) == 1

    # Drop tables at the end
    no_auto.drop_table()
    auto.drop_table()


def test_repr_and_str(pawprint_default_db):
    """Test the __repr__ and __str__."""
    tracker = pawprint_default_db
    expected_repr = "pawprint.Tracker on table '{}' and database '{}'".format(
        tracker.table, tracker.db
    )
    expected_str = "pawprint Tracker object.\ndb : {}\ntable : {}".format(tracker.db, tracker.table)
    assert tracker.__repr__() == expected_repr
    assert tracker.__str__() == expected_str


def test_malicious_strings(pawprint_default_db_with_table):
    """Test that SQL injection strings are sanitized"""
    tracker = pawprint_default_db_with_table

    tracker.write(
        event="armageddon",
        metadata={
            "shady business": {
                "with": "the following string",
                "of sql": "50');INSERT INTO {table} (event, user_id) VALUES "
                "('you got pwnd', '50".format(table=tracker.table),
            }
        },
    )
    assert len(tracker.read()) == 1

    tracker.write(
        event="armageddon",
        metadata={
            "more shady business": {
                "my shady sql": "' OR '1'='1;DROP TABLE {table};".format(table=tracker.table)
            }
        },
    )
    assert len(tracker.read()) == 2

    tracker.write(
        event="' OR '1'='1;",
        metadata={"foo": "x'); DROP TABLE {table}; --".format(table=tracker.table)},
    )
    assert len(tracker.read()) == 3


def test_escaping_from_quotes(pawprint_default_db_with_table):
    tracker = pawprint_default_db_with_table
    tracker.write(
        event="known crummy string",
        metadata={
            "foo": {
                "toState": "#/app/dealnotes/2345/FORPETE'S_SAKE,_LLC_Tenant_Rep_Lease_2",
                "fromState": "#/app/dealdetails/2345",
                "platform": "iOS App",
            }
        },
    )
    assert len(tracker.read()) == 1

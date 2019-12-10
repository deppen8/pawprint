from collections import OrderedDict
import json
from datetime import datetime
from warnings import warn
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError


class Tracker(object):
    """
    This class provides an easy interface to create a database table and send events to it.
    """

    def __init__(self, **kwargs):

        # Parse inputs by merging config files and locally-passed arguments
        if "dotfile" in kwargs:
            with open(kwargs["dotfile"], "r") as f:
                config = json.load(f)
                config.update(kwargs)
        else:
            config = kwargs

        # Set a default schema if none is passed
        if "schema" not in config:
            config["schema"] = OrderedDict(
                [
                    ("id", "SERIAL PRIMARY KEY"),
                    ("timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                    ("user_id", "TEXT"),
                    ("event", "TEXT"),
                    ("metadata", "JSONB"),
                ]
            )
        else:  # If a schema is passed, ensure it's an ordered dict
            if not isinstance(config["schema"], OrderedDict) and isinstance(config["schema"], dict):
                config["schema"] = OrderedDict(config["schema"])

        # Save the database properties
        self.db = config.get("db", None)
        self.table = config.get("table", None)
        self.logger = config.get("logger", None)
        self.json_field = config.get("json_field", "metadata")
        self.user_field = config.get("user_field", "user_id")
        self.timestamp_field = config.get("timestamp_field", "timestamp")
        self.auto_timestamp = config.get("auto_timestamp", False)
        self.schema = config["schema"]

        # Create the connection engine
        if self.db is not None:
            self.engine = create_engine(self.db)

    def create_table(self):
        """
        Create a database with the correct schema.
        """

        # Build a query from the schema
        fields = ", ".join(
            "{} {}".format(field_name, field_type) for field_name, field_type in self.schema.items()
        )
        query = "CREATE TABLE {} ({})".format(self.table, fields)

        # Execute the query to create the table.
        pd.io.sql.execute(query, self.engine)

    def drop_table(self):
        """Delete an existing table."""
        try:
            self.query("DROP TABLE {}".format(self.table))
        except ProgrammingError:
            warn("Table drop unsuccessful. Check that table exists.")
            raise

    def write(self, **data):
        """
        Send a generic event to the user metrics database.
        """

        # If we're autopopulating a timestamp and it isn't provided, add it
        if self.auto_timestamp and self.timestamp_field not in data:
            data[self.timestamp_field] = datetime.now()

        # Parse the field headers
        fields = ", ".join(data.keys())

        values = data.values()
        new_values = []
        for value in values:
            if isinstance(value, dict):
                new_values.append(json.dumps(value))
            else:
                new_values.append(str(value))
        values = new_values

        # Build the PostgreSQL query
        placeholders = "{}".format(", ".join(["%s"] * len(values)))
        query = "INSERT INTO {table} ({fields}) VALUES ({placeholders});".format(
            table=self.table, fields=fields, placeholders=placeholders
        )

        # Write to the database
        try:
            self.engine.execute(query, values)

        # If the write fails, raise the exception
        except Exception as exception:
            if self.db is not None:  # If db is None, fail silently. Otherwise, raise the error

                # If we have a logger, log the error
                if self.logger:
                    # add vars to the query string
                    query = query.replace("%s", "'{}'").format(*values)
                    self.logger.warning(
                        "pawprint failed to write. Table: {}. Query: {}. Exception: {} ({})".format(
                            self.table, query, exception, exception.args
                        )
                    )

                raise

    def read(self, *fields, **conditionals):
        """
        Pull raw data into a dataframe. If no conditions are passed, pull the whole table.
        Otherwise, filter based on the conditions specified ( currently only equality ).
        """

        # Parse the list of fields to return
        field_query = self._parse_fields(*fields)

        # Parse the conditions
        conditionals_query = self._parse_conditionals(**conditionals)

        query = "SELECT {} FROM {} {}".format(field_query, self.table, conditionals_query)

        if "DISTINCT" not in query:
            query += " ORDER BY {}".format(self.timestamp_field)

        return pd.read_sql(query, self.db)

    def count(self, count_field="*", resolution="day", start=None, end=None, **conditionals):
        """Count events of a given type."""
        return self._aggregate("COUNT", resolution, start, end, count_field, **conditionals)

    def sum(self, sum_field, resolution="day", start=None, end=None, **conditionals):
        """Sum numerical values of events of a given type."""
        return self._aggregate("SUM", resolution, start, end, sum_field, **conditionals)

    def average(self, avg_field, resolution="day", start=None, end=None, **conditionals):
        """Average events of a given type."""
        return self._aggregate("AVG", resolution, start, end, avg_field, **conditionals)

    def query(self, query):  # pragma: no cover
        """User-defined SQL query."""
        return pd.io.sql.execute(query, self.engine)

    def _aggregate(self, agg_operation, resolution, start, end, agg_field, **conditionals):
        """
        Aggregate events into a dataframe, between a date range, at a given temporal resolution.
        """

        # Set temporal range
        if start is None:
            start = datetime(1900, 1, 1)
        if end is None:
            end = datetime(2100, 1, 1)

        if agg_operation == "COUNT":
            agg_query = "COUNT ({})".format(agg_field)
        else:
            agg_query = "{aggregate}(({field})::float)".format(
                aggregate=agg_operation,
                field=self._parse_fields(agg_field, skip_alias=True, json_aggregate=True),
            )

        # Parse conditionals; replace WHERE with AND
        conditionals = self._parse_conditionals(**conditionals).replace("WHERE", "AND")

        # Construct the query
        query = (
            "SELECT date_trunc(%(resolution)s, {timestamp}) AS datetime, "
            "{aggregate} FROM {table} "
            "WHERE {timestamp} >= %(start)s "
            "AND {timestamp} <= %(end)s "
            "{conditionals} "
            "GROUP BY date_trunc(%(resolution)s, {timestamp}) "
            "ORDER BY date_trunc(%(resolution)s, {timestamp})".format(
                timestamp=self.timestamp_field,
                aggregate=agg_query,
                table=self.table,
                conditionals=conditionals,
            )
        )
        params = {"resolution": resolution, "start": start, "end": end}
        return pd.read_sql(query, self.db, params=params)

    def _parse_fields(self, *fields, **kwargs):
        """
        Parse a list of fields to be returned by .read() or ._aggregate(). Any field that isn't
        self.json_field oesn't change; any fields that reference the JSON field are parsed into
        JSONB syntax.

        Returns a comma-separated string that can be used in a SQL query.
        """

        # Example :
        #   "event"
        #   "user_id"

        # If the user requests no specific fields, return all fields
        if not fields:
            return "*"

        # Otherwise, parse the requested fields
        parsed = []
        for field in fields:

            # If the field is not a JSON field, or is the root JSON field itself, return it as-is
            if not (field.startswith(self.json_field) and field != self.json_field):
                parsed.append(field)

            # If it's a JSON field with some sort of traversal of the JSON, parse that
            else:
                operator = "#>>" if kwargs.get("json_aggregate") else "#>"
                jsonfield = self.json_field + " {operator} '{{{subfields}}}'".format(
                    operator=operator, subfields=", ".join(field.split("__")[1:])
                )

                if not kwargs.get("skip_alias"):
                    jsonfield += " AS json_field"
                parsed.append(jsonfield)

        return ", ".join(parsed)

    def _parse_values(self, *values):
        """
        Return a generator where numerical values are strings and strings are 'strings'
        ( in single quotes ) for PostgreSQL queries.

        Returns a comma-separated string that can be used in a SQL query.
        """

        # Examples :
        #   "logged_in"
        #   3000
        #   "quentin"

        # Numerical values are as-is, strings get quotes, dicts become JSON strings
        def sqlsafe(value):
            if isinstance(value, dict):  # JSON needs to be correctly encoded
                return "'{}'".format(json.dumps(value))
            elif isinstance(value, list):  # for the IN operator
                return "({})".format(", ".join(["'{}'".format(i) for i in value]))
            else:
                return "'{}'".format(value)  # other things probably need to be in quotes

        if len(values) == 1:
            return sqlsafe(values[0])
        else:
            return ", ".join(sqlsafe(value) for value in values)

    def _parse_conditionals(self, **conditionals):
        """
        Parse the conditional expressions that are passed to .read() or ._aggregate().
        This includes modifiers.

        Returns a comma-separated string that can be used in a SQL query.
        """

        # Examples :
        #   event
        #   metadata__value
        #   metadata__value__contains
        #   user_id__gt

        modifiers = {"gt": ">", "lt": "<", "gte": ">=", "lte": "<=", "contains": "?", "in": "IN"}

        if not conditionals:
            return ""

        else:
            conditions_list = []

            for key, value in conditionals.items():

                # Determine equality vs nonequality conditionals; determine operation
                if key.split("__")[-1] in modifiers.keys():
                    modifier = key.split("__")[-1]
                    operator = modifiers[modifier]
                    key = "__".join(key.split("__")[:-1])
                else:
                    operator = "="

                # Parse the field and the conditional value
                field = self._parse_fields(key, skip_alias=True)
                rhs = self._parse_values(value)

                # In an equality when searching through json_field, compare with text and not JSON
                if operator == "=":
                    field = field.replace(" #> ", " #>> ")

                conditions_list.append("{} {} {}".format(field, operator, rhs))

        return "WHERE {}".format(" AND ".join(conditions_list))

    def __repr__(self):
        return "pawprint.Tracker on table '{}' and database '{}'".format(self.table, self.db)

    def __str__(self):
        return "pawprint Tracker object.\n" "db : {}\n" "table : {}".format(self.db, self.table)


# TODO : strip "event" requirement from aggregates
# TODO : more comments

# Getting set up

The central object for reading and writing events is `pawprint.Tracker`. This object handles the
interaction with your PostgreSQL database. It knows your database's connection information, your
table's schema, and which of the schema's field is the JSONB field for storing arbitrary metadata.
All tracking of user events goes through a `Tracker`, as well as any direct reads from the
database.

## Instantiating using keyword arguments

The `Tracker` contains a handful of attributes. All of these can be set as keyword arguments when
you instantiate a tracker. For example,
```python
from pawprint import Tracker
tracker = Tracker(db="postgresql:///events_tracking", table="user_events")
```
will create a tracker connecting to the `events_tracking` database on localhost and write events to
to table `user_events`.

Here's are all of the attributes that can be set using keyword arguments in this manner :

- `db` : the database connection string. By default, this is `None`. When that's the case, any
writes you perform using the `tracker.write()` method will fail silently; this is essentially a
debug mode.
- `table` : a string containing the name of the table to write events to.
- `schema` : an OrderedDict describing the attributes of the fields in the table. Keys are the
names of fields, and values are their JSON data types. See [schema](#schemas).
- `json_field` : the name of a field in the table that has the datatype `JSONB`. Only one field may
have this data type. This allows the `Tracker` to interpret your JSON queries into PostgreSQL's
syntax.
- `timestamp_field` : the name of the field in the table that tracks the date and time at which
the event was written. This is necessary for any aggregations you wish to perform.
- `user_field` : the name of the field in the table that tracks the user who performed the event.
This comes into play when deriving certain statistics, like average user session durations.
- `auto_timestamp` : a boolean that determines if `pawprint.write()` should automatically populate
the `timestamp_field` if a value isn't passed. In the default schema, the database can handle this.
However, should you use pawprint in an asynchronous manner, you may wish for a timestamp to be
passed rather than waiting for the database to take care of it.
- `logger` : a `Logger` object from Python's standard logging library. This object gets used to
issue errors when events fail to write.

All of these fields are optional to create a `Tracker`; however, event writing will fail silently
if `db` is not set. At a minimum, you realistically want to set `db` and `table`. Everything else
comes with [default values](#defaults) that make sense in most use cases.


## Instantiating using a configuration file

You can also instantiate a `Tracker` using a configuration file on disk. This file should be valid
JSON. Using a configuration file can be a nice way to keep everything in place and reduce the
amount of code that goes into creating a new tracker, if your use case varies substantially from
the default options.

For example, you can have a file `my_db_config.json` which may contain something like this :
```json
{
    "db": "postgresql://username:password@somehost.com:5432",
    "table": "tracking",
    "schema": {
        "timestamp": "TIMESTAMP",
        "user_id": "INT",
        "event_info": "JSONB"
    },
    "json_field": "event_info",
    "timestamp_field": "timestamp"
}
```

Then, you can instantiate a `Tracker` using
```python
tracker = Tracker(dotfile="my_db_config.json")
```

This will create a `Tracker` that a table that contains a timestamp field, an integer field for
user IDs, and a JSON field for storing anything you want. This one's not that different from the
[default schema](#defaults).

If you pass other keywords when instantiating a `Tracker`, those fields in the configuration file
will be overwritten. If, instead, you had instantiated using
```python
tracker = Tracker(dotfile="my_db_config.json", table="new_tracking")
```
then the `Tracker` will using the `new_tracking` table rather than `tracking`, but anything else
set in the configuration file will remain.


## Schemas

The `Tracker.schema` variable will describe the attributes of the table that events get written to.
It's only ever used when you call the tracker's `.create_table()` method, so if you already have a
database table set up, you don't need to worry about setting this attribute.

Schemas are ( ordered ) dictionaries mapping field names to PostgreSQL data types. When you specify
a schema, either as a keyword argument or in a configuration file, you can pass an OrderedDict, or
a standard Python dictionary, which the tracker will convert to an OrderedDict for you.

Here's an example of creating a table that uses a user-defined schema :
```python
# Define a schema for the table
schema = {
    "event_pk": "SERIAL PRIMARY KEY",
    "date": "DATE",
    "event": "TEXT",
    "info": "JSONB"
}

# Tracker pointing to an existing database but with no table, and this schema
tracker = Tracker(db="postgresql:///my_db", table="doesnt_exist", schema=schema)

# Create the table with this schema
tracker.create_table()
```

Take a look at [PostgreSQL's data types](https://www.postgresql.org/docs/9.6/static/datatype-datetime.html)
to see what options are available.

Another handy method is `.drop_table()`, which will drop the table the tracker is attached to.


## Defaults

By default, the `db`, `table`, and `logger` attributes are all `None`. Here are the implications :

- If `db` is `None`, any calls to `.write()` fail silently, to get out of your way when debugging.
- If `table` is `None`, but `db` is not, and you try tracking an event, an error will be raised.
- If `logger` is `None` and an error is raised, it simply won't be logged.

The default schema looks like this :
```python
OrderedDict([
    ("id", "SERIAL PRIMARY KEY"),
    ("timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("user_id", "VARCHAR(32)"),
    ("event", "VARCHAR(64)"),
    ("metadata", "JSONB")
])
```

Per this schema, the default `json_field` is `metadata`, and the default `timestamp` field is, of
course, `timestamp`. This table therefore contains these fields :

- `id` : the primary key that uniquely identifies each event. You don't need to pass this when
you're tracking an event, as it's automatically filled in.
- `timestamp` : a timestamp field ( with no timezone ), that defaults to the current timestamp if
you don't pass a value.
- `user_id` : a text field for storing the user's ID, serial number, email address, etc..
- `event` : a text field for naming the event that you're tracking.
- `metadata` : a binary JSON field that can store anything you can write as valid JSON, to track
any event-specific information. For example, if the event is a `chat_sent`, you may want to store
`{"to": "other_user"}` in this field.

Finally, the default value for `auto_timestamp` is `False`. If you set this to `True`, pawprint
will fill the `timestamp_field` with a UTC datetime before writing to the database. This ensures
that, if your event takes a while to get written ( say, due to high database load ), that the
event's timestamp is that at the time of event capture, and not at the time of writing.  


## Forbidden field names

Because of pawprint's query syntax, there are a number of names that you cannot use in your
database ( or if you do, expect strange behaviour ). These are :

- `resolution`
- anything with a double underscore
- anything that starts with the same text as your `json_field`

In addition, the query syntax uses text [modifiers](reading.md#conditional-expressions) to perform
conditional evaluation, so please don't use any modifiers as the keys of any JSON fields.

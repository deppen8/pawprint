# Tracking events

Events are written to the database using a `pawprint.Tracker` object. It's as simple as passing any
of the fields you want to the `.write()` method.

```python
# A simple user login event
tracker.write(event="user_logged_in", user_id="1337")

# A more complex event
metadata = {
    "client": {
        "name": "Ron Swanson",
        "company": "Breakfast Foods, Ltd.",
    },
    "details": {
        "invoice_amount": 23531.42,
        "due": "2017-06-15"
    }
}
tracker.write(event="invoice_received", metadata=metadata)
```


## Arguments

Arguments to `.write()` must be field names in your database. In the example above, we're using
the default schema, which has `event`, `user_id`, and `metadata` fields. Should we want to, we can
declare our own schema and use those fields instead.

```python
from pawprint import Tracker

tracker = Tracker(db="postgresql:///my_db", table="my_table", schema={"invoice_id": "TEXT"})
tracker.write(invoice_id="boop_123")
```

Note that his schema has no timestamp field, no primary key, and no JSON field, so is probably not
particularly useful !


## With the default schema

Because the default schema contains a timestamp field that autopopulates if you don't pass it, the
minimum you'll generally want to pass to `.write()` is an event. If that event is associated with
a user, that field can be passed too. All fields are optional, although at least one field must be
passed. Here's an example of how we might use the default schema when writing events.

```python
tracker.write(event="server_booted")
tracker.write(event="user_authentication", user_id="foo")
tracker.write(event="navigation", user_id="foo", metadata={"to": "dashboard", "platform": "web"})
tracker.write(event="chat_sent", user_id="foo", metadata={"to": "bar"})
tracker.write(event="task_completed", user_id="foo", metadata={"task_id": 123})
```

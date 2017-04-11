# Reading events

Reading from your events database is simple. All data comes back as a pandas DataFrame.

```python
tracker.read()
```

The output looks like this.

```
    id                    timestamp   user_id              event                      metadata
0    1   2017-03-31 12:19:43.073319      None      server_booted                          None
1    2   2017-03-31 12:19:43.084002     alice          logged_in                          None
2    3   2017-03-31 12:19:43.091005     alice         navigation           {'to': 'dashboard'}
3    4   2017-03-31 12:19:43.097624      None   payment_received   {'tax': 150, 'value': 1000}
4    5   2017-03-31 12:19:43.105161      None   payment_received     {'tax': 60, 'value': 400}
```

## Selecting fields to query

You can query a subset of fields to return by passing field names as arguments.

```python
tracker.read("event", "user_id")
```

```
               event   user_id
0      server_booted     None
1          logged_in    alice
2         navigation    alice
3   payment_received     None
4   payment_received     None
```


## Selecting JSON subfields

JSON fields can be treated as *fields within fields*. You can use a double underscore to access
these.

```python
tracker.read("metadata__tax")
```

```
    json_field
0          NaN
1          NaN
2          NaN
3        150.0
4         60.0
```

When you query your `json_field` ( in the default schema, it's called `metadata` ), the returning
field is called `json_field`. You can select several fields in this manner, though they'll all have
that name.

```python
tracker.read("timestamp", "metadata__tax", "metadata__value")
```

```
                    timestamp   json_field   json_field
0  2017-03-31 12:19:43.073319          NaN          NaN
1  2017-03-31 12:19:43.084002          NaN          NaN
2  2017-03-31 12:19:43.091005          NaN          NaN
3  2017-03-31 12:19:43.097624        150.0       1000.0
4  2017-03-31 12:19:43.105161         60.0        400.0
```

You can chain these double underscores. Say you had a JSON entry that looks like this :

```json
{
    "browser": {
        "name": "Chrome",
        "version": 57
    },
    "platform": {
        "OS": "macOS",
        "resolution": "1920x1080"
    }
}
```

You could get a list of only browser names by calling `tracker.read("metadata__browser__name")`.


## Conditional expressions

Conditional expressions are passed as keyword arguments into the `.read()` method. They use a set of
*modifiers* that also use a double underscore. The following modifiers are currently implemented :

- `gt` : greater than
- `gte` : greater than or equal to
- `lt` : less than
- `lte` : less than or equal to
- `contains` : contains the value
- `in` : is contained in a list

If you're looking for equality, you don't need a modifier. Using the dataset at the top of this page :

```python
tracker.read(user_id="alice")
```

```
    id                    timestamp   user_id        event              metadata
0    2   2017-03-31 12:19:43.084002     alice    logged_in                  None
1    3   2017-03-31 12:19:43.091005     alice   navigation   {'to': 'dashboard'}
```

This works with JSON fields too.

```python
tracker.read(metadata__tax__gt="100")
```

```
    id                    timestamp   user_id              event                      metadata
0    4   2017-03-31 12:19:43.097624      None   payment_received   {'tax': 150, 'value': 1000}

```

Note that, for querying JSON fields, even numerical values need to be passed as strings. For any
field that's a true PostgreSQL numerical type, you can pass numerical values.

```python
tracker.read(id__lte=2)
```

```
    id                    timestamp   user_id           event   metadata
0    1   2017-03-31 12:19:43.073319      None   server_booted       None
1    2   2017-03-31 12:19:43.084002     alice       logged_in       None
```

Finally, if you have an array stored in your JSON field, you can index against that. Say you have
an entry in your JSON field that looks like this :

```json
{
    "ensembles": {"random": "forest", "always": {"cross_validate": ["kfold", "stratified"]}}
}
```

Then you can access the first element in `cross_validate` using

```python
tracker.read("metadata__ensembles__always__cross_validate__0")
```

On this particular piece of JSON, you can also see uses for the `__in` and `__contains` modifiers.
For example, you could read only rows where there's a `cross_validate` key in the `always` subfield
of the `metadata` field :

```python
tracker.read(metadata__ensembles__always__contains="cross_validate")
```

The row containing this JSON object will be returned, because `metadata["ensembles"]["always"]`
does contain a key called `cross_validate`.

You could also check to see if a value contains one of several options :

```python
tracker.read(metadata__ensemble__random__in=["algorithm", "dataset"])
```

The row containing this JSON object will not be returned; the value at
`metadata["ensembles"]["random"]` is `forest`, and `forest` is not in the list
`["algorithm", "dataset"]`.


## Combining subsets and conditionals

Selecting a subset of fields is done using arguments, and conditional expressions are passed as
keyword arguments. You can therefore combine as many of these as you like.

```python
# When did we receive payments larger than $500 ?

# Read this query as, "Select only the timestamp field where the event is a payment_received
# and the value subfield in the metadata field is greater than 500"
tracker.read("timestamp", event="payment_received", metadata__value__gt=500)
```

```
                     timestamp
0   2017-03-31 12:19:43.097624
```

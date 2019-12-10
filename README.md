[![Build Status](https://travis-ci.org/QCaudron/pawprint.svg?branch=master)](https://travis-ci.org/QCaudron/pawprint) [![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/QCaudron/pawprint/master/LICENSE)


<img src="https://raw.githubusercontent.com/cbredev/pawprint/master/docs/images/pawprint.png" width="200px" align="right" />

# pawprint

**pawprint** allows you to quickly track events occurring in your application,
and analyse them using pandas.
For the full API, see the [documentation](http://pawprint.readthedocs.io). *These are a work
in progress*.


## Write data flexibly

```python
tracker.write(event="server_booted")
tracker.write(event="logged_in", user_id="alice")
tracker.write(event="navigation", user_id="bob", metadata={"to": "dashboard"})
tracker.write(event="invoice", metadata={"details": {"amount": 1214, "from": "Ardbeg"}})
tracker.write(event="invoice", metadata={"details": {"amount": 123, "from": "Lagavulin"}})
```

## Query data intuitively

### Read the full dataset.

```python
tracker.read()
```
```
    id                    timestamp   user_id           event                                            metadata  
0    1   2017-03-31 15:51:50.590018      None   server_booted                                                None
1    2   2017-03-31 15:51:50.599256     alice       logged_in                                                None
2    3   2017-03-31 15:51:50.610069       bob      navigation                                 {'to': 'dashboard'}
3    4   2017-03-31 15:51:50.620759      None         invoice     {'details': {'from': 'Ardbeg', 'amount': 1214}}
4    5   2017-03-31 15:51:50.629837      None         invoice   {'details': {'from': 'Lagavulin', 'amount': 123}}
```

### List only events where the user was Alice.

```python
tracker.read("event", user_id="alice")
```
```
        event
0   logged_in
```

### Query unstructured data to find out who invoiced you and when.

```python
tracker.read("timestamp", "metadata__details__from", event="invoice")
```
```
                     timestamp   json_field
0   2017-03-31 15:51:50.620759       Ardbeg
1   2017-03-31 15:51:50.629837    Lagavulin
```

### Perform aggregates over time.

```python
tracker.count("logged_in", resolution="week")
```
```
      datetime   count
0   2017-03-27       1
```

### Aggregate JSON subfields.

```python
tracker.sum(event="invoice", field="metadata__details__amount", resolution="year")
```
```
      datetime      sum
0   2017-01-01   1337.0
```

## Documentation

For installation, dependencies, API details, and a quickstart, please [RTFM](http://pawprint.readthedocs.io) !

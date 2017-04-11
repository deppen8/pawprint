# Performing aggregations

Because pawprint is an event tracker, it makes sense to consider how things change over time. As
such, aggregations are done over the time component of your data.

Let's say your dataset looks like this.

```
    id             timestamp          user_id            event          metadata
0    1   2017-01-03 12:34:00     eric_clapton        logged_in              None
1    2   2017-01-03 18:45:00    joe_bonamassa        logged_in              None
2    3   2017-01-04 07:12:00     eric_clapton        logged_in              None
3    4   2017-01-06 09:02:00   susan_tedeschi        logged_in              None
4    5   2017-01-09 15:14:00     eric_clapton        logged_in              None
5    6   2017-01-09 17:23:00          bb_king        logged_in              None
6    7   2017-01-09 17:25:00          bb_king   closed_account              None
7    8   2017-01-09 18:03:00    joe_bonamassa      sold_albums   {'count': 1912}
8    9   2017-01-09 19:07:00   susan_tedeschi      sold_albums   {'count': 1514}
9   10   2017-01-10 13:08:00    joe_bonamassa      sold_albums    {'count': 762}
```


## Counting events

By default, aggregates are performed over a daily timescale.

```python
tracker.count()
```

```
      datetime   count
0   2017-01-03       2
1   2017-01-04       1
2   2017-01-06       1
3   2017-01-09       3
4   2017-04-06       3
```

However, you pass in a `resolution` argument; valid values can be found [in the PostgreSQL
documentation](https://www.postgresql.org/docs/9.6/static/datatype-datetime.html#DATATYPE-INTERVAL-ISO8601-UNITS).

```python
tracker.count(resolution="week")
```

```
      datetime   count
0   2017-01-02       4
1   2017-01-09       3
2   2017-04-03       3
```

You can also pass in conditional expressions.

```python
tracker.count(event="logged_in", resolution="week")
```

```
     datetime   count
0  2017-01-02       4
1  2017-01-09       2
```

Finally, you can pass fields. For example, `tracker.count("DISTINCT(user_id)", resolution="month")`
will tell you how many active monthly users you have.


## Aggregating numerical values

Numerical fields can be summed or averaged. For example, we can see how many albums have been sold
this month :

```python
tracker.sum("metadata__count", resolution="month")
```

```
      datetime      sum
0   2017-01-09   3426.0
1   2017-01-10    762.0
```

We can also find out how many albums Joe Bonamassa sells on average in a year :

```python
tracker.average("metadata__count", user_id="joe_bonamassa", resolution="year")
```

```
      datetime      avg
0   2017-01-01   1337.0
```

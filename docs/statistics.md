# Derived Statistics

Derived statistics are those that are calculated from your events database.

You start with a `Statistics` object, which you connect to an existing `Tracker` :

```python
from pawprint import Statistics

# Pass your Tracker instance to the instantiation of the Statistics object
stats = Statistics(tracker)
```

## Generating and reading statistics

You can access any existing statistics tables using a `Tracker` object, which means you have
access to all of the `Tracker`'s methods.

```python
# Both of these objects are Trackers.
user_sessions_tracker = stats["sessions"]
engagement_stats = stats["engagement"]

engagement_stats.read()
```

Here, we're reading the `engagement` table; the result might look like this :

```
          date   dau    wau     mau   engagement
0   2017-02-28    25   85.0    99.0     0.252525
1   2017-03-01    24   79.0   107.0     0.224299
2   2017-03-02    15   76.0   114.0     0.131579
3   2017-03-03    20   74.0   117.0     0.170940
4   2017-03-04     3   68.0   122.0     0.024590
```


## Statistic : user sessions

Aggregating user events into sessions provides information on how long users spend on your
product, when they use it, and whether they're regular or sporadic users. You can generate this
table by calling

```python
stats.sessions()
```

You can pass `clean=True` as an argument to this method if you wish to start with a clean slate and
delete the existing table, if it exists. Otherwise, this call will continue filling in the table
from wherever it was left off during its last calculation.

This table can be accessed using `stats["sessions"]`. It looks like this :

```
                     timestamp   user_id    duration   total_events
0   2017-04-11 17:13:04.517904    162824    8.450000              4
1   2017-04-11 18:04:13.741633    159981    1.183333              3
2   2017-04-11 18:08:59.836780    172605    0.466667              3
3   2017-04-11 18:16:07.004563    183951    0.000000              1
4   2017-04-11 18:22:51.349425         1    0.466667              3
5   2017-04-11 18:27:56.790055    162824    2.616667              3
6   2017-04-11 18:34:28.668608        67   12.116667              8
7   2017-04-11 18:40:34.904814    259024    0.000000              1
8   2017-04-11 18:55:19.153985    251976    0.000000              1
9   2017-04-11 19:24:58.415350    159981    0.100000              3
```

Here, each row represents one user session. We can see who the user was, how long ( in minutes )
their session was, and how many events they performed during the session.

Sessions are defined as a number of events with at most some predetermined time between events. Our
default is thirty minutes; you can pass `duration=60` if you want sessions to be defined as a
sequence of events with no more than one hour between events, for example.


## Statistic : user engagement

User engagement can be measured by a number of metrics. Calling

```python
stats.engagement()
```

will calculate the number of unique users daily, weekly, and monthly, and a metric called
*engagement*, which is the ratio of the daily active users to the monthly active users. This is
also often called *stickiness*.

```
          date   dau    wau     mau   engagement
0   2017-02-28    25   85.0    99.0     0.252525
1   2017-03-01    24   79.0   107.0     0.224299
2   2017-03-02    15   76.0   114.0     0.131579
3   2017-03-03    20   74.0   117.0     0.170940
4   2017-03-04     3   68.0   122.0     0.024590
```

Here, we see that we had 25 unique users on the 28th of February, 24 on the 1st of March, and so on.
For the week ending on 28th of Febrary, there were 85 unique users; for the month ending on that
date, there were 99 unique users. The stickiness, or engagement, on that date, was 25.25%.
Intuitively, this value is the fraction of users that were active in the last thirty days logged in
on that day.

As with `stats.sessions()`, you can pass `clean=True` to `stats.engagement()` to start with a clean,
empty table. You can also pass `start="2017-01-03"`, for example, to start calculating from a given
date ( as this statistic can be slow to calculate ). If you don't pass a start date, the calculation
will start from the last date that's been calculated.

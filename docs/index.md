<img src="https://github.com/cbredev/pawprint/raw/master/docs/images/pawprint.png" width="200px" align="right" />

# pawprint

**pawprint** is a flexible, Pythonic event tracker that allows you to rapidly analyse your data.
It brings together the power of **PostgreSQL** and of **pandas**, with a simple query syntax
partially inspired by **Django**'s great ORM.

Out of the box, pawprint allows you to start tracking user or system events extremely quickly.

- Write events flexibly. No individual field is mandatory; the timestamp is autofilled unless you
pass one; use silent-write-failure mode to get pawprint out of the way when developing or
debugging your application.
- Read stored events straight into a pandas DataFrame for quick analysis. Use pawprint's intuitive
query syntax to pull subsets of your database, including only rows that match your conditions.
Leverage the speed of the database to aggregate and preprocess your data before using pandas to
dive deeply into the analysis.
- Use the default tracker for a generalised tracking setup providing JSON capabilities, or set up
your own schema to exactly fit your use case.


## Quick-start

See the [quick-start](https://github.com/cbredev/pawprint/blob/master/README.md).


## Installation

When the first major version is released, pawprint will appear on PyPI. Until then, you can
install the package by calling
```bash
pip install git+https://github.com/cbredev/pawprint.git
```


## Contributing

[Pull requests](https://github.com/cbredev/pawprint/pulls) are very welcome. The design
philosophy is to have a very flexible tool for tracking and analysing all sorts of events.
With that being said, pawprint is being developed with a specific application in mind,
and so please [get in touch](quentincaudron@gmail.com) about developing new features first !


## Support

Feel free to open issues on the [Github repository](https://github.com/cbredev/pawprint/issues).


## License

pawprint is licensed under the [MIT License](https://en.wikipedia.org/wiki/MIT_License).


## Dependencies

pawprint works with Python 2.7+ and Python 3.4+.

- `pandas` >= 0.19
- `psycopg2` >= 2.4
- `sqlalchemy` >= 1.0


## Running tests

We use `pytest`. From the root directory, you can call
```bash
coverage run --source pawprint -m pytest tests -v
```


## Why pawprint ?

pawprint is open-sourced and MIT-licensed. The development of pawprint came about to fill a niche.
With complex questions about the behaviour of our users, we were after a package that would enable
us to track information that didn't necessarily fit into a fixed schema ( and that wasn't just
counting occurrences of events in the form of "metrics" ). There seemed to be very little out there
that could be integrated into our Django codebase quickly, that didn't place additional
requirements on infrastructure in the form of a daemon or service, and that would then allow us to
access our data conveniently for analysis.

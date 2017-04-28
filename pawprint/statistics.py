import numpy as np
import pandas as pd
from datetime import timedelta
from sqlalchemy.exc import ProgrammingError

from pawprint import Tracker


class Statistics(object):
    """
    This class interfaces with an existing Tracker and calculated derived statistics.
    """

    def __init__(self, tracker):

        # Save the tracker
        self.tracker = tracker

    def __getitem__(self, tracker):
        """Overload the [] operator."""

        return Tracker(db=self.tracker.db, table="{}__{}".format(self.tracker.table, tracker))

    def sessions(self, duration=30, clean=False):
        """Create a table of user sessions."""

        # Create a tracker for basic interaction
        stats = self["sessions"]

        # If we're starting clean, delete the table
        if clean:
            stats.drop_table()

        # Determine whether the stats table exists and contains data, or if we should create one
        try:  # if this passes, the table exists and may contain data
            last_entry = pd.read_sql(
                "SELECT timestamp FROM {} ORDER BY timestamp DESC LIMIT 1".format(stats.table),
                self.tracker.db
            ).values[0]
        except ProgrammingError:  # otherwise, the table doesn't exist
            last_entry = None

        # Query : what's the final time we have a session duration for ?
        query = "SELECT DISTINCT({}) FROM {}".format(self.tracker.user_field, self.tracker.table)
        if last_entry:
            query += " WHERE {} > '{}'".format(self.tracker.timestamp_field, last_entry[0])

        # Get the list of unique users since the last data we've tracked
        try:
            users = pd.read_sql(query, self.tracker.db)[self.tracker.user_field].values
        except IndexError:  # no users since the last recorded session
            return

        # Query : the timestamp and user for all events since the last recorded session start
        query = "SELECT {}, {} FROM {}".format(self.tracker.user_field,
                                               self.tracker.timestamp_field,
                                               self.tracker.table)
        if last_entry:
            query += " WHERE {} > '{}'".format(self.tracker.timestamp_field, last_entry[0])

        # Pull the time-series
        events = pd.read_sql(query, self.tracker.db)

        # Session durations DataFrame
        session_data = pd.DataFrame()

        # For each user, calculate session durations
        for user in users:

            # Get the user's time series
            user_events = events[events[self.tracker.user_field] == user].sort_values(
                self.tracker.timestamp_field)
            user_times = user_events[self.tracker.timestamp_field]

            # Index the final elements of each session
            final_events = np.where(user_times.diff().dt.seconds / 60 > duration)[0]
            #final_events[0] = True  # first known event always starts a session

            # Identify times where the user has finished a session
            # The zeroth "session" finished at -1; the last session finishes at the end
            end = len(final_events)
            breaks = np.insert(final_events, [0, end], [0, len(user_times)])

            # Calculate session durations
            user_durations = []
            for i, j in zip(breaks[:-1], breaks[1:]):
                user_durations.append((user_times.iloc[j-1] - user_times.iloc[i]).seconds / 60)

            # Write session durations to the DataFrame
            user_session_data = pd.DataFrame({
                "timestamp": user_times.iloc[breaks[:-1]].values,
                "user_id": [user] * len(user_durations),
                "duration": user_durations,
                "total_events": np.diff(breaks)
            })
            session_data = session_data.append(user_session_data, ignore_index=True)

        # Write the session durations to the database
        session_data[["timestamp", "user_id", "duration", "total_events"]].sort_values(
            "timestamp").to_sql(stats.table, stats.db, if_exists="append", index=False)

    def engagement(self, clean=False, start=None, min_sessions=3):
        """Calculates the daily and monthly average users, and the stickiness as the ratio."""

        # Create a tracker for basic interaction
        stats = self["engagement"]

        # If we're starting clean, delete the table
        if clean:
            stats.drop_table()

        # Determine whether the stats table exists and contains data, or if we should create one
        try:  # if this passes, the table exists and may contain data
            last_entry = pd.read_sql(
                "SELECT date FROM {} ORDER BY date DESC LIMIT 1".format(stats.table),
                self.tracker.db
            ).values[0]
        except ProgrammingError:  # otherwise, the table doesn't exist
            last_entry = None

        # If a start_date isn't passed, start from the last known date, or from the beginning
        if not start:
            start = last_entry[0] + timedelta(days=1) if last_entry else "1900-01-01"

        # If we're also calculating by imposing a minimum number of events per user
        if min_sessions:
            # Count the number of rows per user in the sessions table
            session_counts = self["sessions"].read().groupby(self.tracker.user_field).count()

            # Select the active users where there are at least min_sessions rows per user
            active_users = session_counts[session_counts["duration"] >= min_sessions].index
            active_users = [str(user) for user in active_users]

            # If there are no users that qualify, turn off min_sessions calculations
            if not len(active_users):
                min_sessions = 0

        # DAU : daily active users
        stickiness = self["sessions"].count("DISTINCT({})".format(self.tracker.user_field),
                                            timestamp__gt=start)
        if not len(stickiness):  # if this has been run too recently, do nothing
            return
        stickiness.rename(columns={"count": "dau", "datetime": "timestamp"}, inplace=True)
        stickiness.index = stickiness["timestamp"].dt.date
        stickiness.drop("timestamp", axis=1, inplace=True)

        # Calculate DAU for active users if requested
        if min_sessions:
            active_users_query = {"{}__in".format(self.tracker.user_field): list(active_users)}
            active_dau = self["sessions"].count(
                "DISTINCT({})".format(self.tracker.user_field), timestamp__gt=start, **active_users_query
            )
            active_dau.index = active_dau["datetime"]
            #active_dau["count"]
            stickiness["dau_active"] = active_dau["count"]
            stickiness.dau_active = stickiness.dau_active.fillna(0).astype(int)

        # Weekly and monthly average users
        stickiness["wau"] = np.nan
        stickiness["mau"] = np.nan

        if min_sessions:
            stickiness["wau_active"] = np.nan
            stickiness["mau_active"] = np.nan

        # Calculate weekly and monthly average users
        for date in stickiness.index:
            weekly = self["sessions"].read("DISTINCT({})".format(self.tracker.user_field),
                                           timestamp__gt=date-timedelta(days=6),
                                           timestamp__lte=date+timedelta(days=1)).count()
            monthly = self["sessions"].read("DISTINCT({})".format(self.tracker.user_field),
                                            timestamp__gt=date-timedelta(days=29),
                                            timestamp__lte=date+timedelta(days=1)).count()

            # Calculate WAU and MAU for active users only if requested
            if min_sessions:
                weekly_active = self["sessions"].read("DISTINCT({})".format(self.tracker.user_field),
                                                      timestamp__gt=date-timedelta(days=6),
                                                      timestamp__lte=date+timedelta(days=1),
                                                      **active_users_query).count()
                monthly_active = self["sessions"].read("DISTINCT({})".format(self.tracker.user_field),
                                                       timestamp__gt=date-timedelta(days=29),
                                                       timestamp__lte=date+timedelta(days=1),
                                                       **active_users_query).count()

                stickiness.loc[date, "wau_active"] = weekly_active.iloc[0]
                stickiness.loc[date, "mau_active"] = monthly_active.iloc[0]

            stickiness.loc[date, "wau"] = weekly.iloc[0]
            stickiness.loc[date, "mau"] = monthly.iloc[0]

        # Calculate engagement as DAU / MAU
        stickiness["engagement"] = stickiness.dau / stickiness.mau
        if min_sessions:
            stickiness["engagement_active"] = stickiness.dau_active / stickiness.mau_active

        # Active user counts should be ints
        stickiness.wau = stickiness.wau.astype(int)
        stickiness.mau = stickiness.mau.astype(int)
        if min_sessions:
            stickiness.wau_active = stickiness.wau_active.astype(int)
            stickiness.mau_active = stickiness.mau_active.astype(int)

        # Write the engagement data to the database
        stickiness.sort_index().to_sql(stats.table, stats.db, if_exists="append")

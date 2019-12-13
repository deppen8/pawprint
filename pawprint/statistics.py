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

    def sessions(self, duration=30, clean=False, event_id_col="id"):
        """Create a table of user sessions."""

        # Create a tracker for basic interaction
        stats = self["sessions"]

        # Create a tracker for mapping events to sessions
        event_session_map = self["event_session_map"]

        # If we're starting clean, delete the table
        if clean:
            stats.drop_table()
            event_session_map.drop_table()

        # Determine whether the stats table exists and contains data, or if we should create one
        try:  # if this passes, the table exists and may contain data
            last_entry = pd.read_sql(
                "SELECT timestamp FROM {} ORDER BY timestamp DESC LIMIT 1".format(
                    event_session_map.table
                ),
                self.tracker.db,
            ).loc[0, "timestamp"]
        except ProgrammingError:  # otherwise, the table doesn't exist
            last_entry = None

        # Query : what's the final time we have a session duration for ?
        query = "SELECT DISTINCT({}) FROM {}".format(self.tracker.user_field, self.tracker.table)
        if last_entry:
            query += " WHERE {} > %(last_entry)s".format(self.tracker.timestamp_field)
        params = {"last_entry": str(last_entry)}

        # Get the list of unique users since the last data we've tracked
        users = pd.read_sql(query, self.tracker.db, params=params)[self.tracker.user_field].values

        if len(users) == 0:
            return

        # Query : the timestamp and user for all events since the last recorded session start
        query = "SELECT {}, {}, {} FROM {}".format(
            event_id_col, self.tracker.user_field, self.tracker.timestamp_field, self.tracker.table
        )
        if last_entry:
            query += " WHERE {} > %(last_entry)s".format(self.tracker.timestamp_field)

        # Pull the time-series
        events = pd.read_sql(query, self.tracker.db, params=params)

        # Session durations DataFrame
        session_data = pd.DataFrame()
        event_session_map_data = pd.DataFrame()

        # For each user, calculate session durations
        for user in users:

            # Get the user's time series
            user_events = events[events[self.tracker.user_field] == user].sort_values(
                self.tracker.timestamp_field
            )
            user_times = user_events[self.tracker.timestamp_field]

            # Index the final elements of each session
            time_between = user_times.diff()  # look at the time between events
            time_between.iloc[0] = timedelta(minutes=0)  # fix NaT
            final_events = np.where(time_between.dt.seconds / 60 > duration)[0]

            # Identify times where the user has finished a session
            # The zeroth "session" finished at -1; the last session finishes at the end
            end = len(final_events)
            breaks = np.insert(final_events, [0, end], [0, len(user_times)])

            # Calculate session durations
            user_durations = []
            for i, j in zip(breaks[:-1], breaks[1:]):
                user_durations.append((user_times.iloc[j - 1] - user_times.iloc[i]).seconds / 60)

            # Write session durations to the DataFrame
            user_session_data = pd.DataFrame(
                {
                    "timestamp": user_times.iloc[breaks[:-1]].values,
                    "user_id": [user] * len(user_durations),
                    "duration": user_durations,
                    "total_events": np.diff(breaks),
                }
            )

            session_starts = user_session_data["timestamp"].sort_values()
            session_ends = pd.concat(
                [user_session_data["timestamp"].sort_values().iloc[1:], pd.Series(user_times.max())]
            ).reset_index(drop=True)
            session_idxs = np.searchsorted(
                session_ends.sort_values(), user_events[self.tracker.timestamp_field]
            )
            user_events["session_timestamp"] = session_starts[session_idxs].values
            event_session_map_data = event_session_map_data.append(
                user_events.loc[:, ["id", "user_id", "timestamp", "session_timestamp"]],
                ignore_index=True,
            )

            session_data = session_data.append(user_session_data, ignore_index=True)

        # Write the session durations to the database
        session_data[["timestamp", "user_id", "duration", "total_events"]].sort_values(
            "timestamp"
        ).to_sql(stats.table, stats.db, if_exists="append", index=False)

        # Write event/session lookup table to the database
        event_session_map_data = event_session_map_data.rename(columns={event_id_col: "event_id"})
        event_session_map_data[
            ["event_id", "user_id", "timestamp", "session_timestamp"]
        ].sort_values("session_timestamp").to_sql(
            event_session_map.table, event_session_map.db, if_exists="append", index=False
        )

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
                "SELECT timestamp FROM {} ORDER BY timestamp DESC LIMIT 1".format(stats.table),
                self.tracker.db,
            ).loc[0, "timestamp"]
        except ProgrammingError:  # otherwise, the table doesn't exist
            last_entry = None

        # If a start_date isn't passed, start from the last known date, or from the beginning
        if not start:
            if last_entry:
                start = last_entry + timedelta(days=1)
            else:
                start = "1900-01-01"  # datetime(year=1900, month=1, day=1).date()

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
        stickiness = self["sessions"].count(
            "DISTINCT({})".format(self.tracker.user_field), timestamp__gt=start
        )
        if not len(stickiness):  # if this has been run too recently, do nothing
            return
        stickiness.rename(columns={"count": "dau", "datetime": "timestamp"}, inplace=True)
        stickiness.index = pd.to_datetime(stickiness["timestamp"])
        stickiness.drop("timestamp", axis=1, inplace=True)
        stickiness = stickiness.resample("D").sum().fillna(0).astype(int)

        # Calculate DAU for active users if requested
        if min_sessions:
            active_users_query = {"{}__in".format(self.tracker.user_field): list(active_users)}
            active_dau = self["sessions"].count(
                "DISTINCT({})".format(self.tracker.user_field),
                timestamp__gt=start,
                **active_users_query
            )
            active_dau.index = pd.to_datetime(active_dau["datetime"])
            active_dau = active_dau.resample("D").sum().fillna(0).astype(int)
            stickiness["dau_active"] = active_dau["count"]

        # Weekly and monthly average users
        stickiness["wau"] = np.nan
        stickiness["mau"] = np.nan

        if min_sessions:
            stickiness["wau_active"] = np.nan
            stickiness["mau_active"] = np.nan

        # Calculate weekly and monthly average users
        for date in stickiness.index:
            weekly = (
                self["sessions"]
                .read(
                    "DISTINCT({})".format(self.tracker.user_field),
                    timestamp__gt=date - timedelta(days=6),
                    timestamp__lte=date + timedelta(days=1),
                )
                .count()
            )
            monthly = (
                self["sessions"]
                .read(
                    "DISTINCT({})".format(self.tracker.user_field),
                    timestamp__gt=date - timedelta(days=29),
                    timestamp__lte=date + timedelta(days=1),
                )
                .count()
            )

            # Calculate WAU and MAU for active users only if requested
            if min_sessions:
                weekly_active = (
                    self["sessions"]
                    .read(
                        "DISTINCT({})".format(self.tracker.user_field),
                        timestamp__gt=date - timedelta(days=6),
                        timestamp__lte=date + timedelta(days=1),
                        **active_users_query
                    )
                    .count()
                )
                monthly_active = (
                    self["sessions"]
                    .read(
                        "DISTINCT({})".format(self.tracker.user_field),
                        timestamp__gt=date - timedelta(days=29),
                        timestamp__lte=date + timedelta(days=1),
                        **active_users_query
                    )
                    .count()
                )

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

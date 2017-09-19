from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pawprint import Tracker, Statistics


db = "postgresql://postgres@localhost:5432/pawprint_test_db"
table = "pawprint_test_statistics_table"


class TestPawprintStatistics(object):

    @classmethod
    def setup_class(cls):
        """If the test table exists because tests previously failed, drop it."""

        # Start with a clean slate
        try:
            pd.io.sql.execute("DROP TABLE {}".format(table), db)
        except:
            pass


        # List of users who performed events
        users = [
            "Frodo",
            "Frodo",
            "Frodo",
            "Frodo",
            "Frodo",
            "Frodo",
            "Gandalf",
            "Gandalf",
            "Frodo",
            "Gandalf",
            "Gandalf",
            "Frodo",
            "Frodo",
            "Frodo",
            "Frodo",
            "Frodo"
        ]

        # List of times ( minutes ) between any event and the first events
        timedeltas = [
            0,
            1,
            2,
            3,
            4,
            5,
            100,
            110,
            120,
            130,
            140,
            1000,
            1001,
            1002,
            1003,
            1004
        ]

        # Create a tracker
        tracker = Tracker(db=db, table=table)
        tracker.create_table()

        # Yesterday morning
        today = datetime.now()
        yesterday = datetime(today.year, today.month, today.day, 9, 0) - timedelta(days=1)


        # Write all events
        for user, delta in zip(users, timedeltas):
            tracker.write(user_id=user, timestamp=yesterday + timedelta(minutes=delta))

        # Save the tracker
        cls.tracker = tracker
        cls.stats = Statistics(tracker)

    @classmethod
    def teardown_class(cls):
        pd.io.sql.execute("DROP TABLE {}".format(table), db)

    def drop_table_before_and_after(statstable):
        def decorator(f):
            def wrapper(self):

                try:
                    pd.io.sql.execute("DROP TABLE {}__{}".format(table, statstable), db)
                except:
                    pass

                f(self)

                try:
                    pd.io.sql.execute("DROP TABLE {}__{}".format(table, statstable), db)
                except:
                    pass

            return wrapper
        return decorator

    @drop_table_before_and_after("sessions")
    def test_sessions(self):
        """Test the calculation of session durations."""

        # Calculate user session durations
        self.stats.sessions(clean=True)

        # Read the results
        sessions = self.stats["sessions"].read()

        # Ground truth
        users = np.array(["Frodo", "Gandalf", "Frodo", "Frodo"])
        durations = np.array([5, 40, 0, 4])
        events = np.array([6, 4, 1, 5])

        assert len(durations) == 4
        assert np.all(sessions[self.tracker.user_field] == users)
        assert np.all(sessions.duration == durations)
        assert np.all(sessions.total_events == events)

        self.stats.sessions(clean=False)
        assert len(self.stats["sessions"].read()) == 5

        # Test that calculating sessions with no new data doesn't error
        self.stats.sessions()

    @drop_table_before_and_after("engagement")
    @drop_table_before_and_after("sessions")
    def test_engagement(self):
        """Test the calculation of user engagement metrics."""

        # Calculate user engagement
        self.stats.sessions(clean=True)
        self.stats.engagement(clean=True, min_sessions=0)

        # Read the results
        stickiness = self.stats["engagement"].read()

        # Ground truth
        dau = np.array([2, 1])
        wau = np.array([2, 2])
        mau = np.array([2, 2])
        engagement = np.array([1, 0.5])

        assert len(engagement) == 2
        assert np.all(stickiness.dau == dau)
        assert np.all(stickiness.wau == wau)
        assert np.all(stickiness.mau == mau)
        assert np.all(stickiness.engagement == engagement)
        assert set(stickiness.columns) == {"timestamp", "dau", "wau", "mau", "engagement"}

        # Now test with a minimum number of sessions
        self.stats.engagement(clean=True, min_sessions=2)
        stickiness = self.stats["engagement"].read()

        # Ground truth
        active = np.array([1, 1])
        engagement_active = np.array([1, 1])

        assert np.all(stickiness.dau_active == active)
        assert np.all(stickiness.wau_active == active)
        assert np.all(stickiness.mau_active == active)
        assert np.all(stickiness.dau == dau)
        assert np.all(stickiness.engagement_active == engagement_active)
        assert set(stickiness.columns) == {"timestamp", "dau", "wau", "mau", "engagement",
                                           "dau_active", "wau_active", "mau_active",
                                            "engagement_active"}

        # Test that running engagements again doesn't error if there's no new data
        self.stats.engagement()

        # Test with too large a minimum sessions parameter
        self.stats.engagement(clean=True, min_sessions=20)
        stickiness = self.stats["engagement"].read()
        assert len(stickiness) == 2
        assert set(stickiness.columns) == {"timestamp", "dau", "wau", "mau", "engagement"}

        # Try again with append-only
        self.stats.engagement(clean=False)
        stickiness = self.stats["engagement"].read()
        assert len(stickiness.columns) == 5
        assert len(stickiness) == 2

        self.stats.engagement(clean=True, min_sessions=2)
        stickiness = self.stats["engagement"].read()
        assert len(stickiness) == 2
        assert len(stickiness.columns) == 9

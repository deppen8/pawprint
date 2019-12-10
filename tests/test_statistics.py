import numpy as np

import pawprint


def test_sessions(pawprint_default_statistics_tracker):
    """Test the calculation of session durations."""

    tracker = pawprint_default_statistics_tracker
    stats = pawprint.Statistics(tracker)

    # Calculate user session durations
    stats.sessions()

    # Read the results
    sessions = stats["sessions"].read()

    # Expected values
    users = np.array(["Frodo", "Gandalf", "Frodo", "Frodo"])
    durations = np.array([5, 40, 0, 4])
    events = np.array([6, 4, 1, 5])

    print(sessions[tracker.user_field])

    assert np.all(sessions[tracker.user_field] == users)
    assert np.all(sessions.duration == durations)
    assert np.all(sessions.total_events == events)

    stats.sessions(clean=False)
    assert len(stats["sessions"].read()) == 5

    # Test that calculating sessions with no new data doesn't error
    stats.sessions()


def test_engagement_metrics(pawprint_default_statistics_tracker):
    """Test the calculation of user engagement metrics."""

    tracker = pawprint_default_statistics_tracker
    stats = pawprint.Statistics(tracker)

    # Calculate user engagement
    stats.sessions()
    stats.engagement(min_sessions=0)

    # Read the results
    stickiness = stats["engagement"].read()

    # Expected values
    dau = np.array([2, 1])
    wau = np.array([2, 2])
    mau = np.array([2, 2])
    engagement = np.array([1, 0.5])

    assert np.all(stickiness.dau == dau)
    assert np.all(stickiness.wau == wau)
    assert np.all(stickiness.mau == mau)
    assert np.all(stickiness.engagement == engagement)
    assert set(stickiness.columns) == {"timestamp", "dau", "wau", "mau", "engagement"}


def test_engagement_min_sessions(pawprint_default_statistics_tracker):

    tracker = pawprint_default_statistics_tracker
    stats = pawprint.Statistics(tracker)
    stats.sessions()

    # Now test with a minimum number of sessions
    stats.engagement(min_sessions=2)
    stickiness = stats["engagement"].read()

    # Ground truth
    active = np.array([1, 1])
    engagement_active = np.array([1, 1])
    dau = np.array([2, 1])

    assert np.all(stickiness.dau_active == active)
    assert np.all(stickiness.wau_active == active)
    assert np.all(stickiness.mau_active == active)
    assert np.all(stickiness.dau == dau)
    assert np.all(stickiness.engagement_active == engagement_active)
    assert set(stickiness.columns) == {
        "timestamp",
        "dau",
        "wau",
        "mau",
        "engagement",
        "dau_active",
        "wau_active",
        "mau_active",
        "engagement_active",
    }

    # Test that running engagements again doesn't error if there's no new data
    stats.engagement()


def test_engagement_too_many_min_sessions(pawprint_default_statistics_tracker):
    tracker = pawprint_default_statistics_tracker
    stats = pawprint.Statistics(tracker)
    stats.sessions()

    # Test with too large a minimum sessions parameter
    stats.engagement(min_sessions=20)
    stickiness = stats["engagement"].read()
    assert len(stickiness) == 2
    assert set(stickiness.columns) == {"timestamp", "dau", "wau", "mau", "engagement"}


def test_engagement_append_mode(pawprint_default_statistics_tracker):
    tracker = pawprint_default_statistics_tracker
    stats = pawprint.Statistics(tracker)
    stats.sessions()

    stats.engagement(min_sessions=20)

    # Try again with append-only
    stats.engagement(clean=False)
    stickiness = stats["engagement"].read()
    assert len(stickiness.columns) == 5
    assert len(stickiness) == 2

    stats.engagement(clean=True, min_sessions=2)
    stickiness = stats["engagement"].read()
    assert len(stickiness) == 2
    assert len(stickiness.columns) == 9

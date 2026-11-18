import unittest
from types import SimpleNamespace
from unittest.mock import patch
from train_motion import HomeTracker, Journey, Throttle


class MotionTests(unittest.TestCase):
    def test_sensor_requires_departure_and_rejects_bounce(self):
        tracker = HomeTracker()
        self.assertFalse(tracker.update(True, 0))
        self.assertFalse(tracker.update(True, 1))
        tracker.update(False, 2)
        tracker.update(True, 2.01)
        self.assertFalse(tracker.update(True, 3))
        tracker.update(False, 4)
        tracker.update(False, 4.1)
        tracker.update(True, 5)
        self.assertTrue(tracker.update(True, 5.1))

    def journey(self, mode, sensor=None, timeout=60):
        now = [0]
        class Stop:
            def is_set(self):
                return False
            def wait(self, delay):
                now[0] += delay
        args = SimpleNamespace(journey_timeout=timeout, duty=.6, creep_duty=.4,
                               ramp_seconds=2, visible_seconds=3, idle_seconds=5)
        throttle = Throttle()
        outputs = SimpleNamespace(home=lambda: sensor)
        with patch('train_motion.time.monotonic', lambda: now[0]):
            j = Journey(outputs, Stop(), throttle, args)
            try:
                j.run(mode)
            finally:
                self.assertEqual(throttle.get(), 0)
        return j, now[0]

    def test_pass_and_town_stop_return_home(self):
        passing, pass_time = self.journey('pass')
        stopping, stop_time = self.journey('stop')
        self.assertTrue(passing.parked)
        self.assertTrue(stopping.parked)
        self.assertGreater(stop_time, pass_time + 5)

    def test_stuck_sensor_times_out_and_stops(self):
        for sensor in (True, False):
            with self.assertRaises(RuntimeError):
                self.journey('pass', sensor, timeout=1)


if __name__ == '__main__':
    unittest.main()

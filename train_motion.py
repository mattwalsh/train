"""Real-time train journeys. No GPIO initialization on import."""
import logging
import threading
import time


class Throttle:
    def __init__(self):
        self.lock = threading.Lock()
        self.value = 0.0

    def set(self, value):
        with self.lock:
            self.value = value

    def get(self):
        with self.lock:
            return self.value


class HomeTracker:
    """Require debounced departure before accepting a return to home."""
    def __init__(self, debounce=0.05):
        self.debounce = debounce
        self.candidate = None
        self.since = 0
        self.departed = False

    def update(self, home, now):
        if home != self.candidate:
            self.candidate, self.since = home, now
        if now - self.since < self.debounce:
            return False
        if home is False:
            self.departed = True
        return home is True and self.departed


class Journey:
    def __init__(self, outputs, stop, throttle, args):
        self.outputs, self.stop, self.throttle, self.args = outputs, stop, throttle, args
        self.tracker = HomeTracker()
        self.started = time.monotonic()
        self.deadline = self.started + args.journey_timeout
        self.parked = False
        self.phase = 'starting'

    def tick(self):
        if self.stop.is_set():
            return False
        now = time.monotonic()
        if now >= self.deadline:
            raise RuntimeError('Train home timeout; motor stopped, inspection required')
        home = self.outputs.home()
        if home is None:
            # Dry-run sensor only: departure at 0.5s, return after 12s of motion.
            home = self.motion_time < 0.5 or self.motion_time >= 12
        if self.tracker.update(home, now):
            self.parked = True
            self.throttle.set(0)
            logging.info('Train parked at home (phase=%s)', self.phase)
            return False
        return True

    @property
    def motion_time(self):
        return self.travel

    def hold(self, seconds, begin, end=None):
        self.phase_started = time.monotonic()
        last = self.phase_started
        while True:
            now = time.monotonic()
            if self.throttle.get() > 0:
                self.travel += now - last
            last = now
            if not self.tick():
                return False
            elapsed = now - self.phase_started
            fraction = min(1.0, elapsed / seconds) if seconds else 1
            self.throttle.set(begin if end is None else begin + (end - begin) * fraction)
            if elapsed >= seconds:
                return True
            self.stop.wait(0.01)

    def run(self, mode):
        self.travel = 0
        logging.info('Train journey: %s', mode)
        try:
            # If initially away from home, first recover to home, without a town stop.
            if self.outputs.home() is False:
                logging.info('Train away from home; returning before next scene')
                mode = 'pass'
            self.phase = 'accelerating'
            speed = self.args.duty if mode == 'pass' else self.args.creep_duty
            if not self.hold(self.args.ramp_seconds, 0, speed):
                return
            if mode == 'stop':
                self.phase = 'approaching town stop'
                if not self.hold(self.args.visible_seconds, speed):
                    return
                self.phase = 'braking in town'
                if not self.hold(self.args.ramp_seconds, speed, 0):
                    return
                self.phase = 'idling (sound placeholder)'
                logging.info(self.phase)
                if not self.hold(self.args.idle_seconds, 0):
                    return
                self.phase = 'whistle (sound placeholder)'
                logging.info(self.phase)
                if not self.hold(1, 0):
                    return
                self.phase = 'departing town'
                if not self.hold(self.args.ramp_seconds, 0, self.args.duty):
                    return
            self.phase = 'returning home'
            while self.hold(0.1, self.args.duty):
                pass
        finally:
            self.throttle.set(0)


def train_worker(outputs, stop, throttle, args, rng):
    try:
        while not stop.is_set():
            mode = rng.choice(('pass', 'stop')) if args.train_mode == 'mixed' else args.train_mode
            Journey(outputs, stop, throttle, args).run(mode)
            stop.wait(args.park_seconds)
    finally:
        throttle.set(0)

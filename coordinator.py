#!/usr/bin/env python3
"""Winter village coordinator; dry-run unless --hardware is supplied."""
import argparse
import datetime
import logging
import random
import signal
import threading
import time
from train_motion import Throttle, train_worker

PINS = {'motor': 4, 'right_house': 5, 'left_house': 6,
        'horizon': 22, 'sky': 27, 'church': 23}
HOME_PIN = 17


class Outputs:
    def __init__(self, hardware=False):
        self.gpio = None
        self.states = {}
        self.lock = threading.Lock()
        if hardware:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            try:
                for pin in PINS.values():
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(HOME_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except BaseException:
                GPIO.cleanup()
                raise

    def set(self, name, on):
        with self.lock:
            if self.states.get(name) == on:
                return
            if self.gpio:
                self.gpio.output(PINS[name], on)
            self.states[name] = on
            logging.log(logging.DEBUG if name == 'motor' else logging.INFO,
                        '%s = %s', name, on)

    def home(self):
        # Active-low inferred from the original C++ controller; verify physically.
        return None if self.gpio is None else not self.gpio.input(HOME_PIN)

    def close(self):
        try:
            for name in PINS:
                self.set(name, False)
        finally:
            if self.gpio:
                self.gpio.cleanup()


class Clock:
    def __init__(self, start, rate):
        self.start, self.rate = start, rate
        self.origin = time.monotonic()

    def now(self):
        return self.start + datetime.timedelta(
            seconds=(time.monotonic() - self.origin) * self.rate)


def motor_worker(outputs, stop, throttle, period):
    """Real-time pulses, independent of the accelerated calendar."""
    try:
        while not stop.is_set():
            duty = throttle.get()
            if duty == 0:
                outputs.set('motor', False)
                stop.wait(0.02)
                continue
            outputs.set('motor', True)
            if stop.wait(period * duty):
                break
            if duty < 1:
                outputs.set('motor', False)
                stop.wait(period * (1 - duty))
    finally:
        outputs.set('motor', False)


def scene_worker(outputs, stop, clock, rng):
    evening = None
    house_times = None
    next_storm = time.monotonic() + rng.uniform(60, 180)
    storm_until = 0
    next_flash = 0
    flash_until = 0
    last_hour = None
    while not stop.is_set():
        now = clock.now()
        hour = now.hour + now.minute / 60.0 + now.second / 3600.0
        night = hour >= 18 or hour < 7
        # Anchor each night's random schedule to the preceding evening.
        night_date = now.date() - datetime.timedelta(days=1 if hour < 7 else 0)
        if evening != night_date:
            evening = night_date
            house_times = [18 + rng.uniform(0, 0.75) for _ in range(2)]
        for name, threshold in zip(('left_house', 'right_house'), house_times):
            outputs.set(name, night and (hour < 7 or hour >= threshold))
        outputs.set('church', now.weekday() == 6 and (9 <= hour < 12 or night))
        outputs.set('horizon', 6 <= hour < 8 or 17 <= hour < 19)
        real = time.monotonic()
        # Weather and motor durations use real seconds so acceleration cannot
        # turn a visible flash or a train journey into an imperceptible event.
        if real >= next_storm:
            storm_until = real + rng.uniform(15, 35)
            next_storm = storm_until + rng.uniform(60, 180)
            logging.info('Rain scene started (no rain audio configured)')
        if real < storm_until and real >= next_flash:
            flash_until = real + rng.uniform(0.05, 0.15)
            next_flash = real + rng.uniform(0.2, 3)
        outputs.set('sky', not night or real < flash_until)
        stamp = now.strftime('%a %Y-%m-%d %H')
        if stamp != last_hour:
            logging.info('Village time: %s:00', stamp)
            last_hour = stamp
        stop.wait(0.02)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', action='store_true')
    parser.add_argument('--train', action='store_true', help='enable sensor-guided train journeys')
    parser.add_argument('--rate', type=float, default=120,
                        help='simulated seconds per real second (default 120)')
    parser.add_argument('--start', default='2026-12-06T17:00:00')
    parser.add_argument('--duty', type=float, default=0.6)
    parser.add_argument('--period', type=float, default=0.1, help='motor pulse seconds')
    parser.add_argument('--duration', type=float, default=0, help='real seconds; 0 runs until stopped')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--train-mode', choices=('pass', 'stop', 'mixed'), default='mixed')
    parser.add_argument('--creep-duty', type=float, default=0.4)
    parser.add_argument('--ramp-seconds', type=float, default=2)
    parser.add_argument('--visible-seconds', type=float, default=3,
                        help='travel at creep speed before braking; calibrate on decoration')
    parser.add_argument('--idle-seconds', type=float, default=5)
    parser.add_argument('--park-seconds', type=float, default=30)
    parser.add_argument('--journey-timeout', type=float, default=60)
    args = parser.parse_args()
    import math
    if not all(math.isfinite(v) for v in (args.rate, args.duty, args.period, args.duration)) or args.rate <= 0 or not 0 <= args.duty <= 1 or args.period <= 0 or args.duration < 0:
        parser.error('require finite rate > 0, duty in [0,1], period > 0, duration >= 0')
    if not 0 <= args.creep_duty <= args.duty:
        parser.error('creep duty must be between 0 and cruise duty')
    if not all(math.isfinite(v) and v > 0 for v in
               (args.ramp_seconds, args.visible_seconds, args.idle_seconds,
                args.park_seconds, args.journey_timeout)):
        parser.error('journey durations must be finite and positive')
    try:
        start = datetime.datetime.strptime(args.start, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        parser.error('--start must be YYYY-MM-DDTHH:MM:SS')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    stop, throttle = threading.Event(), Throttle()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, frame: stop.set())
    outputs = Outputs(args.hardware)
    threads = []

    def guarded(fn, *params):
        try:
            fn(*params)
        except BaseException:
            logging.exception('Worker failed; stopping all outputs')
            stop.set()

    try:
        workers = [
            (motor_worker, (outputs, stop, throttle, args.period)),
            (scene_worker, (outputs, stop, Clock(start, args.rate), random.Random(args.seed)))]
        if args.train:
            workers.append((train_worker, (outputs, stop, throttle, args, random.Random(args.seed))))
        for fn, params in workers:
            thread = threading.Thread(target=guarded, args=(fn,) + params)
            threads.append(thread)
            thread.start()
        stop.wait(args.duration if args.duration else None)
    finally:
        stop.set()
        for thread in threads:
            if thread.ident is not None:
                thread.join()
        outputs.close()


if __name__ == '__main__':
    main()

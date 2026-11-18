#!/usr/bin/env python3
"""Full-power lap timing between two debounced active-low home arrivals."""
import signal
import time
import RPi.GPIO as GPIO

MOTOR, SENSOR = 4, 17
TIMEOUT = 60.0
stop = False


def request_stop(signum, frame):
    global stop
    stop = True


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, request_stop)
GPIO.setmode(GPIO.BCM)
try:
    GPIO.setup(MOTOR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    initial = GPIO.input(SENSOR)
    print('Initial sensor raw={} (0 assumed home)'.format(initial), flush=True)
    candidate = stable = initial
    since = started = time.monotonic()
    hits = []
    GPIO.output(MOTOR, GPIO.HIGH)
    print('Motor at FULL power (constant HIGH); timeout {}s'.format(TIMEOUT), flush=True)
    while not stop and time.monotonic() - started < TIMEOUT:
        now = time.monotonic()
        raw = GPIO.input(SENSOR)
        if raw != candidate:
            candidate, since = raw, now
            print('raw={} at {:.4f}s'.format(raw, now - started), flush=True)
        if candidate != stable and now - since >= 0.03:
            stable = candidate
            print('stable={} at {:.4f}s'.format(stable, since - started), flush=True)
            if stable == 0:
                hits.append(since)
                print('HOME arrival {} at {:.4f}s'.format(len(hits), since - started), flush=True)
                if len(hits) == 2:
                    GPIO.output(MOTOR, GPIO.LOW)
                    print('FULL LAP: {:.4f} real seconds'.format(hits[1] - hits[0]), flush=True)
                    break
        time.sleep(0.002)
    else:
        print('Stopped by signal or timeout; no complete lap measurement', flush=True)
finally:
    GPIO.output(MOTOR, GPIO.LOW)
    GPIO.cleanup((MOTOR, SENSOR))
    print('Motor OFF; calibration finished', flush=True)

# Python village coordinator

Compatible with Python 3.4+. Existing controllers are left untouched.

Preview only (no GPIO imports or writes):

    python3 coordinator.py --train --duration 60

Control lights on the Pi (motor stays disabled):

    python3 coordinator.py --hardware

Enable motor too, after checking duty/period for this motor:

    python3 coordinator.py --hardware --train --duty 0.1 --period 0.5

Do not run alongside another GPIO controller. Ctrl-C or SIGTERM stops workers,
turns outputs off, and cleans up GPIO. Worker failures also stop all outputs.

Default clock starts Sunday December 6, 2026 at 17:00, at 120x speed
(one village day per 12 real minutes). Override with --start YYYY-MM-DDTHH:MM:SS
and --rate. --seed gives repeatable random schedules.

Initial scene policy (tunable starter choices):
- Houses turn on independently between 18:00 and 18:45; off at 07:00.
- Church lights only on Sunday, during 09:00-12:00 and at night.
- Horizon on 06:00-08:00 and 17:00-19:00; sky on during daytime.
- Rain scenes every 60-180 real seconds, lasting 15-35 seconds, flash sky.
  Rain is currently a visual scene only; audio is not implemented yet.
- Optional train runs for 15 real seconds every 60 seconds. Motor pulse timing
  uses real time, independent of the calendar. Python/Linux scheduling is not
  precision timing; calibrate duty/period physically.

Sensor GPIO 17 is configured with pull-up; active-low is inferred from the
old C++ code and not physically verified. Timed runs do NOT yet park the train
in its tunnel. The sensor is logged after each run only.

BCM pins: motor 4, right house 5, left house 6, horizon 22, sky 27, church 23.

Architecture: one motor thread, one scene thread, locked output writes and a
shared shutdown event. Scene effects use deadlines rather than blocking sleeps,
so lightning continues during a train run. Audio can later be a managed player
process; no need to block either worker waiting for a sound to finish.

## Sensor-guided journeys (replaces the initial timed-run policy above)

Defaults now use the observed smooth cruise setting: --duty 0.6 --period 0.1.
--train-mode pass accelerates, passes through, and stops on home sensor return.
--train-mode stop ramps to --creep-duty 0.4, travels for --visible-seconds 3,
brakes over --ramp-seconds 2, pauses --idle-seconds 5, leaves a one-second
whistle placeholder, then accelerates to cruise and returns home.
--train-mode mixed (default) randomly selects either journey.
All movement, ramp, idle, and whistle timing is real seconds, regardless of --rate.
The town stop's position and minimum useful creep duty MUST be calibrated on the
physical layout; only the hidden home position has a sensor. Audio is not played.

Home input is debounced 50ms; a departure must precede an accepted return.
If initially away from home, the train first returns home without a town stop.
Any home return ends a journey immediately, even if town-stop timing is too long.
--journey-timeout 60 stops the whole coordinator if the sensor never returns.
--park-seconds 30 controls the wait between journeys. Parking cuts motor power
on sensor arrival; gradual braking is for the visible town stop, since there is
no approach sensor to predict arrival at home. Sensor polarity and coast distance
still require hardware verification. Dry-run simulates departure/return.

Run motion tests: python3 -m unittest -v test_train_motion

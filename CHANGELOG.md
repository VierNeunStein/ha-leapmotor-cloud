# Changelog

## 1.0.0

First release.

- Asynchronous client for the Leapmotor international cloud with stored and refreshed
  sessions, login budget, request pacing and certificate pinning.
- Sensors, binary sensors, lock, climate, covers (windows, sunshade, tailgate), switches,
  numbers, selects, time entities, buttons, device tracker, vehicle picture and software update.
- Vehicle PIN stored per vehicle and used automatically; a rejected PIN is never repeated.
- Adaptive polling, optional wallbox power trigger, daily request limit and error back-off.
- Actions for climate, charging schedule, climate timers, vehicle preparation, destinations and
  raw commands.
- Animated dashboard cards and a dashboard strategy.
- Real vehicle pictures: the app's picture package (model and colour of the car) is downloaded
  once, stored locally and stacked by the vehicle and status cards (doors, tailgate, windows,
  charging animation); option `image` for an own picture.
- Simulated vehicle for trying everything without an account.
- Repairs for a changed server certificate, a rejected PIN, a rejected app certificate and
  session conflicts; redacted diagnostics.
- Blueprint for charging with solar surplus.

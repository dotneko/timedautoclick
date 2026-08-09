# timedautoclick

A python script that autoclicks at a specified time adjusted with an offset

## Requirements

- Targeted for use on macOS
- Requires `cliclick` to be installed. See https://github.com/BlueM/cliclick

## Usage

```
usage: timed_autoclick.py [-h] [-t TIME] [-o OFFSET] [-r REPEAT] [--no-progress] [--sound]
                          [cliclick_args ...]

Countdown timer with cliclick execution and offset support

positional arguments:
  cliclick_args        Arguments to pass to cliclick (default: dc:.)

options:
  -h, --help           show this help message and exit
  -t, --time TIME      Target time in hh:mm:ss format (default: 07:00:00)
  -o, --offset OFFSET  Offset in milliseconds (positive = before, negative = after). Default: 0
  -r, --repeat REPEAT  Repeat cliclick number of times (default: 1)
  --no-progress        Hide progress bar
  --sound              Play sound alert when time is reached

    Examples:
    timed_autoclick.py -t 14:30:00                    # Run at 2:30 PM
    timed_autoclick.py -t 14:30:00 -o 500             # Run 500ms before 2:30 PM
    timed_autoclick.py -t 14:30:00 -o -200            # Run 200ms after 2:30 PM
    timed_autoclick.py -t 14:30:00 "m" "100,100"      # Click at position 100,100 at 2:30 PM
    timed_autoclick.py -t 14:30:00 -o 1000 "m" "100,100"  # Click 1 second before 2:30 PM
```

## Usage with `config.sample`

```
source config.sample
timed_autoclick -o 500 -r 3 $START $CLOSE
```
#!/usr/bin/env python3

import datetime, json, getopt, os, subprocess, sys, time, urllib.request

def die(msg, exit_code=1):
  print(msg, file=sys.stderr)
  sys.exit(exit_code)

def get_token():
    if "CLAUDE_CODE_TOKEN" in os.environ:
      return os.environ["CLAUDE_CODE_TOKEN"]

    if sys.platform == "darwin":  # macos
      cmd = ("security", "find-generic-password", "-s", "Claude Code-credentials", "-w")
    else:  # assuming linux
      cmd = ("secret-tool", "lookup", "service", "Claude Code-credentials")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    if p.returncode:
      die(" ".join("%r" % s for s in cmd) + (" exited with code " + str(p.returncode)) if p.returncode > 0 else (" killed by signal " + str(-p.returncode)))
    try: return json.loads(stdout)["claudeAiOauth"]["accessToken"]
    except Exception as e: die("interpreting the API reply failed: " + str(e))

def fetch(token):
    u = "https://api.anthropic.com/api/oauth/usage"
    try:
        req = urllib.request.Request(
            u,
            headers={
                "Authorization": "Bearer " + token,
                "anthropic-beta": "oauth-2025-04-20",
                "User-Agent": "claude-code/2.0.31",
            },
        )
        json_reply = urllib.request.urlopen(req)
    except Exception as e: die("querying %s failed: %s" % (u, e))
    try: return json.load(json_reply)
    except Exception as e: die("parsing error in %s json reply: %s" % (u, e))

NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight" : 8, "nine": 9}

def summarize(key, key_has_duration, util, order, expiration, verbose):
  if expiration is not None:
    expiration = expiration.total_seconds()
    if expiration > 24 * 3600:
      expiration = "%2.1fd" % (expiration / (24 * 3600.0))
    elif expiration > 3600:
      expiration = "%2.1fh" % (expiration / 3600.0)
    elif expiration > 60:
      expiration = "%2.1fm" % (expiration / 60.0)
    else:
      expiration = "%ds" % int(expiration + 0.5)
  if key_has_duration:
    k = key.split("_", 2)
    n, unit = NUMBERS[k[0]], k[1]
    if unit == "hour": mul, suffix = 1, "h"
    elif unit == "day": mul, suffix = 24, "d"
    if verbose == 0:
      return (order, mul * n, len(k), "%2.1f%%↺%s" % (util, expiration))
    label = str(n) + suffix + (" " + k[2] if len(k) > 2 else "")
    return (order, mul * n, len(k), label + " (%s↺) %2.1f%% " % (expiration, util))
  if verbose == 0:
    return (10000, key, 0, "%2.1f%%" % util)
  return (10000, key, 0, key + " %2.1f%%" % util)

def format_timedelta(td):
  s = str(td)
  i = s.find(",")
  if i >= 0: return s[:i]  # "3 days, HH:MM:SS..."
  i = s.find(":")
  h = int(s[:i])
  s = s[i + 1:]
  m = int(s[:s.find(":")])
  return ("%2.1f hours" % (h + m / 60.0)) if h else str(m) + " minutes"

def render(data, verbose):
  if verbose >= 2: return render_verbose(data)
  now = datetime.datetime.now().astimezone()
  out = []
  for k, v in data.items():
    if v is None: continue
    try:
      # five_hour {'utilization': 92.0, 'resets_at': '2026-04-05T20:00:00.394568+00:00'}
      # seven_day {'utilization': 36.0, 'resets_at': '2026-04-11T11:00:00.394589+00:00'}
      dt = datetime.datetime.fromisoformat(v["resets_at"])
      out.append(summarize(k, True, v["utilization"], 0, dt - now, verbose))
    except KeyError: pass
    if k == "extra_usage":
      # {'is_enabled': True, 'monthly_limit': 8500, 'used_credits': 108.0, 'utilization': 1.2705882352941176}
      utilization = v.get("utilization")
      if v["is_enabled"] and utilization is not None: out.append(summarize("extra", False, utilization, 1, None, verbose))
  print(" ".join(x[3] for x in sorted(out)))

def render_verbose(data):
  now = datetime.datetime.now().astimezone()
  for k, v in data.items():
    if v is None:
      print(k, v)
      continue
    try:
      dt = datetime.datetime.fromisoformat(v["resets_at"])
      print(k, "%3.2f%%" % v["utilization"], "resets at", dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"), "in", format_timedelta(dt - now))
    except KeyError: pass
    if k == "extra_usage":
      print(k, ("%3.2f%%" % v["utilization"]) if v["is_enabled"] else "disabled")


USAGE = """
%(prog)s - prints claude tokens usage

options:
  -h  this help
  -v  verbose
"""

def main():
    try: opts = getopt.getopt(sys.argv[1:], "hv")
    except Exception as e: die(str(e) + ", run with -h for help", exit_code=2)
    verbose = 0
    for opt, arg in opts[0]:
      if opt == "-h":
        print(USAGE.strip() % {"prog": sys.argv[0]})
        sys.exit(0)
      elif opt == '-v': verbose += 1
    render(fetch(get_token()), verbose)

if __name__ == "__main__":
    main()

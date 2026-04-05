#!/usr/bin/env python3

import datetime, json, os, subprocess, sys, time, urllib.request

def die(msg):
  print(msg, file=sys.stderr)
  sys.exit(1)

def get_token():
    if "CLAUDE_CODE_TOKEN" in os.environ:
        return os.environ["CLAUDE_CODE_TOKEN"]

    if sys.platform == "darwin":  # macos
        out = subprocess.check_output(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"])
    else:  # assuming linux
        out = subprocess.check_output(["secret-tool", "lookup", "service", "Claude Code-credentials"])
    return json.loads(out)["claudeAiOauth"]["accessToken"]

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

def render(data):
  for k, v in data.items():
    if v is None:
      print(k, v)
      continue
    try:
      # five_hour {'utilization': 92.0, 'resets_at': '2026-04-05T20:00:00.394568+00:00'}
      # seven_day {'utilization': 36.0, 'resets_at': '2026-04-11T11:00:00.394589+00:00'}
      dt_obj = datetime.datetime.fromisoformat(v["resets_at"])
      formatted_date = dt_obj.astimezone().strftime("%Y-%m-%d %H:%M:%S")
      print(k, "%3.2f%%" % v["utilization"], "resets at", formatted_date)
    except KeyError: pass
    if k == "extra_usage":
      # {'is_enabled': True, 'monthly_limit': 8500, 'used_credits': 108.0, 'utilization': 1.2705882352941176}
      print(k, ("%3.2f%%" % v["utilization"]) if v["is_enabled"] else "disabled")

def main():
    try: token = get_token()
    except Exception as e: die("getting api token failed: %s" % e)
    render(fetch(token))

if __name__ == "__main__":
    main()

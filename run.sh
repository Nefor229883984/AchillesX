#!/bin/bash
cd /workspaces/AchillesX
git pull
# Check if max_login.py is running
if pgrep -f max_login.py > /dev/null; then
    echo "ALREADY_RUNNING"
    cat login_state.json 2>/dev/null || echo "no state yet"
else
    echo "STARTING_SCRIPT"
    nohup python3 max_login.py > /tmp/login.log 2>&1 &
    echo "Started PID: $!"
fi

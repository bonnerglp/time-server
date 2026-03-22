#!/usr/bin/env bash

echo "==== SYSTEM OVERVIEW ===="
echo "Raspberry Pi Time Server"

echo
echo "==== ACTIVE SERVICES ===="
systemctl list-units --type=service | grep -E 'chrony|teensy|piksi'

echo
echo "==== LISTENING PORTS ===="
ss -tulnp | grep -E '808|123'

echo
echo "==== CHRONY STATUS ===="
chronyc tracking
chronyc sources -v

echo
echo "==== CRONTAB (pi) ===="
crontab -l

echo
echo "==== PROJECT STRUCTURE ===="
find ~/time-server/snapshot -maxdepth 2 -type d

echo
echo "==== GIT STATUS ===="
cd ~/time-server
git log --oneline -n 3
git status

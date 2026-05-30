#!/usr/bin/env bash
echo '---CONTAINERS---'
docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'
echo '---NETWORKS---'
docker network ls
echo '---FREE PORT CHECK---'
for p in 8000 8010 8090 8088 3100 3200; do
  if ss -tln | grep -q ":$p "; then echo "$p USED"; else echo "$p free"; fi
done
echo '---DISK---'
df -h / | tail -1
echo '---MEM---'
free -h | grep Mem
echo '---DEPLOY DIR---'
ls -la /opt 2>/dev/null | head -20

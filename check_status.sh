#!/bin/bash
     
     echo "Legislature Monitor Status Check"
     echo "-------------------------------"
     echo "Service status:"
     sudo systemctl status legislature-monitor.service | head -n 5
     
     echo -e "\nLast 10 log entries:"
     tail -n 10 ~/legislature-monitor/legislature_monitor.log
     
     echo -e "\nDisk space:"
     df -h | grep -E 'Filesystem|/dev/sda1'
     
     echo -e "\nDownloaded videos:"
     ls -lh ~/legislature-monitor/downloads/ | head -n 10

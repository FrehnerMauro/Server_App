#!/bin/bash
source /Users/maurofrehner/Desktop/Virt/Server_App_2/bin/activate
exec /Users/maurofrehner/Desktop/Virt/Server_App_2/bin/gunicorn backend.wsgi:app \
  --bind 127.0.0.1:8000 \
  --workers 4 \
  --threads 8
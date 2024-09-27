# gunicorn_config.py

workers = 3  # Number of worker processes
timeout = 120 # number of seconds for timeout
bind = "0.0.0.0:8000"  # Bind to all network interfaces on port 8000

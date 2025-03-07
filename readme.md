# Installation

## Using Docker

1. Create `.env` file in the project root directory and add your environment variables. Example:

    ~~~bash
    TRAIDER_OANDA_API="12345"
    TRAIDER_OANDA_SECRET="yourapisecret"
    TRAIDER_OANDA_BASE_URL="https://api-fxtrade.oanda.com/v3/"
    ~~~

2. Build images and start containers  
    `sudo docker-compose up -d --build`  
    `sudo docker-compose ps`

    ~~~bash
    NAME               IMAGE           COMMAND                  SERVICE   CREATED          STATUS          PORTS
    traider-app-1      traider-app     "python manage.py ru…"   app       35 minutes ago   Up 35 minutes   0.0.0.0:8000->8000/tcp, :::8000->8000/tcp
    traider-broker-1   rabbitmq:4      "docker-entrypoint.s…"   broker    35 minutes ago   Up 35 minutes   4369/tcp, 5671-5672/tcp, 15691-15692/tcp, 25672/tcp
    traider-db-1       postgres:15     "docker-entrypoint.s…"   db        35 minutes ago   Up 35 minutes   5432/tcp
    traider-tasks-1    traider-tasks   "celery -A app worke…"   tasks     35 minutes ago   Up 35 minutes   8000/tcp
    ~~~

3. Apply migrations  
    `sudo docker-compose exec app python manage.py migrate --noinput`

4. Create user  
    `sudo docker-compose exec app python manage.py createsuperuser`

5. Create Pairs, Bots and BotGroup
    - Collect static files
       `sudo docker-compose exec app python manage.py collectstatic --noinput`
    - Populate database  
       `sudo docker-compose exec app python manage.py populate`
    - Restart containers  
       `sudo docker-compose down`  
       `sudo docker-compose up -d`

6. Start the Bot from the dashboard at `http://localhost:8000/bot/`
7. You can check that bot successfully started by looking at the logs `sudo docker-compose logs -f tasks`

## Manual

1. Setup virtual environment and install dependencies  
    `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
2. Setup a [broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/index.html). The default one is RabbitMQ:
    - Install using the [appropriate method](https://www.rabbitmq.com/docs/download) for your environment.
    - Start the server:  
        `sudo rabbitmq-server -detached`
3. Set necessary environment variables. Example:

    ~~~bash
    export TRAIDER_OANDA_API="12345"
    export TRAIDER_OANDA_SECRET="yourapisecret"
    export TRAIDER_OANDA_BASE_URL="https://api-fxtrade.oanda.com/v3/"
    ~~~

4. Apply migrations  
    `python manage.py migrate`

4. Create user  
    `python manage.py createsuperuser`

5. Collect static files
    `python manage.py collectstatic --noinput`

6. Create Pairs, Bots and Botgroups  
    `python manage.py populate`

7. Start the server `python manage.py runserver localhost:8000`, go to `http://localhost:8000/analytics/` and check if you are getting the data. 

8. Start _Celery_:  
    `celery -A app worker --beat -P solo --loglevel=info`  

    If everything is ok, you should see it running the tasks:

    ~~~bash
     celery -A app worker --beat -P solo --loglevel=warning

         -------------- celery@archer v5.3.6 (emerald-rush)
        --- ***** -----
        -- ******* ---- Linux-6.12.7-arch1-1-x86_64-with-glibc2.40 2025-01-07 16:27:05
        - *** --- * ---
        - ** ---------- [config]
        - ** ---------- .> app:         app:0x7b8a2a629550
        - ** ---------- .> transport:   amqp://guest:**@localhost:5672//
        - ** ---------- .> results:     disabled://
        - *** --- * --- .> concurrency: 18 (solo)
        -- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
        --- ***** -----
         -------------- [queues]
                        .> celery           exchange=celery(direct) key=celery


        [tasks]
          . app.tasks.run_bots
    ~~~

9. For long-term deployment consider [setting up](https://wiki.archlinux.org/title/Systemd) _systemd_ services for _Celery_, _Django_ and the broker.

~~~bash
[Unit]
Description=traider celery daemon
After=network.target

[Service]
User=traider
Group=traider
EnvironmentFile=/var/opt/traider/.env
WorkingDirectory=/opt/traider/src
ExecStart=/bin/sh -c '/opt/traider/env/bin/celery -A app worker --beat -P solo --loglevel=warning --logfile=/var/log/kucoin/celery.log'

[Install]
WantedBy=multi-user.target
~~~

# MyTardis Filters as microservice

`docker-compose up` command will start following stack for you to run:
- app - MyTardis clone w/o filters middleware ("nofilters" branch)
- celery - celery worker of app codebase
- db - Postgres database for app
- rabbitmq - messaging bus between "app" and "filters"
- filters - celery worker of filters app (this repo)
- memcached - shared cache between filter workers (to prevent simultaneous processing)

As filters microservice has no acceess to the database, all schemas must be loaded using base app:
```
python manage.py loaddata tardis/filters/mytardisbf/mytardisbf.json
python manage.py loaddata tardis/filters/fcs/fcs.json
python manage.py loaddata tardis/filters/pdf/pdf.json
python manage.py loaddata tardis/filters/xlsx/xlsx.json
python manage.py loaddata tardis/filters/csv/csv.json
python manage.py loaddata tardis/filters/diffractionimage/diffractionimage.json
```

To run tests within stack:
```
docker-compose exec filters flake8 tardis
docker-compose exec filters pylint tardis
docker-compose exec filters python3 manage.py test
```

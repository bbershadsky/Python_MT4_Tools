FROM python:3.8.3-alpine
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
WORKDIR /app
ADD ./backend/requirements.txt /app/backend/

RUN pip install --upgrade pip
RUN pip install gunicorn
RUN pip install -r backend/requirements.txt

ADD ./backend /app/backend
ADD ./docker /app/docker
FROM python:3.5-alpine
ENV PYTHONUNBUFFERED 1

RUN apk --update add --no-cache \
git gcc build-base libffi-dev openssl-dev

COPY . /app
WORKDIR /app

ENV GROUP scielo
ENV USER scielo

RUN addgroup  $GROUP && \
    adduser -s -u $USERID -G $GROUP -D $USER

RUN pip --no-cache-dir install scielo-paperboy
RUN chown -R $USER:$GROUP /app

USER $USER

CMD ["python"]

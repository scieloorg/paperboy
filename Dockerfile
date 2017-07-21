FROM python:2.7-alpine
ENV PYTHONUNBUFFERED 1
ENV PAPERBOY_SETTINGS_FILE config.ini

RUN apk --update add --no-cache \
git gcc build-base libffi-dev openssl-dev wget

RUN apk --no-cache add ca-certificates && \
    wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://raw.githubusercontent.com/sgerrand/alpine-pkg-glibc/master/sgerrand.rsa.pub && \
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.25-r0/glibc-2.25-r0.apk && \
    apk add glibc-2.25-r0.apk

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

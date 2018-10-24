FROM python:3.6-alpine3.6

MAINTAINER Jerry Yuan "yuanxiaochen100@126.com"

ENV TIME_ZONE Asia/Shanghai

COPY EPortalAdapter.py /app/
COPY HTTPRedirectHandler.py /app/
COPY validCode.json /app/
COPY Daemon.py /app/

ENTRYPOINT ["python","/app/Daemon.py"]

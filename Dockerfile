FROM python:3-slim
LABEL maintainer="Egemen Yavuz <melih.egemen.yavuz@sysco.no>"

COPY ./service/service.py /service/
COPY ./service/requirements.txt /service/requirements.txt

WORKDIR /service
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5000/tcp
CMD ["python3", "-u", "./service.py"]

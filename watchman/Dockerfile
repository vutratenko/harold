FROM python:3.9.2-slim

WORKDIR /watchman
ADD ../requirements.txt ./watchman
ADD ./* /watchman/

RUN pip install -r requirements.txt 

CMD ./app.py
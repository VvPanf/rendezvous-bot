FROM python:3.6
WORKDIR app
COPY ./ ./
RUN pip3 install --upgrade pip -r requirements.txt
ENTRYPOINT flask run
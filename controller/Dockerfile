FROM python:3.8.20

COPY requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /controller/
WORKDIR /controller

EXPOSE 6653

RUN useradd ryu
USER ryu

CMD ["ryu-manager", "app.py"]
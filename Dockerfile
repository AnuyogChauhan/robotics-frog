FROM ubuntu:16.04
MAINTAINER Anderson Miller <anderson.miller@frogdesign.com>
#ENV http_proxy http://165.225.104.34:80
#ENV https_proxy https://165.225.104.34:80

RUN echo "8.8.8.8" >> /etc/resolv.conf
RUN echo "8.8.4.4" >> /etc/resolv.conf
RUN apt-get update
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes python2.7 
RUN apt-get install -y python3.5-dev python3.5 virtualenv python3-pip libgrpc-dev
RUN pip3 install --upgrade pip
RUN pip3 install grpcio

RUN mkdir /frog
COPY . /frog/
COPY ./ens/workloadPy.sh /frog/
COPY ./ens/ensiwc.so /frog/
COPY ./ens/enswmain.py /frog/
COPY ./ens/enswr.py /frog/
WORKDIR /frog/

RUN chmod 777 /frog/workloadPy.sh
ENTRYPOINT ["/frog/workloadPy.sh"]



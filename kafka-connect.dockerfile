FROM apache/kafka:latest

USER root 
WORKDIR /opt/kafka

EXPOSE 8083

RUN mkdir /opt/kafka/plugins 

COPY plugins.sh .
RUN chmod +x plugins.sh 
RUN sh plugins.sh

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["start"]
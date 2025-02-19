FROM openjdk:11-jdk-slim

WORKDIR /code

RUN apt-get update && apt-get install -y wget

RUN wget https://repo1.maven.org/maven2/junit/junit/4.13.2/junit-4.13.2.jar -P /lib/
RUN wget https://repo1.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar -P /lib/
RUN wget https://repo1.maven.org/maven2/com/google/code/gson/gson/2.8.9/gson-2.8.9.jar -P /lib/

ENV CLASSPATH=/lib/*:/code

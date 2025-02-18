FROM gcc:11.2.0

WORKDIR /code

# Install Google Test and JsonCpp with proper include paths
RUN apt-get update && apt-get install -y \
    cmake \
    libgtest-dev \
    libjsoncpp-dev \
    && cd /usr/src/gtest \
    && cmake CMakeLists.txt \
    && make \
    && cp lib/*.a /usr/lib \
    && ln -s /usr/include/jsoncpp/json /usr/include/json

# Set security limits
RUN mkdir /sandbox && chmod 777 /sandbox
USER nobody

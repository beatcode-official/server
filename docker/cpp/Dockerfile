FROM gcc:11.2.0

WORKDIR /code

# Install Google Test
RUN apt-get update && apt-get install -y \
    cmake \
    libgtest-dev \
    && cd /usr/src/gtest \
    && cmake CMakeLists.txt \
    && make \
    && cp lib/*.a /usr/lib

# Set security limits
RUN mkdir /sandbox && chmod 777 /sandbox
USER nobody

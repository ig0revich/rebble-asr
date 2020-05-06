FROM python:3.6
ADD . /code
WORKDIR /code

ENV CPPFLAGS="-I/usr/local/include"
ENV LDFLAGS="-L/usr/local/lib"
ENV LD_LIBRARY_PATH="/usr/local/lib" 

RUN apt-get update && \
    apt-get install ffmpeg --yes && \
    pip install -r requirements.txt && \
    wget https://github.com/xiph/speex/archive/Speex-1.2rc1.tar.gz && \
    tar -xvf Speex-1.2rc1.tar.gz && \
    cd speex-Speex-1.2rc1 && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    wget -O pyspeex-0.9.1.tar.gz https://github.com/NuanceDev/pyspeex/archive/0.9.1.tar.gz && \
    tar -xvf pyspeex-0.9.1.tar.gz && \
    cd pyspeex-0.9.1 && \
    make && \
    python setup.py install

CMD exec gunicorn -k gevent -b 0.0.0.0:80 asr:app

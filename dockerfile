FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /config

CMD [ "python" ]

# docker build -f dockerfile -t crypto_web3:1.0 .
# docker run -it --name af_piggybank -v /path/to/config.ini:/config/config.ini -v "$PWD":/usr/src/myapp -w /usr/src/myapp crytpo_web3:1.0 python piggybank.py /config/config.ini
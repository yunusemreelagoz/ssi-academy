FROM --platform=x86_64 ubuntu:22.04

RUN apt-get update
RUN apt-get -y install python3-pip python3-venv
RUN apt-get -y install vim
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /usr/local/lib

COPY nixar_api_linux/x86_64-unknown-linux-gnu/libnixar_core.so .
COPY nixar_api_linux/x86_64-unknown-linux-gnu/libzmq.so.5 .
COPY nixar_api_linux/x86_64-unknown-linux-gnu/libsodium.so.23 .

ENV LD_LIBRARY_PATH=/usr/local/lib
# Update the library cache
RUN ldconfig

WORKDIR /agent

COPY nixar/* nixar/
COPY demo_did_comm.py .
COPY demo_w_json.py .
COPY demo_w_sqlite.py .
COPY demo_w_pgsql.py .
COPY test_utils.py .

COPY genesis.txn .
COPY requirements.txt .


RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Set the virtual environment as default
ENV PATH="/agent/venv/bin:$PATH"


# Run the Python script
CMD ["python", "demo_w_pgsql.py"]

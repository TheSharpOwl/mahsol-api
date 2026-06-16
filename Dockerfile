FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    libgdal-dev \
    unixodbc-dev \
    mdbtools \
    odbc-mdbtools \
    && rm -rf /var/lib/apt/lists/*

# Register the MDBTools driver for unixODBC
RUN echo "[MDBTools]\nDescription = MDBTools Driver\nDriver = /usr/lib/x86_64-linux-gnu/odbc/libmdbodbc.so\nSetup = /usr/lib/x86_64-linux-gnu/odbc/libmdbodbc.so\nFileUsage = 1" > /etc/odbcinst.ini

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

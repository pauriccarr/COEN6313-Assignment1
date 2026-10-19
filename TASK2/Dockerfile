FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # needs grpcio, grpcio-tools, redis

COPY . .
# Generate category_pb2 etc. next to server.py, since it imports them as top-level modules
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. *.proto

RUN useradd --system --uid 10001 app
USER 10001
CMD ["python", "server.py"]

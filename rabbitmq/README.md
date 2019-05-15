## Version
RabbitMQ 3.7.14 on Erlang 21.3.7

## Docker cli
docker run --rm -d --hostname rabbit -e RABBITMQ_NODENAME=rabbit --name rabbit -p 15672:15672 -p 5672:5672 rabbitmq:3-management
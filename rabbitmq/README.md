## Docker cli
docker run --rm -d --hostname node1 --name rabbit -p 15672:15672 -p 5672:5672 rabbitmq:3-management
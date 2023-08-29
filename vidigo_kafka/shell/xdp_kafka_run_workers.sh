#!/bin/bash

# echo "hello :  $1 $2 $3 $4 $5 $6"
echo "hello : $BROKER_ID $BROKER_IP $BOOTSTRAP_SERVERS $BROKER_PORT $KAFKA_DIR $KAFKA_LOG_DIR"
mkdir $KAFKA_DIR
mkdir $KAFKA_LOG_DIR
cd $KAFKA_DIR

## Setup 1 : sasl 파일 생성
cat <<EOF > ${KAFKA_DIR}/bin/xdp_kafka_jaas.conf
KafkaServer {
    org.apache.kafka.common.security.plain.PlainLoginModule required
    username="vadmin"
    password="vidigo_admin"
    user_vadmin="vidigo_admin"
    user_vclient="vidigo_client"
}

Client {
    org.apache.kafka.common.security.plain.PlainLoginModule required
    username="vadmin"
    password="vidigo_admin"
}
EOF

cat <<EOF > ${KAFKA_DIR}/bin/sasl/xdp_zookeeper_jaas.conf
Server {
    org.apache.kafka.common.security.plain.PlainLoginModule required
    username="vadmin"
    password="vidigo_admin"
    user_vadmin="vidigo_admin"
    user_vclient="vidigo_client";
};
EOF

## Setup 2: 일단 Config 설정을 해당 원격서버에도 만들어 주기
cat <<EOF > ${KAFKA_DIR}/vidigo_config/xdp_kafka_configs.sh
#!/bin/bash


## Default Config

KAFKA_BROKER_ID=$BROKER_ID
KAFKA_PORT=$BROKER_PORT
KAFKA_BOOTSTRAP_SERVERS=$BOOTSTRAP_SERVERS
KAFKA_SOCKET_SEND_BUFFER_BYTES=102400
KAFKA_SOCKET_RECEIVE_BUFFER_BYTES=102400
KAFKA_SOCKET_REQUEST_MAX_BYTES=10457600
KAFKA_QUEUED_MAX_REQUESTS=100
KAFKA_ZOOKEEPER_CONNECT=192.168.1.245:2181


## Transaction Config

KAFKA_ACKS=all
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1
KAFKA_TRANSACTION_MAX_TIMEOUT_MS=600000
KAFKA_TRANSACTIONAL_ID_EXPIRATION_MS=1209600000


## Log Config

KAFKA_LOG_DIR=$KAFKA_LOG_DIR
KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS=1800000
KAFKA_RETENTION_HOURS=72
KAFKA_LOG_SEGMENT_BYTES=1610612736
KAFKA_LOG_CLEANER_ENABLE=false
KAFKA_LOG_ROLL_HOURS=72


## SASL Config

KAFKA_SUPER_USER=User:vadmin
KAFKA_SECURITY_INTER_BROKER_PROTOCOL=SASL_PLAINTEXT
KAFKA_SASL_MECHANISM_INTER_BROKER_PROTOCOL=PLAIN
KAFKA_SASL_ENABLED_MECHANISMS=PLAIN
KAFKA_AUTHORIZER_CLASS_NAME=kafka.security.auth.SimpleAclAuthorizer
KAFKA_ALLOW_EVERYONE_IF_NO_ACL_FOUND=true


## Topic Config
KAFKA_NUM_PARTITIONS=3
KAFKA_MESSAGE_MAX_BYTES=205800
KAFKA_NUM_RECOVERY_THREADS_PER_DATA_DIR=5
KAFKA_AUTO_CREATE_TOPICS_ENABLE=false
KAFKA_DEFAULT_REPLICATION_FACTOR=2
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1


## Network Config
KAFKA_NUM_NETWORK_THREADS=3
KAFKA_NUM_IO_THREADS=8
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=SASL_EXTERNAL:SASL_PLAINTEXT,SASL_INTERNAL:SASL_PLAINTEXT,EXTERNAL:PLAINTEXT,INTERNAL:PLAINTEXT
# KAFKA_LISTENERS=INTERNAL://kafka_cluster_broker0_1:9092
KAFKA_ADVERTISED_LISTENERS=INTERNAL://kafka_cluster_broker_$BROKER_ID:9092,SASL_EXTERNAL://192.168.1.245:9092
KAFKA_FETCH_MAX_BYTES=77771680


## JMX Config

KAFKA_JMX_PORT=9997
KAFKA_JMX_OPTS="-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Djava.rmi.server.hostname=$BROKER_IP -Dcom.sun.management.jmxremote.rmi.port=9997"
KAFKA_OPTS="-Djava.security.auth.login.config=/data/son/kafka_cluster/config/kafka_jaas.conf \
            -Djava.security.auth.login.config=/data/son/kafka_cluster/config/zookeeper_jaas.conf"


## Zookeeper Config
ZOOKEEPER_CLIENT_PORT=2181
ZOOKEEPER_TICK_TIME=3000

ZOOKEEPER_INIT_LIMIT=10
ZOOKEEPER_SYNC_LIMIT=5
ZOOKEEPER_DATA_DIR=/data/vidigo/zookeeper/data
ZOOKEEPER_CLIENT_PORT=2181
ZOOKEEPER_MAX_CLIENT_CNXNS=5
ZOOKEEPER_AUTOPURGE_SNAP_REAIN_COUNT=3
ZOOKEEPER_AUTOPURGE_PURGE_INTERVAL=1

ZOOKEEPER_ADMIN_ENABLE_SERVER=true
ZOOKEEPER_ADMIN_SERVER_PORT=3181
ZOOKEEPER_ADMIN_COMMAND_URL=/commands

ZOOKEEPER_DIR=/data/son/zookeeper
ZOOKEEPER_LOG_DIR=/data/son/zookeeper/logs
EOF


## Config를 만들었다면 바로 변수 등록
. ${KAFKA_DIR}/vidigo_config/xdp_kafka_configs.sh

## Kafka directiory로 이동 후 로그 

# cp ./vidigo_config/xdp_kafka_configs.sh $KAFKA_DIR/vidigo_config/xdp_kafka_configs.env


# docker-compose.yml 생성 : env file 째로 전달
cat <<EOF > docker-compose.yml 
version: '3'
services:
    vidigo_zookeeper:
        image: confluentinc/cp-zookeeper:7.3.0
        # hostname: root
        container_name: vidigo_zookeeper
        ports:
            - "3181:3181"
            - "2181:2181"
        env_file:
            - $KAFKA_DIR/xdp_kafka_configs.env
        networks:
            - xdp_kafka

    vidigo_kafka:
        image: confluentinc/cp-kafka:7.3.0
        container_name: vidigo_kafka
        env_file:
            - $KAFKA_DIR/xdp_kafka_configs.env
        ports:
            - "49092:9092"
            - "9997:9997"
        volumes:
            - $KAFKA_DIR:opt/kafka/vidigo
            - /var/run/docker.sock:/var/run/docker.sock
        depends_on:
            - zookeeper
        networks:
            - xdp_kafka

networks:
  xdp_kafka:
    driver: bridge
EOF

# # docker-compose 실행(--env-file 옵션을 추가할까?)
# docker-compose up -d

# echo "ok ${BROKER_ID} is done"

# exit 0


unset BROKER_ID
unset BOOTSTRAP_SERVERS
unset BROKER_IP
unset BROKER_PORT
unset KAFKA_LOG_DIR
unset KAFKA_DIR

echo "bye : $BROKER_ID $BOOTSTRAP_SERVERS $BROKER_IP $BROKER_PORT $KAFKA_LOG_DIR $KAFKA_DIR"


## 1. env 파일 만들기
## 2. docker-compose.yml 파일 만들기
## 3. sasl 파일 만들기(kafka_server_jaas.conf)
## 4. 안쓰는 변수 unset, exit 0 반환
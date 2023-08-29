#!/bin/bash

# source packages/xdp_kafka_configs.sh

# 만약 수행되지 않는다면, LD_LIBRARY_PATH를 원격 컴퓨터에 맞게 설정해야 한다.

## 도움말 function
usage() {
        echo " "
        echo "./xdp_kafka_run.sh [-b | --bootstrap_servers] [-d | --kafka_dir] [-l | --kafka_log_dir] [ENV FOR CONFIGS..]"
        echo " "
        echo "Options : "
        echo "    -h or --help                          도움말 출력"
        echo '    -b ARG or --bootstrap_servers ARG     String으로 붙여서 작성, "<서버IP>:<Kafka 포트>,<서버IP>:<Kafka 포트>..."'
        echo "    -d ARG or --kafka_dir ARG             Kafka Dir 설정"
        echo "    -l ARG or --kafka_log_dir ARG         Kafka Broker 별 Log Dir 설정"
        echo " "
        
        exit 1
}

# arguments 받아서 변수에 저장하는 function
set_options() {
    arguments=$(getopt --options b:d:l:h --longoptions bootstrap_servers:,kafka_dir:,kafka_log_dir:,help --name $(basename $0) -- "$@")
    eval set -- "$arguments"

    if [ $# -lt 6 ]
    then
        echo ""
        echo "옵션 값을 모두 입력해 주세요."
        echo ""
        usage
    fi

    while true
    do
        case $1 in
            -b|--bootstrap_servers)
                BOOTSTRAP_SERVERS=$2
                if [ $BOOTSTRAP_SERVERS = "-d" ] || [ $BOOTSTRAP_SERVERS = "--kafka_dir" ] || [ $BOOTSTRAP_SERVERS = "-l" ] || [ $BOOTSTRAP_SERVERS = "--kafka_log_dir" ]
                then
                    echo ""
                    echo "정확한 bootstrap_server 인자값을 넣어주세요."
                    usage;
                fi
                shift 2
                ;;
            -d|--kafka_dir)
                KAFKA_DIR=$2
                if [ $KAFKA_DIR = "-b" ] || [ $KAFKA_DIR = "--bootstrap_servers" ] || [ $KAFKA_DIR = "-l" ] || [ $KAFKA_DIR = "--kafka_log_dir" ]
                then
                    echo ""
                    echo "정확한 kafka_dir 인자값을 넣어주세요."
                    usage;
                fi
                shift 2
                ;;
            -l|--kafka_log_dir)
                KAFKA_LOG_DIR=$2
                if [ $KAFKA_LOG_DIR = "-b" ] || [ $KAFKA_LOG_DIR = "--bootstrap_servers" ] || [ $KAFKA_LOG_DIR = "-d" ] || [ $KAFKA_LOG_DIR = "--kafka_dir" ]
                then
                    echo ""
                    echo "정확한 kafka_log_dir 인자값을 넣어주세요."
                    usage;
                fi
                shift 2
                ;;
            --)
                shift
                break
                ;;
            *) 
                usage
                ;;
        esac
    done
    # 명령 문자열의 길이가 0이거나 interval이 0이면
    # 도움말을 출력하고 종료합니다.

    # 남아있는 인자 얻기, 남아 있는 인자는 config file
    shift $((OPTIND-1))
    CONFIGS=$@
    # exit 0
}
set_options "$@"

## BOOTSTRAP_SERVERS 문자열 분리 후 리스트화
SERVER_SPLIT=($(echo $BOOTSTRAP_SERVERS | tr "," "\n"))

# for 문 돌려서 서버 하나씩 접근
for i in ${SERVER_SPLIT[@]}
do
    # IP, PORT로 파싱
    IPADDR_SPLIT=($(echo $i | tr ":" "\n"))

    BROKER_ID=($(echo ${IPADDR_SPLIT[0]} | tr "." "\n"))
    echo "ip : ${IPADDR_SPLIT[0]}"
    echo "port : ${IPADDR_SPLIT[1]}"

    # IP 활용 SSH
    # ssh root@$i "/bin/bash" < dd.sh $BROKER_ID[3] $SERVER_SPLIT $i[0] $i[1] # broker id , bootstrap_servers, borker ip, broker port
    ssh root@$IPADDR_SPLIT "env BROKER_ID=${BROKER_ID[3]} BOOTSTRAP_SERVERS=${SERVER_SPLIT[@]} BROKER_IP=${IPADDR_SPLIT[0]} BROKER_PORT=${IPADDR_SPLIT[1]} bash < /data/son/kafka/packages/dd.sh" # broker id , bootstrap_servers, borker ip, broker port
    # 유저한테 받은 인자를 환경변수 파일(.env)와 대조, 기존 값 대체
    echo "kafka_dir : ${KAFKA_DIR}"
    echo "kafka_log_dir : ${KAFKA_LOG_DIR}"
    echo "broker_id : ${BROKER_ID[3]}"
    echo ""
    
    # 완료 됐다면 완료 사인
done

echo "Success."

# 다 쓴 변수는 해제
unset BOOTSTRAP_SERVERS
unset KAFKA_DIR
unset KAFKA_LOG_DIR

unset SERVER_SPLIT
unset IPADDR_SPLIT
unset BROKER_ID
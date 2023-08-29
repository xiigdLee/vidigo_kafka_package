cd $KAFKA_DIR

# 기존 docker-compose 재실행 -> 변경사항으로 재실행 해야 하기 때문에 다운 후 다시 올리기
docker-compose down
docker-compose up -d

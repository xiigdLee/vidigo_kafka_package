from confluent_kafka.admin import AdminClient
from confluent_kafka import Producer, Consumer
from confluent_kafka.error import KafkaException
from confluent_kafka.cimpl import KafkaError

from typing import Dict, Union, List
from dataclasses import dataclass

from vidigo_kafka.utils.kafka_logger import vidigoLogger


class KafkaHealthCheck():    
    '''
    Kafka 상태 파악 모듈입니다.

    Vidigo의 Kafka 클라이언트는 해당 클래스를 상속 받고, 동작 시 상태를 확인한 후 동작 합니다.

    필수 파라미터
    - bootstrap_servers : string, Kafka 클러스터 내 브로커 주소 하나의 string으로 명시
    - broker_id : list, 브로커 ID 명시
    - request_timeout_ms : integer, 타임아웃 제한 시간 명시(ms)
    '''
    def __init__(self, bootstrap_servers, broker_id, request_timeout_ms) :
        self.boostrap_servers : str = bootstrap_servers
        self.brokerid :list = broker_id
        self.request_timeout_ms : int = request_timeout_ms
    
        # Logger
        self.logger = vidigoLogger()
        self.client = None
    
    def check_client_status(self) :
        ''' 
        client 활성 여부
        '''
        if self.client is None :
            # return False
            self.logger.logging_failure(f"ERROR : {KafkaError.UNKNOWN_MEMBER_ID} | 클라이언트가 없습니다.")
            raise KafkaError(KafkaError.UNKNOWN_MEMBER_ID, "클라이언트가 없습니다.")
        else :
            return True


    def check_broker_health(self) :
        ''' 
        브로커 업 다운 유무 / prometheus로 대체 가능
        '''
        check_brokers = self.client.list_topics(timeout=1.0).brokers
        if check_brokers == [] :
            # return False
            self.logger.logging_failure(f"ERROR : {KafkaError.UNKNOWN_MEMBER_ID} | 클라이언트가 없습니다.")
            raise KafkaError(KafkaError.UNKNOWN_MEMBER_ID, "클라이언트 없습니다.")
        elif set(check_brokers.keys()) != set(self.brokerid) :
            # return False
            self.logger.logging_failure(f"ERROR : {-185} | 브로커 연결시간 초과했습니다.")
            raise KafkaError(-185, "브로커 연결시간 초과했습니다.")
        else :
            return True


    def check_topics_exist(self, topic_name:str) -> Dict[str, str]:
        """ 
        컨슈밍 하려고 하는 토픽 유무 / 일단 아직 사용되지 않음
        """
        check_topics : dict = self.client.list_topics(topic=topic_name).topics
        
        if check_topics is None :
            # return False
            self.logger.logging_failure(f"ERROR : {KafkaError.UNKNOWN_TOPIC_OR_PART} | 토픽이 존재하지 않습니다.")
            raise KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART, "토픽이 존재하지 않습니다.")
        else : 
            print(f"topic is exist : {list(check_topics.values())[0].topic}")
            return True
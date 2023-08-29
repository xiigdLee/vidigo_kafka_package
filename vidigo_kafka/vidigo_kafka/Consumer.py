from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition, Producer

from dataclasses import dataclass
from typing import Dict, List
import time

from vidigo_kafka.utils import KafkaHealthCheck

@dataclass
class vidigoConsumer(KafkaHealthCheck) :
    
    def __init__(self, bootstrap_servers, broker_id:List[int]):
        super().__init__(bootstrap_servers, broker_id, None)
        # default option    
        self.service: str = "vidigo"
        self.group_id: str = "vidigo_consumer_1"
        self.auto_offset_reset : str = "earliest"
        
        # transaction
        self.enable_auto_commit : bool = False  # 트랜잭션 적용 때문에 수동으로 커밋해야 함.
        self.isolation_level : str = "read_committed"
        
        #throughput
        self.fetch_min_bytes : int = 525288 # 대략 청크 2개 분량
        self.session_timeout_ms : int = 30000
        self.heartbeat_interval_ms : int = 10000
        self.max_poll_interval_ms : int = 30000
        # fetch_max_wait_ms : int = 100
        # max_poll_records : int = 100
        
        self.configs: dict = {
            "bootstrap.servers" :self.boostrap_servers,
            "group.id" : self.group_id,
            "default.topic.config" : { 
                "auto.offset.reset" : self.auto_offset_reset,
            },
            "enable.auto.commit" : self.enable_auto_commit,
            "isolation.level" : self.isolation_level,
            "fetch.min.bytes" : self.fetch_min_bytes,
            
            "max.poll.interval.ms" : self.max_poll_interval_ms,
            "session.timeout.ms" : self.session_timeout_ms,
            "heartbeat.interval.ms" : self.heartbeat_interval_ms,
            # "fetch.max.wait.ms" : self.fetch_max_wait_ms,
            # "max.poll.records" : self.max_poll_records,

            # 'security.protocol' :"SASL_SSL",
            # "sasl.mechanism" : "PLAINTEXT",
            # "sasl.plain.username" : "vadmin", 
            # "sasl.plain.password" : "admin",
        }
        self.client = Consumer(self.configs)

        ## DLQ
        self.dlq_configs: dict = {
            "bootstrap.servers" : self.boostrap_servers,
            "acks" : 0
                        
            # 'security.protocol' :"SASL_SSL",
            # "sasl.mechanism" : "PLAINTEXT",
            # "sasl.plain.username" : "vadmin", 
            # "sasl.plain.password" : "admin",
        }

        # sasl 인증
        self.client.set_sasl_credential("vadmin", "vidigo_kafka")
        self.dlq_producer.set_sasl_credential("vadmin", "vidigo_kafka")

        self.dlq_producer = Producer(self.dlq_configs)

    def send_deadletter(self, topic, value) :
        self.dlq_producer.produce(topic, value)
        self.dlq_producer.flush()


    def check_topics_exist(self, topic_name:str) -> Dict[str, str]:
        """ 컨슈밍 하려고 하는 토픽 유무 """
        try:
            if self.check_broker_health() == False :
                self.logger.logging_failure(f"FAILURE : [{self.group_id}] | {data}")
                return False

            check_topics = self.client.list_topics(topic=topic_name).topics
            data = {"topic" : check_topics}
            print(f"Available topic : {list(check_topics.values())[0].topic}")
            return data
        
        
        # 카프카 에러
        except KafkaException as ke:
            # 브로커 다운 시 에러코드 -195 / 못 찾고 타임아웃 -185 / 그 밖에 ... 
            if ke.args[0].code() == -195 :
                print(f"ERROR : ({ke.args[0].code()}) 브로커 중지 상태. Kafka 실행 후 다시 시도해 주세요.")
                self.logger.logging_failure(f"FAILURE : [{self.group_id}] | {ke}")
                return False
            elif ke.args[0].code() == -185:
                print(f"ERROR : ({ke.args[0].code()}) 브로커 아이디 등을 확인 후 재시도 바랍니다.")
                self.logger.logging_failure(f"FAILURE : [{self.group_id}] | {ke}")
                return False
            else :
                print(f"ERROR : ({ke.args[0].code()}) 브로커 에러입니다. 상세 정보 : {ke}")
                self.logger.logging_failure(f"FAILURE : [{self.group_id}] | {ke}")
            return False
        
        # 커스텀 연결 에러
        except KafkaError as kee:
            print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
            return False
        
        # 기타 에러
        except Exception as e:
            print(f"Error : {e} 상태 확인 후 재시도 해주세요.")
            return False


    def rollback_transaction(self, topic,partition,rollback_cnt):
        '''
        [incomplete] if failed to consume all chunk data, offset rollback 
        아직은 로직을 좀 더 생각해 볼 필요가 있음. 불안정함.
        '''
        # self.client.commit([TopicPartition(topic,(partition-rollback_cnt)+1)])
        
        # return self.client.position([TopicPartition(topic,partition)]).offset()
        pass

    def consume_message(self, topic:str, partition:int) :
        ''' consuming method '''

        if self.check_broker_health() == True :
            target_topic = TopicPartition(topic, partition)
            count = 0
            total_latency = 0
            total_message_size = 0

            self.client.assign([target_topic]) # 없는 토픽이라면 error

            while True :
                try :
                    msg = self.client.poll(timeout=2)
                    ## kafka header : [ (name, b"file_result"), (1, 10) ]
                    if msg is None:
                        self.client.commit(asynchronous=True)
                        print("finish!")
                        break
                        
                    message_size = len(msg.value())
                    latenc = int(time.time() * 1000) - msg.timestamp()[1]

                    self.logger.logging_success(f"CONSUME : topic= {msg.topic()}/{msg.partition()}, offset= {msg.offset()}, value= {message_size}, timestamp={int(time.time()*1000)}, latency= {latenc} ms")
                    count += 1
                    total_latency += latenc
                    total_message_size += message_size

                    # if count % 100 == 0 :
                    #     self.client.commit(asynchronous=True)
                    #     print(f"commit..{count}")
                    #     continue

                    if msg.error() is not None:
                        print(msg.error())
                        self.send_deadletter(msg.value())
                        break
                    
                except KafkaException as ke:
                    # 브로커 다운 시 에러코드 -195 / 못 찾고 타임아웃 -185 / 그 밖에 ... 
                    if ke.args[0].code() == -195 :
                        self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 중지 상태. Kafka 실행 후 다시 시도해 주세요.")
                        self.send_deadletter(msg.value())
                    elif ke.args[0].code() == -185:
                        self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 아이디 등을 확인 후 재시도 바랍니다.")
                        self.send_deadletter(msg.value())
                    else :
                        self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 에러입니다. 상세 정보 : {ke}")
                        self.send_deadletter(msg.value())
                
                # 커스텀 연결 에러
                except KafkaError as kee:
                    self.logger.logging_dead_letter(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
                    self.send_deadletter(msg.value())

                # 기타 에러
                except Exception as e:
                    self.logger.logging_dead_letter(f"Error : {e} 상태 확인 후 재시도 해주세요.")
                    self.send_deadletter(msg.value())
    
                

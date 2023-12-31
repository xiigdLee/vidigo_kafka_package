from confluent_kafka import Producer
from confluent_kafka import KafkaError, KafkaException

from dataclasses import dataclass
from threading import Thread
from datetime import datetime
from glob import glob
import asyncio, json, time

from typing import List

from vidigo_kafka.utils import chunkUtils, KafkaHealthCheck

class vidigoAIOProducer(KafkaHealthCheck) :
    '''
    vidigo kafka의 Producer class 입니다.
    메세지를 청크사이즈로 쪼개서 분할 전송 하도록 구현되어 있습니다.
    '''
    def __init__(self, bootstrap_servers, broker_id:List[int], request_timeout_ms:int, chunk_size:int, linger_ms, loop=None) :

        super().__init__(bootstrap_servers, broker_id, request_timeout_ms)
        
        self.dist: str = "results"
        self.service: str = "vidigo"
        self.uid: str = "VIDIGOUID1" 
        self.elapsed_bar: float = 0.03 
        self.chunk_size:int = 102400
        self.meta_info_type: str = "analysis"
        self.meta_info_name: str = "analysis_result"
        
        # default properties
        self.message_max_bytes: int = 1048576 # messsage 최대 사이즈
        self.batch_size: int = chunk_size * 2 + 1000 # batch 사이즈 : 최대로 몇개씩 묶어서 보낼 것인가
        self.linger_ms: int = linger_ms # 최대로 몇 ms까지 배치 사이즈를 채울 수 있도록 기다릴 것인가
        # transaction & retries
        self.enable_idempotence: bool = True # 중복없는 전송
        self.transaction_id: str = f"kafka_transaction_{self.uid}1" # transaction 도입을 위해 고유 id 설정
        self.max_in_flight_requests_per_connection: int = 4 # 최대 몇개까지 한번에 전송할지
        self.acks: str = "all" # acks 사인은 리더와 레플리카에 모두 전송한 데이타가 복제 되면 ok 사인
        self.delivery_timeout_ms : int = 3000 # retry를 시도해 볼 수 있는 기간
        
        self.configs: dict = {
            "bootstrap.servers" : self.boostrap_servers,
            "message.max.bytes" : self.message_max_bytes,
            "max.in.flight.requests.per.connection" : self.max_in_flight_requests_per_connection,
            "enable.idempotence" : self.enable_idempotence,
            "transactional.id" : self.transaction_id,
            "batch.size" : self.batch_size,
            "linger.ms": self.linger_ms,
            "acks" : self.acks,
            "delivery.timeout.ms" : self.delivery_timeout_ms 
            # 'security.protocol' :"SASL_SSL",
            # "sasl.mechanism" : "PLAINTEXT",
            # "sasl.plain.username" : "vadmin", 
            # "sasl.plain.password" : "admin",
        }


        self._loop = loop or asyncio.get_event_loop()
        self.client = Producer(self.configs)

        self._cancelled: bool = False
        self._poll_thread = Thread(target=self._poll_loop)
        self._poll_thread.start()

        # sasl 인증
        self.client.set_sasl_credential("vadmin", "vidigo_kafka")

    def _poll_loop(self):
        '''
        자식 스레드에서 실행할 polling loop
        '''
        while not self._cancelled:
            self.client.poll(0)
            if self._poll_thread.is_alive() :
                continue
            else :
                print("poll loop thread restart...")
                self._poll_thread.start()

    def close(self):
        '''
        자식 스레드를 완료하고 부모스레드와 병합
        '''
        self._cancelled: bool = True
        self._poll_thread.join()


    def delivery_report(self, err, msg) -> None :
        '''
        producing 한 레코드 당 받을 콜백 메서드
        '''
        if err:
            # 메세지에 에러가 났다면 transaction 중지, dead letter file 로그로 빠지게
            self.logger.logging_dead_letter({"error" : err, "msg" : msg})
            self.client.abort_transaction()

        else:
            # 메세지 전송 성공 시 로깅
            print(msg.topic(), msg.partition(), msg.offset())
            self.logger.logging_success(f'Timestamp : {msg.timestamp()} Topic : {msg.topic()}, Partition : {msg.partition()}, Offset : {msg.offset()}, Length : {len(msg.value())} ')


    def send_messages(self, topic: str, data:bytes, filename:str="result_image.png"):
        ''' producing method, filename is required'''
        self.client.init_transactions() # 트랜잭션 초기화

        try:
            if self.check_broker_health() != True :
                self.logger.logging_failure(f"FAILURE : [{self.uid}] | {data}")
            
            
            # self.client.init_transactions()
            start_time = datetime.strptime(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"), "%Y-%m-%d %H:%M:%S.%f")
            print (f"start : {start_time}")
            
            count = 0 # 전송한 메세지 총 갯수
            total_elapsed = 0 
            timestamp = int(datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), '%Y-%m-%d %H:%M:%S.%f').timestamp() * 1000)
            self.client.begin_transaction() # 트랜잭션 시작
            t00 =time.time()
            
            # 메세지를 chunk size로 쪼개기
            messages = chunkUtils(self.service,
                                self.uid, 
                                timestamp, 
                                filename,
                                self.meta_info_type,
                                self.meta_info_name,
                                self.chunk_size,
                                data)
            
            # 메세지를 리스트를 받아 produce
            for index, msg in enumerate(messages.get()):
                self.client.produce(topic=topic, value=json.dumps(msg), on_delivery=self.delivery_report)
                
                t01 =time.time()
                elapsed = t01 - t00

                sleep_time = self.elapsed_bar - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                total_elapsed += elapsed
                
                count += 1
            
            self.client.commit_transaction() # 트랜잭션 커밋

 
        except KafkaException as ke:
            if ke.args[0].code() == -195 :
                self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 중지 상태. Kafka 실행 후 다시 시도해 주세요.")
            if ke.args[0].code() == -185:
               self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 아이디 등을 확인 후 재시도 바랍니다.")
            else :
                self.logger.logging_dead_letter(f"ERROR : ({ke.args[0].code()}) 브로커 에러입니다. 상세 정보 : {ke}")
            
            self.client.abort_transaction()
            self.logger.logging_dead_letter({"error" : ke})

        except KafkaError as kee:
            print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
            
            self.client.abort_transaction()
            self.logger.logging_dead_letter({"error" : kee})


        finally:
            self.close() # 자식 스레드 병함


## 잠시만, 실제 vidigo에서는 producer 루프가 돌지 않는다. 요청이 들어오면 데이터 짤라서 그거 for 루프로 메세지 엮고, 던진다. -> 그것도 여기서 안한다 그냥 던진다. util class에서 for문으로 잘 짤라서 리턴한다.

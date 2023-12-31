from confluent_kafka.admin import AdminClient, NewTopic, RESOURCE_BROKER, ConfigResource, NewPartitions, ConfigEntry
from confluent_kafka.error import KafkaException
from confluent_kafka.cimpl import KafkaError

from typing import Dict, Union, List
from dataclasses import dataclass

from vidigo_kafka.utils import KafkaHealthCheck

class vidigoAdminClient(KafkaHealthCheck):
    
    def __init__(self, bootstrap_servers:str, broker_id:List[int]):
        super().__init__(bootstrap_servers, broker_id, None)
        self.client_id : int = "kafka_adimin"
        self.connections_max_idle_ms : int = 300000
    

        self.configs = {
            "bootstrap.servers" : self.boostrap_servers,
            "request.timeout.ms": self.request_timeout_ms,
            "client.id" : self.client_id,
            "connections.max.idle.ms" : self.connections_max_idle_ms,
                                
            # 'security.protocol' :"SASL_SSL",
            # "sasl.mechanism" : "PLAINTEXT",
            # "sasl.plain.username" : "vadmin", 
            # "sasl.plain.password" : "admin",
        }
        
        self.client = AdminClient(self.configs)
        
        # sasl 인증
        self.client.set_sasl_credential("vadmin", "vidigo_kafka")

        # adminclien로 dynamic configuration 가능한 옵션 리스트
        self.dynamic_config_lists=["advertised.listeners","listeners","principal.builder.class","sasl.enabled.mechanisms","sasl.kerberos.kinit.cmd",
                                "sasl.kerberos.min.time.before.relogin","sasl.kerberos.principal.to.local.rules", "sasl.kerberos.service.name","sasl.kerberos.ticket.renew.jitter",
                                "sasl.kerberos.ticket.renew.window.factor","sasl.login.refresh.buffer.seconds","sasl.login.refresh.min.period.seconds","sasl.login.refresh.window.factor",
                                "sasl.login.refresh.window.jitter","sasl.mechanism.inter.broker.protocol","ssl.client.auth","ssl.enabled.protocols","ssl.keymanager.algorithm",
                                "ssl.protocol", "ssl.provider", "ssl.trustmanager.algorithm","listener.security.protocol.map","ssl.endpoint.identification.algorithm", "ssl.secure.random.implementation", 
                                "background.threads", "compression.type", "log.flush.interval.messages","log.retention.bytes","log.segment.bytes", "log.segment.delete.delay.ms","message.max.bytes", "min.insync.replicas",
                                "num.io.threads","num.network.threads", "num.recovery.threads.per.data.dir", "num.replica.fetchers", "unclean.leader.election.enable",
                                "log.cleaner.backoff.ms", "log.cleaner.dedupe.buffer.size", "log.cleaner.delete.retention.ms", "log.cleaner.io.buffer.load.factor", "log.cleaner.io.buffer.size", 
                                "log.cleaner.io.max.bytes.per.second", "log.cleaner.max.compaction.lag.ms", "log.cleaner.min.cleanable.ratio", "log.cleaner.min.compaction.lag.ms", "log.cleaner.threads",
                                "log.cleanup.policy", "log.index.interval.bytes", "log.index.size.max.bytes", "max.connections.per.ip.overrides","ssl.cipher.suites",
                                "log.message.timestamp.difference.max.ms","log.message.timestamp.type","log.preallocate","max.connection.creation.rate","max.connections","max.connections.per.ip",
                                "log.message.downconversion.enable","metric.reporters"]
    
    # 현재 클러스터 내 모든 토픽 조회
    def view_topics(self, timeout_sec:int=0.5) -> Dict[str,List[str]]:
        '''
        클러스터 내 모든 토픽 조회
        '''
        try:
            # broker health cheack 후 진행
            self.check_broker_health()
        
            # topic 리스트 
            all_topic_lists = list(self.client.list_topics(timeout=timeout_sec).topics.keys())
            
            # 리스트가 빈 리스트라면
            if bool(all_topic_lists) == False :
                raise KafkaError(-188, "브로커 내에 토픽이 존재하지 않습니다.")
            else :
                # 결과 dict
                data : Dict[str, List[str]] = {"status" : True, "topics" : all_topic_lists}
                return data
        
        except TypeError as te:
            te.args = (KafkaError(-154, "find_topic 타입은 str 타입이여야 합니다."),)
            print(f"ERROR : ({te.args[0].code()}) {te.args[0].str()} 재설정 후 다시 시도해 주세요 " )
            self.logger.logging_failure(f"{te.args[0].code()} | {te.args[0].str()}")
        except KafkaError as kee :
            print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"{kee.code()} | {kee.str()}")
        except Exception as e :
            print(f"ERROR : (9999) {str(e)} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"9999 | {kee.str()}")
    
    
    # New Topic 핸들링 해야 함 / client 객체 연동 실패, 리턴 값 조정
    def new_topics(self, set_topic:str="test0", set_partition:int=1, set_replication_factor:int=1, timeout_sec:int=2) -> Dict[str,Union[str, bool]] :
        '''
        새로운 토픽 생성
        '''        
        try:
            # broker health cheack 후 진행
            self.check_broker_health()

            # 인자 타입이 안 맞다면?
            if (type(set_partition) is not int) or (type(set_replication_factor) is not int):
                raise KafkaError(-154,"set_partition 혹은 set_replication_factor 인자 타입이 안 맞습니다.")           
            
            # 생성할 토픽 정보 
            new_topic = NewTopic(topic=set_topic, num_partitions=set_partition, replication_factor=set_replication_factor)
            new_topic_list = self.client.create_topics(new_topics=[new_topic], request_timeout=timeout_sec)
            
            # 토픽 생성
            ## v는 future class로 토픽이 이미 있으면 여기에 담겨서 kafkaError가 날 것.
            for k,_ in new_topic_list.items() :
                if k == None :
                    raise KafkaError(-196, "토픽이 생성되지 않았습니다.")
                print(f'SUCCESS : 토픽 생성 완료. 토픽 이름 = "{k}"')
                data = {"status": True, "topic_name": k}
            return data

        except KafkaException as ke:
            print(f"ERROR : ({ke.args[0].code()}) {ke.args[0].str()} 오타 확인이나 재설정 후 다시 시도해 주세요")
            self.logger.logging_failure(f"{ke.args[0].code()} | {ke.args[0].str()}")
        except TypeError as te:
            te.args = (KafkaError(-154, "find_topic 타입은 str 타입이여야 합니다."),)
            print(f"ERROR : ({te.args[0].code()}) {te.args[0].str()} 재설정 후 다시 시도해 주세요 " )
            self.logger.logging_failure(f"{te.args[0].code()} | {te.args[0].str()}")
        except KafkaError as kee :
            print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"{kee.code()} | {kee.str()}")
        except Exception as e :
            print(f"ERROR : (9999) {str(e)} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"9999 | {kee.str()}")


    # 토픽 삭제 메서드
    def del_topics(self, set_topic:str="test", timeout_sec:int=2) -> Dict[str, str]:
        '''
        토픽 삭제
        '''
        try:
            self.check_broker_health()

            # 삭제하고자 하는 토픽 정보
            del_topic_list = self.client.delete_topics(topics=[set_topic], request_timeout=timeout_sec)

            for k,v in del_topic_list.items() :
                # 삭제하고자 하는 토픽 값이 없다면 False 반환
                v.result()
                if k == None :
                    raise KafkaError(-196, "토픽이 삭제되지 않았습니다.")
                print(f'SUCCESS : 토픽 삭제 완료. 토픽 이름 = "{k}"')
                data = {"status": True, "topic_name": k}
            return data
    
        except KafkaException as ke:
            print(f"ERROR : ({ke.args[0].code()}) {ke.args[0].str()} 오타 확인이나 재설정 후 다시 시도해 주세요")
            self.logger.logging_failure(f"{ke.args[0].code()} | {ke.args[0].str()}")
        except TypeError as te:
            te.args = (KafkaError(-154, "find_topic 타입은 str 타입이여야 합니다."),)
            print(f"ERROR : ({te.args[0].code()}) {te.args[0].str()} 재설정 후 다시 시도해 주세요 " )
            self.logger.logging_failure(f"{te.args[0].code()} | {te.args[0].str()}")
        except KafkaError as kee :
            print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"{kee.code()} | {kee.str()}")
        except Exception as e :
            print(f"ERROR : (9999) {str(e)} 다시 확인 후 재시도 바랍니다.")
            self.logger.logging_failure(f"9999 | {kee.str()}")

    
    
    
    # def new_partition(self, set_topic, total_partition, broker_list=1):
    #     '''새로운 파티션 생성'''
        
    #     # 브로커에 이상이 있다면?
    #     if self.check_broker_health() != True :
    #         self.logger.logging_failure(f"FAILURE : [ AdminClient ] | {data}")
        
    #     set_partition = NewPartitions(set_topic, total_partition, [[broker_list]])
    #     new_partition_list = self.client.create_partitions(new_partitions=[set_partition], request_timeout=2)
    #     for k,v in new_partition_list.items() :
    #         # print(v.result())
    #         # 생성하고자 하는 토픽 값이 없다면 False 반환
    #         if k == None :
    #             print("ERROR : Partition doesn't created.")
    #             return False
    #         print(f'SUCCESS : Created partition. Topic name = "{k}"')
    #         data = {"status": True, "partition_name": k}
    #     return data




    # def alter_broker_configs(self, brokerid:str=300, alter_config_name:str="message.max.bytes", alter_configs_value=1050000, timeout_sec=2):
    #     '''
    #     동적 브로커 구성 변경 항목만 가능 : per-broker, cluster wide

    #     현재는 잠깐 사용 중단
    #     '''
    #     try :
    #         self.check_broker_health()
            
    #         dynamic_config_lists =[]
    #         dynamic_config_api = requests.get(f"http://192.168.2.15:49000/api/clusters/vidigo_kafka_test/brokers/{brokerid}/configs?page=1&perPage=100").json()
    #         for i in dynamic_config_api :
    #             dynamic_config_lists.extend(i['name'])
        

    #         # 브로커 아이디가 int 타입이 아니라면?
    #         if type(brokerid) is not int:
    #             raise KafkaError(-154, "brokerid 타입은 int 타입이여야 합니다.")
            
    #         view_all_config = ConfigResource(RESOURCE_BROKER, str(brokerid))
    #         all_config_info = self.client.describe_configs(resources=[view_all_config], request_timeout=timeout_sec) # return =  {ConfigResource : Future} / Future 객체가 진짜.
    #         config_dict = list(all_config_info.values())[0].result() # type : dict, {"name" : ConfigEntry }
            
    #         # 브로커 설정 값이 옳지 않다면?
    #         if alter_config_name not in dynamic_config_lists:
    #             raise KafkaError(40, "동적으로 변경할 수 없는 설정입니다.")
    #         # 브로커 아이디가 str type이 아니라면?
            
    #         # 동적 설정 변경 가능한 애들만.
    #         dynamic_config_dict = {}
    #         for i in dynamic_config_lists:
    #             dynamic_config_name=config_dict[i].name
    #             dynamic_config_value=config_dict[i].value
    #             dynamic_config_dict[dynamic_config_name] = dynamic_config_value
    #             dynamic_config_dict[alter_config_name] = alter_configs_value
            
    #         # 변경 적용된 모든 설정을 불러서 덮어쓰기
    #         view_alter_config = ConfigResource(RESOURCE_BROKER, str(brokerid), set_config=dynamic_config_dict)
    #         alter_config_info = self.client.alter_configs(resources=[view_alter_config], request_timeout=2)
    #         result_dict = list(alter_config_info.values())[0].result() #type : dict, {"name" : ConfigEntry }
    #         print(config_dict[alter_config_name])

    #         return result_dict

    #     except KafkaError as kee :
    #         print(f"ERROR : ({kee.code()}) {kee.str()} 다시 확인 후 재시도 바랍니다.")
    #         self.logger.logging_failure(kee)
    #     except Exception as e :
    #         print(f"ERROR : {e.__cause__} {str(e)} 다시 확인 후 재시도 바랍니다.")
    #         self.logger.logging_failure(e)

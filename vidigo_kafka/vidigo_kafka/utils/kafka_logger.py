from dataclasses import dataclass
import time, logging, datetime
from typing import Dict, Union


@dataclass
class vidigoLogger :

    # 로거, 포매터 생성, 핸들러 생성
    logger = logging.getLogger("vidigoKafka")
    logging_date = datetime.datetime.now().strftime("%Y%m%d")
    
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] >> %(message)s')
    kafka_fileHandler = logging.FileHandler(f"C:\\Users\\xiili\\Downloads\\kd.lee\\vidigo_kafka\\vidigo_kafka\\logs\\success\\vidigo_kafka_{logging_date}.log")
    
    failure_logger = logging.getLogger("vidigoKafkaFailure")
    failure_fileHandler = logging.FileHandler(f"C:\\Users\\xiili\\Downloads\\kd.lee\\vidigo_kafka\\vidigo_kafka\\logs\\failure\\vidigo_kafka_{logging_date}.log")

    dlq_logger = logging.getLogger("vidigoKafkaForDLQ")
    dlq_formatter = logging.Formatter('{"timestamp": %(asctime)s, "message" : %(message)s},')
    dlq_fileHandler = logging.FileHandler(f"C:\\Users\\xiili\\Downloads\\kd.lee\\vidigo_kafka\\vidigo_kafka\\logs\\success\\vidigo_kafka_{logging_date}.log")

    def __post_init__(self) :
        self.kafka_fileHandler.setFormatter(self.formatter)
        self.logger.addHandler(self.kafka_fileHandler)
        self.logger.setLevel(level=logging.INFO)

        self.failure_fileHandler.setFormatter(self.formatter)
        self.failure_logger.addHandler(self.failure_fileHandler)
        self.failure_logger.setLevel(level=logging.WARN)

        self.failure_fileHandler.setFormatter(self.dlq_formatter)
        self.failure_logger.addHandler(self.dlq_fileHandler)
        self.failure_logger.setLevel(level=logging.INFO)

    def logging_success(self, message: str) :
        self.logger.info(message)
    
    def logging_failure(self, message: str) : 
        self.failure_logger.error(message)

    def logging_dead_letter(self, message : Dict[str, Union[str, bytes]]) :
        self.dlq_logger.info(message)
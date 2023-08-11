from dataclasses import dataclass
from typing import Union, Tuple, List

import base64, os

import math
import filetype

@dataclass
class chunkUtils:
    service: str
    uid: str 
    timestamp: int 
    filename : str
    meta_info_type: str
    meta_info_name: str
    chunk_size: int
    data : bytes

    def __post_init__(self):
        self.messages = list()
        source = {
            'service' : self.service,
            'uid' : self.uid,
            'timestamp' : self.timestamp
        }
        kind = filetype.guess(self.data)
        meta_file_name, meta_file_extension = os.path.splitext(self.filename)
    
        if kind is None:
            file_type = meta_file_extension.replace('.', '')
        else:
            file_type = kind.mime.split('/')[0]
            meta_file_extension = kind.extension
        
        meta = {
            'info' : {
                'type' : self.meta_info_type,
                'name' : self.meta_info_name,
                'dist_id' : f'{self.uid}_{self.timestamp}_{self.filename}',
            },
            'file' : {
                'type' : file_type,
                'name' : meta_file_name,
                'extension' : meta_file_extension,
            }
        }

        chunks_length, chunks = self.split_str(self.data, self.chunk_size)
        
        for i, chunk in enumerate(chunks) :
            data = {
                "chunks" : {
                    "data_length" : len(self.data),
                    "chunk_num" : chunks_length,
                    "chunk_size" : self.chunk_size,
                    "chunk_index" : i
                },
                "value" : self.b64_encoding_data(chunk)
            }
            message = {
                "source" :source,
                "meta" : meta,
                "data": data
            }
            self.messages.append(message)

    def b64_encoding_data(self, value:Union[bytes, str]) -> str :
        """
        Encode data
        """
        if type(value) != bytes : 
            value = value.encode("utf-8")
        
        return base64.b64encode(value).decode('utf-8')


    def split_str(self, str_value:str, chunk_num:int) -> Tuple[int, List[str]]:
        """
        Split data by chunk size
        """
        result = [str_value[i:i+chunk_num] for i in range(0, len(str_value), chunk_num)]
        return len(result), result

    def get(self):
        return self.messages
    
    def get_len(self):
        return len(self.messages)
    
    def get_simple(self):
        messages = list()
        
        for msg in self.messages:
            
            m = {
                'source' : msg['source'],
                'meta' : msg['meta'],
                'data' : dict()
            }
            m['data']['chunks'] = msg['data']['chunks']
            m['data']['value'] = len(msg['data']['value'])
            messages.append(m)
        return messages



# def get_num_chunks(data: bytes, chunk_size: int):
#     data_length, num_chunks = len(data), math.ceil(len(data) / chunk_size)
#     return data_length, num_chunks


@dataclass
class Message:
    service: str
    uid: str
    timestamp: int
    dist: str
    meta_info_type: str
    meta_info_name: str
    filepath: str
    file_index: int
    chunk_size: int
        
    def __post_init__(self):
        self.messages = list()
        source = {
            'service' : self.service,
            'uid' : self.uid,
            'timestamp' : self.timestamp
        }
        kind = filetype.guess(self.filepath)
        splitted = self.filepath.split('/')
        filedir, filename = splitted[-2], splitted[-1]
        # filename = os.path.basename(self.filepath)
        _, file_ext = os.path.splitext(filename)
    
        if kind is None:
            file_type = file_ext.replace('.', '')
        else:
            file_type = kind.mime.split('/')[0]
        
        meta = {
            'info' : {
                'type' : self.meta_info_type,
                'name' : self.meta_info_name,
                'dist_id' : f'{self.uid}_{self.timestamp}_{self.dist}',
            },
            'file' : {
                'type' : file_type,
                'name' : filename,
                'dir' : filedir,
                'extension' : file_ext,
                'index' : self.file_index
            }
        }
        
        with open(self.filepath, 'rb') as f:
            data = f.read()
        data_length = len(data)
        chunks_num, chunks = self.chunks_str(data, self.chunk_size)
        
        for i, chunk in enumerate(chunks):
            data = {
                'chunks' : {
                    'data_length' : data_length,
                    'chunks_num' : chunks_num,
                    'chunk_size' : self.chunk_size,
                    'chunk_index' : i
                },
                'value' : base64.b64encode(chunk).decode('utf-8') if isinstance(chunk, bytes) else chunk
            }
            
            message = {
                'source' : source,
                'meta' : meta,
                'data' : data
            }
            self.messages.append(message)
            
    def get(self):
        return self.messages
    
    def get_len(self):
        return len(self.messages)
    
    def get_simple(self):
        messages = list()
        
        for msg in self.messages:
            
            m = {
                'source' : msg['source'],
                'meta' : msg['meta'],
                'data' : dict()
            }
            m['data']['chunks'] = msg['data']['chunks']
            m['data']['value'] = len(msg['data']['value'])
            messages.append(m)
        return messages

    def chunks_str(self, str_value, n):
        result = list()
        """Yield successive n-sized chunks from lst."""
        for i in range(math.ceil(len(str_value) / n)):
            s = i * n
            e = (i+1) * n 
            result.append(str_value[s:e])
        return len(result), result

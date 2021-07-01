#利用Crypto来对数据进行加密！
from Crypto.Cipher import AES
from Crypto import Random
import struct
import json

max_buff_size = 1024
key = b'fdj27pFJ992FkHQb'


#定义加密和解密函数

def encrypt(data):
    code = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CFB, code)
    return code + cipher.encrypt(data)


def decrypt(data):
    return AES.new(key, AES.MODE_CFB, data[:16]).decrypt(data[16:])

#接收数据函数，发送数据前会在数据前部加上指明数据大小的一个二字节数。接收数据时先接收这个二字节数，获取将要接收的数据包的大小，然后接收这个大小的数据作为本次接的数据包。
def pack(data):
    return struct.pack('>H', len(data)) + data


def send(socket, data_dict):
    socket.send(pack(encrypt(json.dumps(data_dict).encode('utf-8'))))


def recv(socket):
    data = b''
    surplus = struct.unpack('>H', socket.recv(2))[0]
    socket.settimeout(5)
    while surplus:
        recv_data = socket.recv(max_buff_size if surplus > max_buff_size else surplus)
        data += recv_data
        surplus -= len(recv_data)
    socket.settimeout(None)
    return json.loads(decrypt(data))

import socketserver
import pickle
import time

import utils

#初始化用户和历史记录
users = None
history = None

'''用户管理相关函数包含从文件中加载所有已注册用户的信息（账号和密码对应的MD5值）
注册用户、验证用户（看看密码的MD5值是否和文件中的值相同）
将所有已注册用户的信息
'''
def load_users():
    try:
        return pickle.load(open('users.dat', 'rb'))
    except:
        return {}


def register(usr, pwd):
    if usr not in users.keys():
        users[usr] = pwd
        save_users()
        return True
    else:
        return False


def validate(usr, pwd):
    if usr in users.keys() and users[usr] == pwd:
        return True
    return False



def save_users():
    pickle.dump(users, open('users.dat', 'wb'))
    
#配置聊天记录
'''
聊天记录管理相关函数每条聊天记录为key-value形式
key为（sender，receiver）
value为（sender，time，msg
）相关函数包含从文件中加载所有用户的所有聊天记录
把一条聊天记录存入内存中，返回某用户对某用户的聊天记录
将所有用户的所有聊天记录保存到文件中
'''
def load_history():
    try:
        return pickle.load(open('history.dat', 'rb'))
    except:
        return {}


def get_key(u1, u2):
    return (u1, u2) if (u2, u1) not in history.keys() else (u2, u1)


def append_history(sender, receiver, msg):
    if receiver == '':
        key = ('','')
    else:
        key = get_key(sender, receiver)
    if key not in history.keys():
        history[key] = []
    history[key].append((sender, time.strftime('%m月%d日%H:%M', time.localtime(time.time())), msg))
    save_history()


def get_history(sender, receiver):
    if receiver == '':
        key = ('','')
    else:
        key = get_key(sender, receiver)
    return history[key] if key in history.keys() else []


def save_history():
    pickle.dump(history, open('history.dat', 'wb'))

#配置服务器
'''
服务端采用socketserver的BaseRequestHandler类，可自动处理并发请求，
即每有一个客户端请求连接时，都会new一个BaseRequestHandler类，然后在一个线程中处理相关请求。
服务端能处理登录请求、注册请求、获取所有已登录用户的列表、
获取连接中的用户与其他用户的聊天记录、将连接中的用户的消息发给其期望接收的用户、
将连接中的用户的发送文件请求发给其期望接收的用户
'''
class Handler(socketserver.BaseRequestHandler):
    clients = {}

    def setup(self):
        self.user = ''
        self.file_peer = ''
        self.authed = False

    
    def handle(self):
        while True:
            data = utils.recv(self.request)
            if not self.authed:
                self.user = data['user']
                if data['cmd'] == 'login':
                    if validate(data['user'], data['pwd']):
                        utils.send(self.request, {'response': 'ok'})
                        self.authed = True
                        for user in Handler.clients.keys():
                            utils.send(Handler.clients[user].request, {'type': 'peer_joined', 'peer': self.user})
                        Handler.clients[self.user] = self
                    else:
                        utils.send(self.request, {'response': 'fail', 'reason': '账号或密码错误！'})
                elif data['cmd'] == 'register':
                    if register(data['user'], data['pwd']):
                        utils.send(self.request, {'response': 'ok'})
                    else:
                        utils.send(self.request, {'response': 'fail', 'reason': '账号已存在！'})
            else:
                if data['cmd'] == 'get_users':
                    users = []
                    for user in Handler.clients.keys():
                        if user != self.user:
                            users.append(user)
                    utils.send(self.request, {'type': 'get_users', 'data': users})
                elif data['cmd'] == 'get_history':
                    utils.send(self.request, {'type': 'get_history', 'peer': data['peer'], 'data': get_history(self.user, data['peer'])})
                elif data['cmd'] == 'chat' and data['peer'] != '':
                    utils.send(Handler.clients[data['peer']].request, {'type': 'msg', 'peer': self.user, 'msg': data['msg']})
                    append_history(self.user, data['peer'], data['msg'])
                elif data['cmd'] == 'chat' and data['peer'] == '':
                    for user in Handler.clients.keys():
                        if user != self.user:
                            utils.send(Handler.clients[user].request, {'type': 'broadcast', 'peer': self.user, 'msg': data['msg']})
                    append_history(self.user, '', data['msg'])
                elif data['cmd'] == 'file_request':
                    Handler.clients[data['peer']].file_peer = self.user
                    utils.send(Handler.clients[data['peer']].request, {'type': 'file_request', 'peer': self.user, 'filename': data['filename'], 'size': data['size'], 'md5': data['md5']})
                elif data['cmd'] == 'file_deny' and data['peer'] == self.file_peer:
                    self.file_peer = ''
                    utils.send(Handler.clients[data['peer']].request, {'type': 'file_deny', 'peer': self.user})
                elif data['cmd'] == 'file_accept' and data['peer'] == self.file_peer:
                    self.file_peer = ''
                    utils.send(Handler.clients[data['peer']].request, {'type': 'file_accept', 'ip': self.client_address[0]})
                elif data['cmd'] == 'close':
                    self.finish()


    def finish(self):
        if self.authed:
            self.authed = False
            if self.user in Handler.clients.keys():
                del Handler.clients[self.user]
            for user in Handler.clients.keys():
                utils.send(Handler.clients[user].request, {'type': 'peer_left', 'peer': self.user})

#主函数
if __name__ == '__main__':
    users = load_users()
    history = load_history()

    #绑定ip，端口
    app = socketserver.ThreadingTCPServer(('0.0.0.0', 8888), Handler)
    #设置始终监听
    app.serve_forever()

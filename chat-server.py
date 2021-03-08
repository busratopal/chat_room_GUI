# stream multiclient server

import asyncio

SERVER_PORT = 50050

# for bug patch with Spyder

import nest_asyncio

nest_asyncio.apply()

class ClientInfo:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.nick = None

class Server:
    def __init__(self):
        self.clients = []
        self.msg_dict = {
            'LOGIN': self.login_proc, 
            'SEND_MSG': self.send_msg_proc, 
            'LOGOUT': self.logout_proc,
        }
        
    async def run(self, reader, writer):
        ci = ClientInfo(reader, writer)
        
        peername = writer.get_extra_info('peername')
        print(f'new client socket connected: {peername}')
        
        try:
            while True:
                b = await reader.readline()
                if not b:
                    break
                msg_line = b.decode('UTF-8').strip()
                result = await self.process_msg(ci, msg_line)
                if not result:
                    break
        except Exception as e:
            print(f'Exception occurred on {ci.nick}: {e}')
            await self.logout_proc(ci, None)
            if ci in self.clients:
                self.clients.remove(ci)
            
        writer.close()
        await writer.wait_closed()
        print(f'client disconnected: {peername}')

    async def process_msg(self, ci, msg_line):
        msg, params = self.cmd_split(msg_line)
        f = self.msg_dict.get(msg)
        if not f:
            ci.writer.write(f'ERROR Invalid command: {msg_line}\n')
            ci.writer.flush()
            return True

        return await f(ci, params)
    
    async def login_proc(self, ci, params):
        for client in self.clients:
            if params == client.nick:
                ci.writer.write('LOGIN_REJECTED User name alread exists!\n'.encode('UTF-8'))
                return
                
        ci.writer.write('LOGIN_ACCEPTED\r\n'.encode('UTF-8'))
        ci.nick = params
        
        self.clients.append(ci)
        
        nicks = ','.join([client.nick for client in self.clients])
        ci.writer.write(f'LOGGEDIN_CLIENT_LIST {nicks}\n'.encode(encoding='UTF-8'))
        
        for client in self.clients:
            if client is not ci:
                client.writer.write(f'NEW_CLIENT_LOGGEDIN {params}\n'.encode(encoding='UTF-8'))
        print(f'client loggedin: {ci.nick}')
        
        return True
         
    async def send_msg_proc(self, ci, params):
        for client in self.clients:
             client.writer.write(f'RECEIVE_MSG <{ci.nick}>: {params}\n'.encode(encoding='UTF-8'))
             
        return True
             
    async def logout_proc(self, ci, params):
        ci.writer.write('LOGOUT_ACCEPTED \n'.encode(encoding='UTF-8'))
        for client in self.clients:
            if client is not ci:
                client.writer.write(f'CLIENT_LOGGEDOUT {ci.nick}\n'.encode(encoding='UTF-8'))
        self.clients.remove(ci)
        print(f'client loggedout: {ci.nick}')
        
        return False
                  
    @staticmethod         
    def cmd_split(msg_line):
        index = msg_line.find(' ')
        if index == -1:
            return msg_line, ''
        return msg_line[:index], msg_line[index + 1:]
     
loop = asyncio.get_event_loop()
print('waiting for connection...')

server = Server()

async_server = asyncio.start_server(server.run, '', SERVER_PORT)
loop.run_until_complete(async_server)
loop.run_forever()




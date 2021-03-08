import tkinter as tk
import tkinter.scrolledtext
import tkinter.messagebox
import socket
import threading
import os

DISCONNECTED = 0
CONNECTED = 1

class GUI:
    def __init__(self, master):
        master.geometry('900x700')
        master.title('Sample Messagebox')
        master.resizable(width=False, height=False)
        self.master = master
        self.msg_dict = {
            'NEW_CLIENT_LOGGEDIN': self.new_client_loggedin_proc, 
            'LOGGEDIN_CLIENT_LIST': self.loggedin_client_list_proc, 
            'RECEIVE_MSG': self.receive_msg_proc,
            'LOGOUT_ACCEPTED': self.logout_accepted_proc,
            'CLIENT_LOGGEDOUT': self.client_loggedout_proc,
        }        
        
        self.status_label_connect_var = tk.StringVar()
        self.status_label_connect_var.set('Not Connected')
        self.entry_chat_var = tk.StringVar()

        self.menu_bar = tk.Menu(master)
        self.client_popup = tk.Menu(tearoff=0)
        self.menu_bar.add_cascade(label='Client', menu=self.client_popup, underline=0)
        
        self.client_popup.add_command(label='Connect...', command=self.client_connect_handler, underline=1, accelerator='Ctrl+O')
        self.client_popup.add_command(label='Disconnect', command=self.client_disconnect_handler, underline=0, accelerator='Ctrl+D', state='disabled')
        master.bind('<Control-o>', lambda  event: self.client_connect_handler())
        master.bind('<Control-d>', lambda event: self.client_disconnect_handler())
        master.config(menu=self.menu_bar)
        
        master.protocol('WM_DELETE_WINDOW', self.window_close_handler)
        
        self.status_frame = tk.Frame(master)
        self.status_connection_label = tk.Label(self.status_frame, relief=tk.SUNKEN, anchor='w', padx=(3, ), textvariable=self.status_label_connect_var)
        self.status_connection_label.pack(side='left', fill='x', expand=True)
        self.status_frame.pack(side='bottom', fill='x')
        
        self.frame = tk.Frame(self.master)
        self.text_chat = tk.scrolledtext.ScrolledText(self.frame, font='Calibri 14', width=60)
        self.listbox_clients = tk.Listbox(self.frame, font='Calibri 14', width=25)
        self.entry_chat = tk.Entry(self.master, font='Calibri 14', textvariable=self.entry_chat_var)
        self.button_ok = tk.Button(self.master, text='Ok', width=10, command=self.button_ok_handler)

        self.master.bind('<Return>', lambda event: self.button_ok_handler())
        self.will_close = False
        self.status = DISCONNECTED
        
    def show_widgets(self):
        self.text_chat.pack(side='left', padx=(0, 20), fill='y', anchor='n')
        self.listbox_clients.pack(side='left', fill='y', anchor='n')
        self.frame.pack(side='top', fill='x', anchor='n', padx=(10, 10), pady=(10, 10))
        self.entry_chat.pack(side='top', fill='x', padx=(10, 10), pady=(10, 10))
        self.button_ok.pack(side='top', padx=(10, 10), pady=(10, 10))
        
        self.master.bind('<Return>', lambda event: self.button_ok_handler())
        self.entry_chat.focus()
        
    def hide_widgets(self):
        self.text_chat.delete('1.0', 'end')
        self.text_chat.pack_forget()
        self.listbox_clients.delete(0, 'end')
        self.listbox_clients.pack_forget()
        self.frame.pack_forget()
        self.entry_chat.pack_forget()
        self.button_ok.pack_forget()
        
    def button_ok_handler(self):
        self.fw_sock.write(f'SEND_MSG {self.entry_chat_var.get()}\n')
        self.fw_sock.flush()
        self.entry_chat_var.set('')
        self.entry_chat.focus()
        
    def client_connect_handler(self):
        cd = ConnectDialog(self.master)
        self.master.wait_window(cd)
        if cd.result:
            self.thread = threading.Thread(target=self.thread_proc, args=(cd.server_name, cd.server_port, cd.nick), daemon=True)
            self.thread.start()
            
    def client_disconnect_handler(self):   
        self.fw_sock.write('LOGOUT \n')
        self.fw_sock.flush()
       
    def thread_proc(self, server_name, server_port, nick):
        try:
            self.client_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            self.client_sock.connect((server_name, server_port))
            self.fr_sock = self.client_sock.makefile('r', encoding='UTF-8')
            self.fw_sock = self.client_sock.makefile('w', encoding='UTF-8')  
            self.server_name = server_name
            self.server_port = server_port
            self.nick = nick
            
            self.login_proc()
        except Exception as e:
            tk.messagebox.showerror(title='Error', message=e)
        
    def login_proc(self):
        self.fw_sock.write(f'LOGIN {self.nick}\n')
        self.fw_sock.flush()
        
        response = self.fr_sock.readline().strip()
        if not response:
            self.socket_closed()
            return
        
        msg, args = self.cmd_split(response)
        if msg == 'LOGIN_ACCEPTED':
            self.status_label_connect_var.set('Connected')
            self.client_popup.entryconfig(0, state='disabled')
            self.client_popup.entryconfig(1, state='normal')
            self.show_widgets()
            self.status = CONNECTED
            self.msg_proc()
            return
        
        if msg == 'LOGIN_REJECTED': 
            tk.messagebox.showerror(title='Error', message=args)
            return
                
    def msg_proc(self):
        try:
            while True:
                msg_line = self.fr_sock.readline().strip()
                msg, params = self.cmd_split(msg_line)
                f = self.msg_dict.get(msg)
                if not f:
                   break
                
                f(params)
        except:
            pass
            
    def new_client_loggedin_proc(self, params):
       self.listbox_clients.insert(tk.END, params)
       
    def loggedin_client_list_proc(self, params):
        for nick in params.split(','):
            self.listbox_clients.insert(tk.END, nick)
            
    def receive_msg_proc(self, params):
        self.text_chat.insert('end', params + os.linesep)
        self.text_chat.yview('end')
        
    def logout_accepted_proc(self, params):
        self.fw_sock.close()
        if self.will_close:
            self.master.destroy()
        self.status_label_connect_var.set('Not Connected')
        self.client_popup.entryconfig(0, state='normal')
        self.client_popup.entryconfig(1, state='disabled')
        self.hide_widgets()
        self.status = DISCONNECTED
        
    def client_loggedout_proc(self, params):
        index = self.listbox_clients.get(0, 'end').index(params)
        self.listbox_clients.delete(index)
          
    @staticmethod         
    def cmd_split(msg_line):
        index = msg_line.find(' ')
        if index == -1:
            return msg_line, ''
        return msg_line[:index], msg_line[index + 1:]
    
    def socket_closed(self):
        self.status_label_connect_var.set('Connected')
        tk.messagebox.showwarning(title='Warninh', message='connection closed')
        
    def window_close_handler(self):
        if self.status == CONNECTED:    
            self.will_close = True
            self.master.after(3000, lambda: self.master.destroy())
            self.client_disconnect_handler()
        else:
            self.master.destroy()
        
class ConnectDialog(tk.Toplevel):
    def __init__(self, master):
        super(ConnectDialog, self).__init__()
        self.geometry('380x170+300+400')
        self.title('Connection Dialog')
        self.resizable(width=False, height=False)
        self.master = master
        
        self.entry_host_var = tk.StringVar()
        self.entry_port_var = tk.StringVar()
        self.entry_nick_var = tk.StringVar()
        
        self.entry_host_var.set('localhost')
        self.entry_port_var.set('50050')

        self.transient(master)
        self.grab_set()   
        
        self.label_host = tk.Label(self, text='Host', width=6, font='Arial 14')
        self.label_host.grid(row=0, column=0, pady=5)
        
        self.entry_host = tk.Entry(self, width=25, textvariable=self.entry_host_var, font='Arial 14')
        self.entry_host.grid(row=0, column=1)
        
        self.label_port = tk.Label(self, text='Port', width=6, font='Arial 14')
        self.label_port.grid(row=1, column=0, pady=5)
        
        self.entry_port = tk.Entry(self, width=25, textvariable=self.entry_port_var, font='Arial 14')
        self.entry_port.grid(row=1, column=1)
        
        self.label_nick = tk.Label(self, text='Nick', width=6, font='Arial 14')
        self.label_nick.grid(row=2, column=0, pady=5)
        
        self.entry_nick = tk.Entry(self, width=25, textvariable=self.entry_nick_var, font='Arial 14')
        self.entry_nick.grid(row=2, column=1)
        
        self.frame = tk.Frame(self)
        self.button_connect = tk.Button(self.frame, text='Connect', width=8, command=self.connect_proc)
        self.button_connect.pack(side='left', padx=(0, 10))
        self.button_cancel = tk.Button(self.frame, text='Cancel', width=8,  command=self.cancel_proc)
        self.button_cancel.pack(side='left')
        self.frame.grid(row=3, column=1, sticky='e', pady=(20, 0))
        
        self.bind('<Return>', lambda event: self.connect_proc())
        
        self.entry_nick.focus()
        
    def connect_proc(self):
        self.result = False
        try:
            nick = self.entry_nick_var.get().strip()
            if not nick:
                tk.messagebox.showerror(title='Error', message='Nick name must be specified!')
                self.entry_nick.focus()
                return
            
            self.server_name = self.entry_host_var.get()
            self.server_port = int(self.entry_port_var.get())
            self.nick = self.entry_nick_var.get()
            self.result = True
            self.destroy()
            
        except Exception as e:
            tk.messagebox.showerror(title='Error', message=e)
        
    def cancel_proc(self):
        self.result = False
        self.destroy()
        
root = tk.Tk()
gdb = GUI(root)
root.mainloop()



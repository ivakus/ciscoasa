#!/usr/bin/python36
# -*- coding: utf-8 -*-
# version 0.3
# date 21.12.2018
# Ivaka D.M/
import re
import datetime
import socket
import os
from sys import exit,argv
from paramiko.ssh_exception import (
    SSHException,
    BadAuthenticationType,
    ChannelException,
    ProxyCommandFailure,
)
import subprocess
from netmiko import ConnectHandler


class ASAContext:
    def __init__(self,name="",configurl="startup-config",method="scp"):
        self.name=name
        self.configurl=configurl
        self.SaveMethod = method
    def SetMethod(self,m_):
        self.SaveMethod = m_
    def GetMethod(self):
        return self.SaveMethod
    def SetUrl(self,u_):
        self.configurl = u_
    def GetUrl(self):
        return self.configurl
    def GetName(self):
        return self.name
    def isNameNull(self):
        if "null" in self.name :
            return True
        else:
            return False

    def __str__(self):
        return "Name -{}:{}:{}".format(self.name,self.configurl,self.SaveMethod)
    def __repr__(self):
        return "Name -{}:{}:{}".format(self.name,self.configurl,self.SaveMethod)

class CiscoASA :
    def __init__(self, device_ip ="",port = 22, username = "", password = "",enable = "" ):
        self.net_connect = {
        "ip":device_ip,
        "port": port,
        "username":username,
        "password":password,
        "secret": enable,
        "device_type":"cisco_asa"
        }
        self.Device_name="UNKNOW"
        self.isContext = False
        self.ContextCount = 0;
        self.DEBUG = False
        self.ssh_conn = None
        self.ContextList = list()
        self.Datenow = datetime.datetime.now().strftime('%Y.%m.%d %H:%M:%S')
        self.Status = "UNKNOW"
        self.StatusINT = 1
        self.Dir=""

    def Discovery_host(self):
        # Производим изучение устройства проверяем на наличие контекстов
        if self.SetConnection() == False :
            return False
        self.GetDeviceName()
        self.isContext = self.CheckContext()
        #self.DEBUG = True
        if (self.isContext):
            if self.FindAllContext() != True:
                self.CreateSystemContext()
        else:
            self.CreateSystemContext()
        return True
    def SetConnection(self):
        # Устанавливаем коннект к устройству, если не удачно возвращаем None
        self.DebbugOutput ("INFORMATIONAL: Connecting to : {}".format(self.net_connect["ip"]))
        try:
            self.ssh_conn = ConnectHandler(**self.net_connect)
        except  SSHException():
            self.DebbugOutput("ERROR: Incompatible version SSH (1.5 instead of 2.0)")
            self.Status = "SSH ERROR,  Version 1"
            self.StatusINT = 7
        except socket.error:
            self.DebbugOutput("ERROR: ip Address not Correct : {} ".format(self.net_connect["ip"]))
            self.Status = 'IP incorrect'
            self.StatusINT = 5
        except:
            print ("ERROR:  not connected to IP {}".format(self.net_connect["ip"]))
            self.StatusINT = 2
            self.Status = "TIMEOUT"
        if self.ssh_conn == None :
            self.DebbugOutput ("ERROR: Connection to : {} ".format(self.net_connect["ip"]))
            return False
        else:
            self.DebbugOutput("OK: Connection Established to: {} ".format(self.net_connect["ip"]))
            return True
    def GetDeviceName(self):
        # Получаем имя устройства к нему будем добовлять название контекстов при наличии.
        new_prompt = self.SendCommand("show hostname")
        if (new_prompt == None ):
            self.DebbugOutput("ERROR: Not finde Device name : ".format(self.Device_name))
            return False
        self.DebbugOutput("OK: Device promt {}".format(new_prompt))
        self.Device_name = new_prompt.strip()
        self.Dir = self.Device_name
        self.Dir = self.ssh_conn.base_prompt.strip("#")
        self.DebbugOutput("OK: Device name {}".format(self.Device_name))
        return True
    def CheckContext(self):
        cmd_check_context = "show context count"
        o_ = self.SendCommand(cmd_check_context)
        if (len (o_) <=0 ):
            self.DebbugOutput("ERROR:  Command \"{}\"  return : {} " .format(cmd_check_context,o_))
            return False
        self.DebbugOutput("OK:  Command \"{}\"  return : {} ".format(cmd_check_context,o_))
        for line in o_.split("\n"):
            m_ = re.search("Total.*:\s*\d*",line)
            if m_ != None :
                self.DebbugOutput("OK:  Faind context \"{}\" ".format(m_[0]))
                n_,c_ = m_[0].split(":")
                try :
                    self.ContextCount = int (c_)
                except:
                    self.DebbugOutput("ERROR:  Can't convert count context to Int  \"{}\" ".format(c_))
                    return False
                else :
                    self.DebbugOutput("OK: Context count  \"{}\" type {}".format(self.ContextCount,type(self.ContextCount)))
                    return True
        return False
    def SendCommand(self,cmd):
        o_=""
        if self.ssh_conn is None :
            self.SetConnection()
        if self.ssh_conn.is_alive() == False :
            if self.SetConnection() == False :
                return None
        try :
            o_ = self.ssh_conn.send_command(cmd)
        except:
            print ("Could not Execute commanfd {}".format(cmd))
            return None
        else:
            self.DebbugOutput("OK: Command : \"{}\" run succsesfuuly".format(cmd))
            self.DebbugOutput("OK: Command Return : \"{}\"".format(o_))
            #print (o_)
            return o_
    def ChangeContext(self):
        cmd_chahge_context = "change system"
        if (self.ssh_conn == None ) :
            return None
        if self.ssh_conn.is_alive() == False :
            if self.SetConnection() == False :
                return None
        try :
            o_ =  self.ssh_conn.send_command(cmd_chahge_context, expect_string=self.Dir.split("/",1)[0])
        except:
            self.DebbugOutput("ERROR : Could not Execute commanfd {}".format(cmd_chahge_context))
            return None
        else:
            if ("error" in o_.lower()):
                self.DebbugOutput("INFORMATION: Context not use")
                self.StatusINT = "6"
                self.Status = "CONTEXT ERROR"
            self.DebbugOutput("OK: Command : \"{}\" run succsesfuuly".format(cmd_chahge_context))
            self.ssh_conn.base_prompt = self.ssh_conn.find_prompt()
            #self.Device_name = self.ssh_conn.base_prompt
            self.Dir = self.ssh_conn.base_prompt.strip("#")
            return o_
    def DebbugOutput(self,str):
        if (self.DEBUG):
            print ("DATE {}".format(self.Datenow))
            print (str)
    def FindAllContext(self):
        # Переключаемся в системный контекст и собираем информацию по всем имеющися контекстам заполняем поле имя и congigUrl
        cmd_show_context = "show context detail"
        o_ = self.ChangeContext()
        if o_ == None :
            self.DebbugOutput("ERROR: Cant switch to System context : {}".format(self.net_connect["ip"]))
        o_ = self.SendCommand(cmd_show_context)
        curent_context = None
        if (len(o_)<=0) :
            return False
        for line_ in o_.split("\n"):
            #print (line_)
            m_ = re.search(r"^Context\s+\"(.*)\".*$",line_)#"(.+)".+Config URL\s?:\s?.+$',o_)
            if m_ != None :
                if curent_context != None:
                    self.ContextList.append(curent_context)
                    self.DebbugOutput("Faind Context : {}".format(curent_context))
                curent_context = ASAContext(name=m_[1])
            m_ = re.search(r"^.+Config URL:\s+(.*)$",line_)
            if (m_ != None):
                if ("startup-config" in m_[1]):
                    curent_context.SetMethod("run")
                curent_context.SetUrl(m_[1])
        self.ContextList.append(curent_context)
        self.DebbugOutput("Not Context{}".format(self.ContextList))
        return True
    def CreateSystemContext(self):
        # создаем системный окнтекст для устройств где контексты не включены
        self.ContextList.append(ASAContext(name="system",method="run"))
        self.DebbugOutput("Not Context{}".format(self.ContextList))
        return True
    def GetConfig(self,context_ = None):
        # получаем конфиг контекста
        if context_ == None :
            return False
        if "run" in context_.GetMethod():
            cmd = "show running-config"
        else:
            cmd = "more " +context_.GetUrl()
        #self.DEBUG = True
        self.DebbugOutput("Send command : \"{}\" for context \"{}\" ".format(cmd, context_))
        o_ = self.SendCommand(cmd)
        return o_
    def GetCheksumm(self):
        cmd = "show checksum"
        o_ = self.SendCommand(cmd)
        if o_ != None :
            if ("error" in o_.lower()):
                return None
            else:
                return o_.split()[-1]

    def CloseSSH(self):
        if not self.ssh_conn == None:
            self.ssh_conn.disconnect()
    def SaveConfig(self,config_dir):
        # Сохраняем конфигурационный файлф, на вход подаем директорию куда сохранять
        bytes = 0
        self.ChangeContext()
        for i in range(0, len(self.ContextList)):
            if not (self.ContextList[i].isNameNull()):
                config_context = self.GetConfig(self.ContextList[i])
                if (len(config_context) > 0):
                    self.StatusINT = 0
                    self.Status = "OK"
                    bytes += len(config_context)
                    file_dir = config_dir+"/" +  dev_.ContextList[i].name+""
                    if (not os.path.exists(file_dir)):
                        os.makedirs(file_dir)
                    file_name = file_dir+"/" + "{}-{}.conf".format(dev_.Device_name, dev_.ContextList[i].name)
                    # print (file_name)
                    # file_name = "{}-{}.conf".format(dev_.Device_name,dev_.ContextList[i].name)
                with open(file_name, "w") as F:
                    print(config_context, file=F)
        return bytes

def zabbix_sender(ip, status_int):
    # /usr/bin/zabbix_sender -z 10.53.76.6 -s 172.16.4.171 -k LastCfgBackupStatus -o 0
    cmd = 'zabbix_sender -z '+ ZABBIX_SERVER+' -s ' + ip +' -k LastCfgBackupStatus -o '+str(status_int)
    #print (cmd)
    subprocess.Popen(cmd, shell = True, cwd='/usr/bin/')


def get_dir_from_hostname(in_hostname):
    #hostname = in_hostname
    s = in_hostname.split("/", 1)
    hostname = s[0]
    context = s[1]
    # изменяем путь в зависимости от РСПД или ИИТИ (DO*)
    s = str(hostname[0:2])
    if (s == "DO"):
        path_git = common_path_git_IITI
    else:
        path_git = common_path_git

    # заменить (в конце) "86-ENER-C700-ACSW-1" на "86-ENER-C700-ACSW1"
    p00 = re.compile(r'(\D+)\-(\d+)$')
    hostname = p00.sub(r"\1\2", hostname)

    hostname_dir = hostname

    # делаем замены кодов регионов в имена или удаляем совсем
    hostname_dir = hostname_dir.replace('89-', '').replace('11-', '').replace('28-', 'GPPB-BLAG-').replace('77-BLAG-',
                                                                                                           'GPPB-MOSCOW-')
    hostname_dir = hostname_dir.replace('77-', 'MOSCOW-').replace('86-SZSK-', 'SZSK-').replace('86-', 'SURGUT-')
    hostname_dir = hostname_dir.replace('02-', '')

    # меняем DO46-DC2-DU-ASA01 на DO46/DC2/DU/ASA01
    p99 = re.compile(r'\-|\/')
    hostname_dir = re.sub(p99, '/', hostname_dir)

    # собираем полный путь с path_git (в зависимости от начала имени хоста)
    #     /data/git/IITI/DO46/DC2/DU/ASA01/act/
    # или /data/git/CONFIGS/SURGUT/ENER/C007/FRWL2/act
    hostname_dir = path_git + '/' + hostname_dir+"/"+context
    # если директория не существует, то создаем
    if (not os.path.exists(hostname_dir)):
        os.makedirs(hostname_dir)
    return hostname_dir


DEBUG = False
ZABBIX_SERVER = '127.0.0.1'

# Путь к директориям устройств в git
common_path_git = '/data/git/CONFIGS'
common_path_git_IITI = '/data/git/IITI'
ssh_user = "ciscobot"
ssh_password = ""
ssh_admin_user = "admin"
ssh_admin_password = ""
ssh_admin_enable = ""
BYTES = 0
STATUS = "UNKNOW"
STR_OUT = ""
STATUS_INT = 1
HOSTNAME = "UNKNOW"
DIR = "UNKNOW"
IP = ""
ZABIX_SEND = True

try:
    IP =  argv[1]
    try:
        command = argv[2]
    except IndexError:
        command = "config"
    #command = "cheksum"
    #IP = "172.16.61.62"
    #IP = "10.53.253.145"
    #IP = "10.53.253.241"
    #IP = "172.16.81.61"

    dev_ = CiscoASA (device_ip=IP,username=ssh_admin_user,password=ssh_admin_password,enable=ssh_admin_enable)
    dev_.DEBUG = DEBUG
    if ("cheksum" in command.lower()):
        cheksumm = dev_.GetCheksumm()
        print(cheksumm)
        STATUS = " {} Cheksum - {}, OK".format(IP, cheksumm)
        STATUS_INT = 0
        ZABIX_SEND = False
    Host_connect = dev_.Discovery_host()
    if Host_connect :
        if ("config" in command.lower()):
            Host_connect = dev_.Discovery_host()
            DIR = get_dir_from_hostname(dev_.Dir)
            BYTES = dev_.SaveConfig(DIR)
            HOSTNAME = dev_.Device_name
            STATUS = dev_.Status
            STATUS_INT = dev_.StatusINT
            dev_.CloseSSH()
            STR_OUT = HOSTNAME + ', ' + DIR + ', ' + IP + ', ' + str(BYTES)

except IndexError:
    STATUS = 'Need input parameter'
    STATUS_INT = 4

STR_OUT = STR_OUT + " "+STATUS +":"+str(STATUS_INT)
cmd2 = 'logger -p local5.info -t ' + str(os.path.basename(__file__)) + ' ' + STR_OUT
print (cmd2)
#subprocess.Popen(cmd2, shell = True, cwd='/usr/bin/')
if ZABIX_SEND :
    zabbix_sender(IP, STATUS_INT)


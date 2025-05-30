# -*- coding: utf-8 -*-

import re
import os, sys
import time
import threading
#import getpass
from ftplib import FTP
from datetime import datetime
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
import traceback
import filelock

def datetime_():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:23]

def print_msg(msg, FLAG=True) :
    if FLAG : logging.info(msg)
    print(f'[{datetime_()}] {msg}')

def get_arg(index):
    try               : sys.argv[index]
    except IndexError : return False
    else              : return True

def ftp_chdir(ftp,fpath):
    try : 
        for path in fpath.split('/'):
            if len(path) == 0: continue
            try :
                ftp.cwd(path)
            except Exception as ex :
                ftp.mkd(path)
                ftp.cwd(path)
        return True;
    except Exception as ex :
        return False;

# Function of ftp upload

def ftp_upload(fullpath, dirname, filename):
    # Login to ftp server.
    ftp = FTP()
    ftp.connect(host,port)
    ftp.login(username, password)
    #print_msg("Connection established.")
    # File open
    file = open(fullpath, 'rb')
    filesize = os.path.getsize(fullpath)
    # Set upload path - Server path
    #ftp.cwd(Rpath + dirname + "/")
    dirname = re.sub( r'^\/(.*)$', r'\1', dirname)
    if ftp_chdir(ftp, os.path.join(Rpath, dirname) + '/') :
        #Perform upload and Show user for progress bar
        #with tqdm(unit='blocks', unit_scale=True, leave=False, miniters=1, desc="Uploading...", total=filesize) as tqdm_instance:
        #    ftp.storbinary('STOR ' + filename, file, 20480, callback=lambda sent: tqdm_instance.update(len(sent)))
        ftp.storbinary('STOR ' + filename, file);
        print_msg(f"Remote : {os.path.join(Rpath, dirname)}, Local : {fullpath} , Upload OK !")
    # Close ftp server.
    ftp.quit()
    # Close file open().
    file.close()

# Function of FTP Account Check

def CheckAccount():
    try:
        ftp = FTP()
        ftp.connect(host=host, port=port)
        ftp.login(username, password)
        ftp.close()
        return True
    except Exception as e:
        print(e)
        ftp.close()
        print_msg("FTP close!")
        return False

def get_ref_timestamp() :
    v_now = datetime.now()
    return datetime(v_now.year, v_now.month, v_now.day, v_now.hour).timestamp()

def print_ref_timestamp(v_duration=3600) : 
    ref_timestamp = get_ref_timestamp()
    print_msg(f"Start, End : [{datetime.fromtimestamp(ref_timestamp-v_duration)}, {datetime.fromtimestamp(ref_timestamp)})")

def CheckCSVFiles(v_include):
    v_upload_all = int(get_arg(1)) # False(~3H ago) or True(ALL)
    csv_file_list = []
    v_duration = 3600

    print_ref_timestamp(v_duration)
    for file in os.walk(Lpath) :
        if len(file[2]) > 0 and sum([ re.findall(v_include,x) != [] for x in file[2] ]):
            for cfile in file[2] : 
                csv_path = '/'.join([file[0],cfile])
                file_mtime, file_size = os.path.getmtime(csv_path), os.path.getsize(csv_path)
                ref_timestamp = get_ref_timestamp()
                try    : file_ctime = datetime.strptime(re.sub('(.*)(\d{8})_(\d{6})(.*)',r'\2\3', csv_path),"%Y%m%d%H%M%S").timestamp()
                            #✅ 1. (.*) 뜻. → "아무 문자 하나"를 의미 // * → "0개 이상 반복" 그래서 .*는 **"아무 문자열이나 다 매치"**한다는 뜻 // 괄호 ( )로 감쌌으므로 1번 그룹으로 저장됨
                            # 정규식으로 날짜와 시간만 추출해서 붙이는 작업입니다.
                            # \d{8} → 날짜 (20250508)
                            # \d{6} → 시간 (152300)
                            # r'\2\3' → 두 번째 그룹(20250508) + 세 번째 그룹(152300)만 남깁니다.
                            # → 예시 결과: "20250508152300"
                except : file_ctime = os.path.getctime(csv_path)
                if re.findall(v_include,cfile) != [] and file_ctime >= (ref_timestamp - v_duration) :
                    print( f"Filtered File : {cfile}, {csv_path}, {datetime.fromtimestamp(file_ctime)}")
                    #if v_upload_all : #| (file_ctime < ref_timestamp) : 
                    csv_file_list.append([csv_path, cfile])
    print("="*100)
    for csv_file in csv_file_list :
        if not os.path.exists(csv_file[0]) : continue
        try    : dirname = csv_file[0][len(Lpath):-len(csv_file[1])]
        except : dirname = '/'
        t = threading.Thread(target=ftp_upload(csv_file[0], dirname, csv_file[1]))
        t.start()

def set_variable() : 
    global Rpath, Lpath
    global host, port, username, password

    #echo 'export EQPID="A3SPT01"' >> $HOME/.bashrc
    #os.environ['EQPID'] 
    v_EQPID = os.getenv('EQPID', 'A3_JOSOOJE_TEST') 

    # FTP server remote path & OS local path
    Rpath = f"/FTP/{v_EQPID}"
    Lpath = "/home/pi/sooje_practice"

    # Variables FTP UID, PWD
    host = "11.96.77.9"
    port = 10021
    username = "administrator"
    password = "moscon&1"
    '''
    host = "127.0.0.1"
    port = 10021
    username = "piftp"
    password = "piftp"
    '''
if __name__ == '__main__':
    v_log_file = os.path.abspath(__file__) + '.log'
    #logging.basicConfig(handlers=[logging.FileHandler(v_log_file, 'a', 'utf-8')]
    logging.basicConfig(handlers=[ RotatingFileHandler(v_log_file, maxBytes=10*1024*1024, backupCount=2, mode='a+', encoding='utf-8-sig')]
                       ,format = '[%(asctime)s.%(msecs)03d] - %(name)-15s - %(levelname)-8s - %(message)s'
                       ,datefmt = '%Y-%m-%d %H:%M:%S'
                       ,level=logging.DEBUG)
    #set the global variable 
    set_variable()

    argument = sys.argv
    proc_name = argument[0].split('/')[-1].split('\\')[-1]

    # Include extension !!
    v_include_ext = ['\.csv','\.wav','\.png']

    LOCK = filelock.FileLock(os.path.abspath(__file__) + '.lock')
    try : 
        with LOCK.acquire(timeout=1) : 
            logging.info("file lock acquired !")
            # Check FTP Account Info 
            v_flag = False
            for i in range(5) : # while True:
                # print("###### Enter the ftp ID and Password ######")
                # username = input("ID: ")
                # password = getpass.getpass(prompt="Password: ")
                if CheckAccount():
                    #print_msg("Verified!")
                    v_flag = True
                    break

                else:

                    print_msg("Please check FTP ID or Password.({0})".format(i))

                    time.sleep(3)

                    continue

            #w = Watcher()

            #w.run()

            if v_flag : 

                print_msg("Connection Successed !")

                CheckCSVFiles('|'.join(v_include_ext)); 

            else : 

                print_msg("Connection Failed !")

    

    # except filelock.Timeout as ex :

        # logging.error(f'Unable to lock - {LOCK.lock_file} : {ex}')

        # print(f'Unable to lock - {LOCK.lock_file} : {ex}')

        # LOCK.release(force=True)

        # sys.exit(1)

    

    except Exception as ex:

        #logging.error('에러발생[__main__] : {0}\n{1}'.format( ex, ''.join(traceback.TracebackException.from_exception(ex).format()) ));

        print_msg('에러발생[__main__] : {0}\n{1}'.format( ex, traceback.format_exc(limit=1) ));

        

        LOCK.release(force=True)

        sys.exit(1)





'''

##########################################################################################################################################



#from tqdm import tqdm

#from watchdog.observers import Observer

#from watchdog.events import FileSystemEventHandler





## Class of Monitoring

#class Watcher:

#    # Set Monitoring Directory

#    DIRECTORY_TO_WATCH = Lpath

#

#    def __init__(self):

#        self.observer = Observer()

#    

#    def run(self):

#        event_handler = Handler()

#        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)

#        self.observer.start()

#        print("###### Start Monitoring ######")

#        

#        try:

#            while True:

#                time.sleep(1)

#        except KeyboardInterrupt: # Ctrl + C를 누를 경우 프로세스 종료 (인터럽트)

#            self.observer.stop()

#        

#        self.observer.join()

#

#



## Class of Event Handle

#class Handler(FileSystemEventHandler):

#

#    @staticmethod

#    #def on_any_event(event): on_moved / on_modified / on_deleted / on_created

#    def on_modified(event) :

#        # Extract file extension

#        ext = os.path.splitext(event.src_path)[-1]

#        filename = event.src_path.split('/')[-1]

#        dirname = event.src_path.split('/')[-2]

#        

#        if event.is_directory:

#            return None

#        elif '.csv' in filename and '.log' not in filename and '.pos' not in filename :

#            #and (datetime.now().timestamp() - os.path.getctime(event.src_path)) >= 3600*1.0 \

#            #and (datetime.now().timestamp() - os.path.getctime(event.src_path)) <  3600*2.1 

#            # Take any action here when a file is first created.

#            #print("Received modified event - %s." % event.src_path)

#            print("Received created event - %s" % event.src_path)

#            

#            # If file extension is .csv, perform file upload.

#            t = threading.Thread(target=ftp_upload(filename, dirname, event.src_path))

#            t.start()

#        else:

#            pass

#

##########################################################################################################################################

'''


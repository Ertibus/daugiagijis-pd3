import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import threading
import math
import time

class TaskManager():
    _upd = None 
    _msg = None 

    _attribute_count = 0
    _template = "None"
    _init_path = "None"

    _is_running = False
    _is_paused = False
    _thread_lock = None

    def __init__(self, update_listener, msg_listener):
        self._upd = update_listener
        self._msg = msg_listener

    def get_init_file(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(path + " was not found")

        attributes = []
        with open(path, 'r') as file:
            lines = file.readlines()[:-1]
            self._template = "".join(lines)

            for line in lines:
                if line.isspace():
                    continue
                if(line.count("@attribute", 0, 10)):
                    attr = line.replace("@attribute ", "", 1).strip()
                    attributes.append(attr)
                    continue

        self._init_path = path
        self._attribute_count = len(attributes)
        return attributes

    def start_process(self, output_path, out_attributes):
        self._output_path = output_path
        self._output_attributes = out_attributes

        thp = threading.Thread(target=self.process_thread)
        thp.start()

    def stop_process(self):
        self.pause_process(False)
        self._is_running = False

    def lock_thread(self):
        self._thread_lock.acquire()

    def pause_process(self, pause):
        if pause:
            th = threading.Thread(target=self.lock_thread)
            th.start()
            self._is_paused = True
        else:
            self._is_paused = False
            if self._thread_lock.locked():
                self._thread_lock.release()

    def get_file_list(self):
        file_list = []
        dir_path = os.path.dirname(self._init_path)
        for file in os.listdir(dir_path):
            file_list.append(dir_path + "/" + file)
        return file_list

    def process_thread(self):
        self._is_running = True
        self._is_paused = False
        self._thread_lock = threading.Lock()
        self._upd(0)
        files = self.get_file_list()
        file_count = len(files)
        self._msg(f"Found {file_count} files.")

        partition = 1 / file_count * 100
        fin_count = 0

        with open(self._output_path, 'w') as output:
            output_struct = self._template.split('\n')

            output.write(output_struct[0])
            output.write('\n\n')
            pointer = 0
            line = " "
            while not line.count("@attribute", 0, 10):
                pointer += 1
                line = output_struct[pointer]

            for att in self._output_attributes:
                output.write(output_struct[pointer + att])
                output.write('\n')

            output.write('\n@data\n\n')
                
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = [executor.submit(self.work_file, file) for file in files]
                for data in concurrent.futures.as_completed(results):
                    if data.result() == None:
                        continue
                    if self._is_paused:
                        self._thread_lock.acquire(blocking=False)
                    output.write(",".join(data.result()))
                    output.write("\n")
                    fin_count += 1
                    self._upd(math.floor(partition * fin_count))

        self._upd(100)
        self._msg("Finished!")
        self._is_running = False
        self._is_paused = False
        
    def work_file(self, path):
        # Check for stop/pause/resume
        if not self._is_running:
            return None
        if self._is_paused:
            self._thread_lock.acquire(blocking=True)
            self._thread_lock.release()
        # Read file
        if not os.path.exists(path):
            raise FileNotFoundError(path + " was not found")
        
        ret_list = []
        with open(path, 'r') as file:
            lines = file.readlines()
            if self._template != "".join(lines[:-1]):
                self._msg('%s has a different structure then the selected arff, it will be skipped!' % path)
                return None

            variables = " "
            while variables.isspace():
                variables = lines.pop(-1)
            var_list = variables.strip().split(',')

            if self._attribute_count != len(var_list):
                self._msg('%s has a missing values for attributes, it will be skipped!' % path)
                return None

            for i in range(len(self._output_attributes)):
                ret_list.append(var_list[self._output_attributes[i]])

        return ret_list

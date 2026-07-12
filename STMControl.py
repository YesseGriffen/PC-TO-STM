import serial
import wave
import sys
import os
import time
import tkinter as tk
from tkinter import ttk
import threading
import queue
 
class LogicFunctions:
    def __init__(self):
        self.starting_com_port = "COM6"
        self.starting_baud_rate = "115200"
        self.starting_page_size = "256"
        self.starting_input_path = r"path to .wav audio file"
        self.starting_output_path = r"path to .raw converted audio file"
        self.connected = False
        self.python_transferring = False
        self.serial_connection = None
        self.python_textbox = None
        self.stm_textbox = None
        self.serial_lock = threading.Lock()
        self.python_queue = queue.Queue()
        self.stm_queue = queue.Queue()
    
    def py_print(self, input):
        self.python_queue.put(input)
    
    def stm_print(self, input):
        self.stm_queue.put(input)

    def connect_serial(self, com_port, baud_rate, python_textbox, stm_textbox):
        try:
            self.py_print(f"Action: Connecting to serial port")
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.python_textbox = python_textbox
            self.stm_textbox = stm_textbox
            self.serial_connection = serial.Serial(com_port, baud_rate, timeout=5)
            self.connected = True
            self.py_print(f"--Connected to {com_port} at {baud_rate} baud")
        except Exception as e:
            self.py_print(f"!*ERR: In connect serial")
            self.py_print(f"!*{e}")

    def stm_reader(self):
        try:
            if self.python_transferring:
                return
            if not self.connected or not self.serial_connection.is_open:
                return
            with self.serial_lock:
                self.serial_connection.timeout = 0.5
                while True:
                    line = self.serial_connection.readline().decode("utf-8", errors="replace").strip()
                    if line:
                        self.stm_print(line)
                    else:
                        break
                self.serial_connection.timeout = 5
        except Exception as e:
            self.stm_print(f"!*ERR: In serial reader")
            self.py_print(f"!*{e}")
            
    def stm_flash_jedecid(self,):
        self.py_print(f"Action: Sending 'J'(0x4A) for JedecID")
        try:
            with self.serial_lock:
                self.serial_connection.write(b'J')
            self.py_print(f"--Sent 'J' (0x4A) Successfully")
        except Exception as e:
            self.py_print(f"!*ERR:{e}")

    def audioconverter_wav_to_raw(self, input_path, file_name, output_path):
        self.py_print(f"Action: Converting wav file({file_name}) to raw file")
        input_extension = ".wav"
        input_file_path = f"{input_path}\\{file_name}{input_extension}"
        try:
            with wave.open(input_file_path, 'rb') as wf:
                self.py_print(f"--File seen at {input_file_path}")
                self.py_print(f"--Channels: {wf.getnchannels()}")
                self.py_print(f"--Sample rate: {wf.getframerate()} Hz")
                self.py_print(f"--Bit depth: {wf.getsampwidth() * 8}-bit")

                raw_data = wf.readframes(wf.getnframes())
            self.py_print(f"--Noticed wav file {file_name} sucessfully")
        except Exception as e:
            self.py_print(f"!*ERR: In audioconverter raw_to_wav input path\n{e}")
            return
        output_extension = ".raw"
        result_path = f"{output_path}\\{file_name}{output_extension}"
        try:
            with open(result_path, 'wb') as f:
                f.write(raw_data)
            self.py_print(f"--Wav to raw convert completed successfully")
            self.py_print(f"--{len(raw_data)} bytes written to {result_path}")
            return result_path
        except Exception as e:
            self.py_print(f"!*ERR: In audioconverter wav_to_raw result path\n{e}")
            return
        
    def audioconverter_raw_to_stm(self, page_size, result_path):
        page_size = int(page_size)
        self.py_print(f"Action: Pushing {result_path} to STM through UART")
        try:
            with open(result_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            self.py_print(f"!*ERR: In audioconverter raw_to_stm reading result path")
            self.py_print(f"!*{e}")
            return
        try:
            remainder = len(data) % page_size
            if remainder:
                data += b'\x00' * (page_size - remainder)
            self.py_print(f"--Last page filled with {remainder} x00")
            total_pages = len(data) // page_size
            self.py_print(f"--Total pages to send: {total_pages}")
        except Exception as e:
            self.py_print(f"!*ERR: In page calculation")
            self.py_print(f"!*{e}")
            return
        try:
            self.python_transferring = True
            with self.serial_lock:
                self.py_print(f"--Sending 'G'(0x47) for UART_Transfer")
                self.serial_connection.write(b'G')
                time.sleep(1)
                self.py_print(f"--Sending page_size bit")
                self.serial_connection.write(total_pages.to_bytes(4, byteorder="little"))
                for i in range(total_pages):
                    page = data[i * page_size:(i+1) * page_size]
                    self.serial_connection.reset_input_buffer()
                    self.serial_connection.reset_output_buffer()
                    self.serial_connection.write(page)
                    ack = self.serial_connection.read(1)
                    if ack != b'\x06':
                        self.py_print(f"!*ERR:No ACK on page {i} got: {ack}")
                        break
                    if i % 16 == 0:
                        self.py_print(f"--Page {i} / {total_pages} received")
        except Exception as e:
            self.py_print(f"!*ERR: In audioconverter raw_to_stm transfering raw file over")
            self.py_print(f"!*{e}")
        finally:
            self.python_transferring = False

    def stm_audio_playback(self):
        self.py_print(f"Action: Sending 'L'(0x4C) for audio playback")
        try:
            with self.serial_lock:
                self.serial_connection.write(b'L')
            self.py_print(f"--Sent 'L' (0x4C) Successfully")
        except Exception as e:
            self.py_print(f"!*ERR: In stm audio playback sending 'L' (0x4C)")
            self.py_print(f"!*{e}")

    def stm_chip_erase(self):
        self.py_print(f"Action: Sending 'Z'(0x5A) for chip erase")
        try:
            with self.serial_lock:
                self.serial_connection.write(b'Z')
            self.py_print(f"--Sent 'Z' (0x5A) Successfully")
        except Exception as e:
            self.py_print(f"!*ERR: In stm audio chip erase sending 'Z' (0x5A)")
            self.py_print(f"!*{e}")

    def fill_textboxes(self):
        if self.connected:
            while not self.python_queue.empty():
                self.python_textbox.append(self.python_queue.get_nowait())
            self.python_textbox.buffer_logic()
            self.stm_reader()
            while not self.stm_queue.empty():
                self.stm_textbox.append(self.stm_queue.get_nowait())
            self.stm_textbox.buffer_logic()
        
class TextState:
    def __init__(self, text_widget):
        #---------------------------------------------\ TEXT VARIABLES
        self.assigned_text_widget       = text_widget
        self.buffer                     = []
        self.error_buffer               = []
        self.buffer_maintained_count    = 0
        #---------------------------------------------/

    #---------------------------------------------\ APPEND FUNCTION
    def append(self, input):
        self.buffer                     .append(input)
    #---------------------------------------------/
    #---------------------------------------------\ RESET FUNCTION
    def reset(self):
        self.buffer                     = []
        self.error_buffer               = []
    #---------------------------------------------/
    #---------------------------------------------\ RESET MAINTAINED FUNCTION
    def reset_maintained(self):
        if self.buffer_maintained_count > 14:
            self.assigned_text_widget       .delete("1.0", tk.END)
            self.buffer_maintained_count    = 0
    #---------------------------------------------/
    #---------------------------------------------\ BUFFER LOGIC FUNCTION
    def buffer_logic(self):
        self.reset_maintained()
        for buffer in self.buffer:
            self.buffer_maintained_count    += 1
            if buffer[0:2] == "ERR":
                self.error_buffer.append(buffer)
            self.assigned_text_widget.insert(tk.END, buffer + "\n")
        
        self.reset()
    #---------------------------------------------/
    #---------------------------------------------\ DUDLER LEN FUNCTION
    def __len__(self, maintained=False):
        if maintained:
            return                          self.buffer_maintained_count
        else:
            return                          len(self.buffer)
    #---------------------------------------------/

class Frame:
    def __init__(self, root:tk.Tk=None, frame_type:str="Frame", text:str=None):
        match frame_type:
            case "Frame":
                self.frame                      = tk.Frame(master=root)
            case "LabelFrame":
                self.frame                      = tk.LabelFrame(master=root, text=text, padx=10, pady=10)
        self.widgets                    = []

class Panel:
    def __init__(self, root:tk.Tk=None, text:str=None):
        self.panel                      = tk.LabelFrame(master=root, text=text, padx=10, pady=10)
        self.check                      = tk.BooleanVar(value=False)
        self.prev_check                 = tk.BooleanVar(value=False)
        self.widgets                    = []

class WorkSpace:
    def __init__(self):
        #---------------------------------------------\ ROOT SETUP
        self.root                       = tk.Tk()
        self.root                       .title("STM32 Dashboard")
        #---------------------------------------------/
        #---------------------------------------------\ FRAME VARIABLES
        self.frames                     = {"Controls": Frame(root=self.root, frame_type="LabelFrame", text="Panel Controller"),
                                           "WorkSpace": Frame(root=self.root, frame_type="Frame")
                                           }
        #---------------------------------------------/
        #---------------------------------------------\ PANEL VARIABLES
        self.cur_panel_row              = 0
        self.cur_panel_col              = 0
        self.raw_result_path            = tk.StringVar(value="")
        self.panels                     = {"AudioConverter": Panel(root=self.frames["WorkSpace"].frame, text="Audio Converter"),
                                           "PrintOutput": Panel(root=self.frames["WorkSpace"].frame, text="Print Display"),
                                           "TestAction": Panel(root=self.frames["WorkSpace"].frame, text="Test Action")
                                           }
        #---------------------------------------------/
        #---------------------------------------------\ LOGIC CONTROLLER VARIABLE
        self.logic                      = LogicFunctions()
        #---------------------------------------------/
        #---------------------------------------------\ WIDGET CREATION FUNCTION
        self.widget_creation()
        #---------------------------------------------/

    def fit_logic(self, action:str=None):
        match action:
            case "SerialConnect":
                self.logic.connect_serial(com_port=self.frames["Controls"].widgets[0][2].get(),
                                        baud_rate=self.frames["Controls"].widgets[0][4].get(),
                                        python_textbox=self.panels["PrintOutput"].widgets[3][1][1],
                                        stm_textbox=self.panels["PrintOutput"].widgets[3][2][1])
            
            case "JedecID":
                def run():
                    self.logic.stm_flash_jedecid()
                threading.Thread(target=run, daemon=True).start()
            case "WavToRaw":
                def run():
                    result = self.logic.audioconverter_wav_to_raw(input_path=self.panels["AudioConverter"].widgets[0][2].get(),
                                                                file_name=self.panels["AudioConverter"].widgets[0][4].get(),
                                                                output_path=self.panels["AudioConverter"].widgets[0][6].get())
                    self.raw_result_path.set(result)
                threading.Thread(target=run, daemon=True).start()
            case "RawToSTM":
                def run():
                    self.logic.audioconverter_raw_to_stm(page_size=self.frames["Controls"].widgets[0][6].get(),
                                                         result_path=self.raw_result_path.get())
                threading.Thread(target=run, daemon=True).start()
            case "AudioPlayback":
                def run():
                    self.logic.stm_audio_playback()
                threading.Thread(target=run, daemon=True).start()
            case "ChipErase":
                def run():
                    self.logic.stm_chip_erase()
                threading.Thread(target=run, daemon=True).start()

    def toggle_panels(self):
        def correct_panel_pos(mode):
            if mode == 1: self.cur_panel_col += 1
            elif mode == -1: self.cur_panel_col -= 1 if self.cur_panel_col > 0 else 0
            if self.cur_panel_col % 3 == 0:
                self.cur_panel_row += 1
                self.cur_panel_col = 0

        for panel in self.panels:
            panel = self.panels[panel]
            if panel.check.get():
                panel.panel.grid(row=self.cur_panel_row, column=self.cur_panel_col)
                correct_panel_pos(1)
            else:
                panel.panel.grid_forget()
                correct_panel_pos(-1)

    def widget_creation(self):
        def set_entry(master, default="", width=10):
            entry = tk.Entry(master=master, width=width)
            if default:
                entry.insert(0, default)
            return entry
            
        def create_text(master, serial_on=False, height=70, width=10, font=("TkDefaultFont", 7)):
            text_box = tk.Text(master=master, height=height, width=width, font=font)
            text_box_state = TextState(text_widget=text_box)
            return (text_box, text_box_state)
        
        root = self.frames["Controls"].frame
        self.frames["Controls"].widgets = [
            [
                "entries",
                tk.Label(master=root, text="COM Port", width=10),
                set_entry(master=root, default=self.logic.starting_com_port, width=10),
                tk.Label(master=root, text="Baud Rate", width=10),
                set_entry(master=root, default=self.logic.starting_baud_rate, width=10),
                tk.Label(master=root, text="Page Size", width=10),
                set_entry(master=root, default=self.logic.starting_page_size, width=10)
            ],
            [
                "checks",
                tk.Checkbutton(master=root, text="Audio", variable=self.panels["AudioConverter"].check, command=self.toggle_panels, padx=5, pady=5),
                tk.Checkbutton(master=root, text="Print", variable=self.panels["PrintOutput"].check, command=self.toggle_panels, padx=5, pady=5),
                tk.Checkbutton(master=root, text="Test", variable=self.panels["TestAction"].check, command=self.toggle_panels, padx=5, pady=5)
            ],
            [
                "buttons",
                tk.Button(master=root, text="Connect", width=15, command=lambda: self.fit_logic(action="SerialConnect")),
                tk.Button(master=root, text="Quit", width=15, command=self.root.destroy)
            ],
            [
                "texts"
            ]
        ]
        root = self.panels["AudioConverter"].panel
        self.panels["AudioConverter"].widgets = [
            [
                "entries",
                tk.Label(master=root, text="Input Path", width=10),
                set_entry(master=root, default=self.logic.starting_input_path, width=50),
                tk.Label(master=root, text="File Name", width=10),
                set_entry(master=root,  default="", width=50),
                tk.Label(master=root, text="Output Path", width=10),
                set_entry(master=root, default=self.logic.starting_output_path, width=50),
                tk.Label(master=root, text="Result Path", width=10),
                tk.Label(master=root, textvariable=self.raw_result_path, width=50)
            ],
            [
                "checks"
            ],
            [
                "buttons",
                tk.Button(master=root, text="Wav -> Raw", width=15, command=lambda: self.fit_logic(action="WavToRaw")),
                tk.Button(master=root, text="Raw -> STM32", width=15, command=lambda: self.fit_logic(action="RawToSTM"))
            ],
            [
                "texts"
            ]
        ]
        root = self.panels["PrintOutput"].panel
        self.panels["PrintOutput"].widgets = [
            [
                "entries",
                tk.Label(master=root, text="Python Output", width=15),
                tk.Label(master=root, text="STM32 Output", width=15)
            ],
            [
                "checks"
            ],
            [
                "buttons"
            ],
            [
                "texts",
                create_text(master=root, serial_on=False, height=10, width=70, font=("TkDefaultFont", 7)),
                create_text(master=root, serial_on=True, height=10, width=70, font=("TkDefaultFont", 7))
            ]
        ]
        root = self.panels["TestAction"].panel
        self.panels["TestAction"].widgets = [
            [
                "entries"
            ],
            [
                "checks"
            ],
            [
                "buttons",
                tk.Button(master=root, text="Recall JedecID", width=15, command=lambda: self.fit_logic(action="JedecID")),
                tk.Button(master=root, text="Playback Audio", width=15, command=lambda: self.fit_logic(action="AudioPlayback")),
                tk.Button(master=root, text="Chip Erase", width=15, command=lambda: self.fit_logic(action="ChipErase"))
            ],
            [
                "texts"
            ],
        ]

        def correct_element_pos(master_name:str, widget_name:str, widget_len:int, idx:int, pos:tuple):
            cpos = [pos[0], pos[1]]
            new_pos = [0, 0]

            if widget_name == "entries" or widget_name == "texts":
                if idx % 2 != 0:
                    cpos[1] += 1
                else:
                    if cpos[1] != 0:
                        cpos[1] -= 1
                        cpos[0] += 1
                new_pos = [cpos[0], cpos[1]]
                
                
            if widget_name == "checks":
                if idx % 2 == 0:
                    cpos[0] += 1
                    cpos[1] = 0
                else:
                    cpos[1] += 1
                new_pos = [cpos[0], cpos[1]]
            
            if widget_name == "buttons":
                if idx % 2 == 0:
                    cpos[0] += 1
                    cpos[1] = 0
                else:
                    cpos[1] += 1
                new_pos = [cpos[0], cpos[1]]



            return (new_pos)

            
        current_frame_row = 0
        current_frame_col = 0
        for frame_key in self.frames:
            element_pos = (0, 0)
            frame = self.frames[frame_key]
            frame.frame.grid(row=current_frame_row, column=current_frame_col)
            current_frame_col += 1
            for widget in frame.widgets:
                for i, element in enumerate(widget[1:]):
                    element_pos = correct_element_pos(master_name=frame_key, widget_name=widget[0], widget_len=len(widget), idx=i, pos=element_pos)
                    if isinstance(element, tuple):
                        element[0].grid(row=element_pos[0], column=element_pos[1])
                    else:
                        element.grid(row=element_pos[0], column=element_pos[1])

        for panel_key in self.panels:
            element_pos = (0, 0)
            panel = self.panels[panel_key]
            for widget in panel.widgets:
                for i, element in enumerate(widget[1:]):
                    element_pos = correct_element_pos(master_name=panel_key, widget_name=widget[0], widget_len=len(widget), idx=i, pos=element_pos)
                    if isinstance(element, tuple):
                        element[0].grid(row=element_pos[0], column=element_pos[1])
                    else:
                        element.grid(row=element_pos[0], column=element_pos[1])

    def on_loop(self):
        self.logic.fill_textboxes()
        self.root.after(500, self.on_loop)
      
    def __call__(self):
        self.root.after(500, self.on_loop)
        self.root.mainloop()

if __name__ == '__main__':
    workspace = WorkSpace()
    workspace()

# PC-TO-STM

*This is not complete and is rough in terms of readability and overall code efficieny*

(Interface between Computer and STM32)

This program uses Python with tkinter for a basic gui.
This program has two main uses:
  1. Ability to send commands to the STM32 through USART protocol.
  2. Ability to receive messages, commands from the STM32 to the Computer through USART protocol.

Notes about my setup in particular:
  -My use case is using a NUCLEO-STM32H7A3ZIQ. With other boards like a W25Q128 flash chip, MAX98357A Amp.  
  -For transmitting and receiving between my Computer and the STM32, I use the ST-LINK which is CN1 on this NUCLEO.  
  -Through CubeMX, tt may be needed to turn off VCOM and manually turn on USART3, VCOM may slow down transfers and can mess with timing overall.  
  
  

Some of the code is designed for my use case, most of the functions in "LogicFunctions" for example, and what buttons/entries I use.  
The structure of the code:  
  1. WorkSpace Class is where all tkinter widgets get placed, to add widgets, you need to specify the frame or panel then it is recommended to place entries in the entries array and etc.  
    Defining the widget is all you need to do. I am experimeting with an auto-grider that is basic and does have some flaws as of now. So once you define a widget, that is all you need to do.  
  2. To add actions, you would need to first create the necessary function in "LogicFunctions", then in "fit_logic" under WorkSpace, we redefine it in fit_logic to add threading and effect anything else that changes after the function like a variable being returned, etc.  
     In my example I have a panel called "TestAction" that just has buttons on it for me to press and send commands for example.  
     A simple example of a function is:  
     def stm_flash_jedecid(self):  
        self.py_print(f"Action: Sending 'J'(0x4A) for JedecID")  
        try:  
            with self.serial_lock:  
                self.serial_connection.write(b'J')  
            self.py_print(f"--Sent 'J' (0x4A) Successfully")  
        except Exception as e:  
            self.py_print(f"!*ERR:{e}")  
  
     Then in fit_logic:  
       case "JedecID":  
              def run():  
                  self.logic.stm_flash_jedecid()  
              threading.Thread(target=run, daemon=True).start()  
  
     Then in a panel/frame:  
       tk.Button(master=root, text="Recall JedecID", width=15, command=lambda: self.fit_logic(action="JedecID"))  
       
     When I press this button, I am sending the letter 'J' or (0x4A) to the STM32, in my STM32 I have a switch statement that looks for incoming bytes through USART, and once it picks up 'J' it will go through a function to retrieve the JEDECID from my flash chip and        print it back to my computer through the tkinter GUI.  

# LeafCNC Application

# Import Libraries and Modules
import tkinter

from tkinter import *
from tkinter import ttk, messagebox, filedialog


# Functions to Move CNC Head

# Functions to Control Camera

# Create Config File and Variables

# XML Management Functions


# Tkinter Application Overview
class LeafCNC:
	def __init__(self):
		self.tk = Tk()
		self.tk.attributes('-fullscreen',True)
		self.tk.title("LeafCNC Controller")
		self.frame = Frame(self.tk)
		self.frame.pack(side="top", fill="both", expand = True)
		self.frame.grid_rowconfigure(0, weight=1)
		self.frame.grid_columnconfigure(0, weight=1)
		self.state = False
		self.tk.bind("<F11>", self.toggle_fullscreen)
		self.tk.bind("<Escape>", self.end_fullscreen)

		self.frames = {}
		FrameList = ()
		
		for F in FrameList:
			frame = F(self.frame, self)
			self.frames[F] = frame
			frame.grid(row=0, column=0, sticky="nsew")
		
		self.show_frame(StartPage, Settings, SampleDetails, Initilization, RunSample)
	
		
	def show_frame(self, cont):
		frame = self.frames[cont]
		frame.tkraise()

	def toggle_fullscreen(self, event=None):
		self.state = not self.state
		self.tk.attributes("-fullscreen", self.state)
		return "break"
		
	def end_fullscreen(self, event=None):
		self.state = False
		self.tk.attributes("-fullscreen", False)
		return "break"

	def go_fullscreen(self, event=None):
		self.state = True
		self.tk.attributes("-fullscreen", True)
		return "break"
		
	def quitProgram(self, event=None):
# 		Kill Camera Ports and IDX
# 		config["cam1"]["port"] = "null"
# 		config["cam2"]["port"] = "null"
# 		config["cam3"]["port"] = "null"
# 		config["cam4"]["port"] = "null"
# 		config["cam1"]["idx"] = "null"
# 		config["cam2"]["idx"] = "null"
# 		config["cam3"]["idx"] = "null"
# 		config["cam4"]["idx"] = "null"
# 		config["cam1"]["code"] = ""
# 		config["cam2"]["code"] = ""
# 		config["cam3"]["code"] = ""
# 		config["cam4"]["code"] = ""
# 		updateConfig(config, configpath)
# 		
# 		Kill Test Images
# 		for cam in camList:
# 			killTestImage(cam)
# 		
# 		turnOffMotors()
# 		
# 		exit()
		return "break"

# Start Page Class
class StartPage(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)

		# Size Columns
		self.grid_columnconfigure(1, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="Leaf CNC Controller", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")


# Settings Class
class Settings(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)

		# Size Columns
		self.grid_columnconfigure(1, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="Controller Settings", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")


# Sample Details Class
class SampleDetails(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)

		# Size Columns
		self.grid_columnconfigure(1, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="Sample Details", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")


# Initilization class
class Initilization(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)

		# Size Columns
		self.grid_columnconfigure(1, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="System Initilization", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")


# Run Sample Class
class RunSample(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)

		# Size Columns
		self.grid_columnconfigure(1, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="Run Sample", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")



#RunApplication Start

app = LeafCNC()

app.tk.mainloop() 
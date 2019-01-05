#!/usr/bin/python3

# LeafCNC Application

# Import Libraries and Modules
import tkinter, configparser, os, serial, time

from gpiozero import LED
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# Global Variables
configpath = os.path.dirname(os.path.abspath(__file__))+"/config.ini"

# Stores info about the status of all components of system
systemStatus = {}

# Stores details about active sessionData
sessionData = {}  

cameraStatusUpdateText = ""	

# CNC Positions
xPos = 0
yPos = 0


# Display Constants
LARGE_FONT = ("Verdana", 16)
MED_FONT = ("Verdana", 12)
SMALL_FONT = ("Verdana", 9)


# GPIO Pin Settings
focus = LED(17)
shutter = LED(24)


# Functions to Move CNC Machine

def moveCNC(dx,dy, machine):
	global xPos
	global yPos
	xPos = xPos + dx
	yPos = yPos + dy
	msg = 'G0 X'+str(xPos)+' Y'+str(yPos)+'\n'
	print(str(msg))
	machine.write(msg.encode())
	responseString = machine.readline().decode()
	print("Response: "+str(responseString))
	return responseString
	 
def openCNC(port):
	machine = serial.Serial(port,115200)
	return machine

def closeCNC(machine):
	machine.close()
	return True

def setCNCOrigin():
	global machine
	global xPos
	global yPos
	closeCNC(machine)
	machine = openCNC(config["cnc"]["port"])
	xPos = 0
	yPos = 0

# Functions to Control Camera

# Create Config File and Variables
def createConfig(path):
	# Create config file
	config = configparser.ConfigParser()
	
	config["cnc"] = {"port": "/dev/ttyUSB0", "xOverlap": "40", "yOverlap":"40", "pauseLength":"1"}
	config["camera"] = {"body": "Canon T1i", "lens": "Tokina 100mm", "trigger":"USB", "exposure":"1"}
	config["filepaths"] = {"download":"True", "imagePath":'', "xmlPath": ''}
	
	# Write Config file
	with open(path, "w") as config_file:
		config.write(config_file)

def getConfig(path):
	if not os.path.exists(path):
		createConfig(path)
	
	config = configparser.ConfigParser()
	config.read(path)
	return config

def updateConfig(config, path):
	with open(path, "w") as config_file:
		config.write(config_file)




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
		FrameList = (StartPage, Settings, SampleDetails, Initilization, RunSample)
		
		for F in FrameList:
			frame = F(self.frame, self)
			self.frames[F] = frame
			frame.grid(row=0, column=0, sticky="nsew")
		
		self.show_frame(StartPage)
	
		
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
		self.grid_columnconfigure(10, minsize=50)
		self.grid_columnconfigure(12, minsize=50)
		self.grid_columnconfigure(14, minsize=50)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(10, minsize=50)
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="Leaf CNC Controller", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")
		
		
		# Buttons
		btnInit = ttk.Button(self, text="Initilization", command=lambda: controller.show_frame(Initilization))
		btnInit.grid(row=10, column=10, sticky="NEWS")
		btnRunSample = ttk.Button(self, text="Run Sample", command=lambda: controller.show_frame(RunSample))
		btnRunSample.grid(row=10, column=12, sticky="NEWS")
		btnSettings = ttk.Button(self, text="Settings", command=lambda: controller.show_frame(Settings))
		btnSettings.grid(row=10, column=14, sticky="NEWS")
		

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
		btnStartPage.grid(row=100, column=1, sticky="WE")

		btnQuit = ttk.Button(self, text="Quit", command=controller.quitProgram)
		btnQuit.grid(row=100, column=6, sticky="EW")


# Settings Class
class Settings(tkinter.Frame):
	def __init__(self, parent, controller):
		tkinter.Frame.__init__(self,parent)
		
		# Variables
		self.cameraBody = StringVar()
		self.cameraBody.set(config['camera']['body'])
		self.lens = StringVar()
		self.lens.set(config['camera']['lens'])
		self.triggerMethod = StringVar()
		self.triggerMethod.set(config['camera']['trigger'])
		self.exposureLength = StringVar()
		self.exposureLength.set(str(config['camera']['exposure']))
		self.xOverlap = IntVar()
		self.xOverlap.set(config['cnc']['xOverlap'])
		self.yOverlap = IntVar()
		self.yOverlap.set(config['cnc']['yOverlap'])
		self.pauseLength = StringVar()
		self.pauseLength.set(config['cnc']['pauseLength'])
		self.download = BooleanVar()
		self.download.set(config['filepaths'].getboolean("download"))
		self.imagePath = StringVar()
		self.imagePath.set(config['filepaths']['imagePath'])
		self.xmlPath = StringVar()
		self.xmlPath.set(config['filepaths']['xmlPath'])
		
		# Size Columns
		self.grid_columnconfigure(1, minsize=50)
		self.grid_columnconfigure(10, minsize=100)
		self.grid_columnconfigure(11, minsize=200)
		self.grid_columnconfigure(12, minsize=25)
		self.grid_columnconfigure(19, minsize=50)
		self.grid_columnconfigure(20, minsize=100)
		self.grid_columnconfigure(21, minsize=200)
		self.grid_columnconfigure(99, minsize=50)
		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(99, minsize=20)
		self.grid_rowconfigure(10, minsize=50)
		self.grid_rowconfigure(11, minsize=20)
		self.grid_rowconfigure(10, minsize=50)
		self.grid_rowconfigure(12, minsize=20)
		self.grid_rowconfigure(13, minsize=50)
		self.grid_rowconfigure(14, minsize=20)
		self.grid_rowconfigure(15, minsize=50)
		self.grid_rowconfigure(16, minsize=20)
		self.grid_rowconfigure(17, minsize=50)
		self.grid_rowconfigure(18, minsize=20)
		self.grid_rowconfigure(19, minsize=50)

		self.grid_rowconfigure(20, minsize=20)
		self.grid_rowconfigure(21, minsize=50)
		self.grid_rowconfigure(22, minsize=20)
		self.grid_rowconfigure(23, minsize=50)
		self.grid_rowconfigure(24, minsize=20)
		self.grid_rowconfigure(25, minsize=50)
		self.grid_rowconfigure(26, minsize=20)
		self.grid_rowconfigure(27, minsize=50)
		
		# Page Title
		pageTitle = ttk.Label(self, text="LeafCNC Settings", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")


		# Camera Settings
		lblCameraBody = ttk.Label(self, text="Camera Body", font=MED_FONT)
		cmbCameraBody = ttk.Combobox(self, textvariable=self.cameraBody, width=10)
		cmbCameraBody['values'] = ["Canon T1i"]
		lblCameraBody.grid(row=10, column=10, sticky="WE")
		cmbCameraBody.grid(row=10, column=11, sticky="WE")
		lblLens = ttk.Label(self, text="Lens", font=MED_FONT)
		cmbLens = ttk.Combobox(self, textvariable=self.lens, width=10)
		cmbLens['values'] = ["Tokina 100"]
		lblLens.grid(row=12, column=10, sticky="WE")
		cmbLens.grid(row=12, column=11, sticky="WE")
		lblTriggerMethod = ttk.Label(self, text="Trigger Method", font=MED_FONT)
		cmbTriggerMethod = ttk.Combobox(self, textvariable=self.triggerMethod, width=10)
		cmbTriggerMethod['values'] = ["USB","Cable Release"]
		lblTriggerMethod.grid(row=14, column=10, sticky="WE")
		cmbTriggerMethod.grid(row=14, column=11, sticky="WE")
		lblExposure = ttk.Label(self, text="Exposure Length (s)", font=MED_FONT)
		entryExposure = ttk.Entry(self, textvariable=self.exposureLength, width=5)
		lblExposure.grid(row=16, column=10, sticky="WE")
		entryExposure.grid(row=16, column=11, sticky="WE")
		
		# CNC Settings
		lblxOverlap = ttk.Label(self, text="X-Axis Overlap (%)", font=MED_FONT)
		entryxOverlap = ttk.Entry(self, textvariable=self.xOverlap, width=5)
		lblxOverlap.grid(row=10, column=20, sticky="WE")
		entryxOverlap.grid(row=10, column=21, sticky="WE")
		lblyOverlap = ttk.Label(self, text="Y-Axis Overlap (%)", font=MED_FONT)
		entryyOverlap = ttk.Entry(self, textvariable=self.yOverlap, width=5)
		lblyOverlap.grid(row=12, column=20, sticky="WE")
		entryyOverlap.grid(row=12, column=21, sticky="WE")
		lblPause = ttk.Label(self, text="Pause Length (s)", font=MED_FONT)
		entryPause = ttk.Entry(self, textvariable=self.pauseLength, width=5)
		lblPause.grid(row=14, column=20, sticky="WE")
		entryPause.grid(row=14, column=21, sticky="WE")

		# File Paths
		folderIcon = ImageTk.PhotoImage(Image.open("/home/pi/leafcnc/backend/folderIcon-small.png"))
		lblDownloadFiles = ttk.Label(self, text="Download Files from Camera", font=MED_FONT)
		lblDownloadFiles.grid(row=20, column=10, sticky="EW")
		chkDownloadFiles = ttk.Checkbutton(self, var=self.download, onvalue=True, offvalue=False, command=lambda: [self.updateVariable()] )
		chkDownloadFiles.grid(row=20, column=11, sticky="EW")
		lblImagePath = ttk.Label(self, text="Image Storage Path", font=MED_FONT)
		lblImagePath.grid(row=22, column=10, sticky="EW")
		fileImagePath = ttk.Entry(self, textvariable=self.imagePath, width=30)
		fileImagePath.grid(row=22, column=11, sticky="EW")
		btnImagePath = ttk.Button(self, image=folderIcon, command=lambda: selectDirectory(self.imagePath))
		btnImagePath.image = folderIcon
		btnImagePath.grid(row=22, column=12, sticky="W")
		lblxmlPath = ttk.Label(self, text="XML Storage Path", font=SMALL_FONT)
		lblxmlPath.grid(row=24, column=10, columnspan=2, sticky="EW")
		filexmlPath = ttk.Entry(self, textvariable=self.xmlPath, width=30)
		filexmlPath.grid(row=24, column=11, sticky="EW")
		btnxmlPath = ttk.Button(self, image=folderIcon, command=lambda: selectDirectory(self.xmlPath))
		btnxmlPath.image = folderIcon
		btnxmlPath.grid(row=24, column=12, sticky="W")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Save", command=lambda: [self.updateVariable(), controller.show_frame(StartPage)])
		btnStartPage.grid(row=100, column=1, sticky="WE")

		
	def updateVariable(self, event=None):
		config['camera']['body'] = str(self.cameraBody.get())
		config['camera']['lens'] = str(self.lens.get())
		config['camera']['trigger'] = str(self.triggerMethod.get())
		config['camera']['exposure'] = str(self.exposureLength.get())
		config['cnc']['xOverlap'] = str(self.xOverlap.get())
		config['cnc']['yOverlap'] = str(self.yOverlap.get())
		config['cnc']['Pause'] = str(self.pauseLength.get())
		config['filepaths']['download'] = str(self.download.get())
		config['filepaths']['imagePath'] = str(self.imagePath.get())
		config['filepaths']['xmlPath'] = str(self.xmlPath.get())
		updateConfig(config, configpath)


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
		
		# Global Variables
		global machine
		
		# Size Columns
		self.grid_columnconfigure(1, minsize=34)
		
		self.grid_columnconfigure(10, minsize=20)
		self.grid_columnconfigure(11, minsize=10)
		self.grid_columnconfigure(12, minsize=5)
		self.grid_columnconfigure(13, minsize=20)
		self.grid_columnconfigure(14, minsize=5)
		self.grid_columnconfigure(15, minsize=10)
		self.grid_columnconfigure(16, minsize=20)
		
		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		
		self.grid_rowconfigure(10, minsize=20)
		self.grid_rowconfigure(11, minsize=10)
		self.grid_rowconfigure(12, minsize=5)
		self.grid_rowconfigure(13, minsize=20)
		self.grid_rowconfigure(14, minsize=5)
		self.grid_rowconfigure(15, minsize=10)
		self.grid_rowconfigure(15, minsize=20)
		
		self.grid_rowconfigure(99, minsize=20)

		# Page Title
		pageTitle = ttk.Label(self, text="System Initilization", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")

		# CNC Initilization Buttons
		btnCNCUpSmall = ttk.Button(self, text="Up5", command=lambda: moveCNC(0, 5, machine))
		btnCNCUpMed = ttk.Button(self, text="Up50", command=lambda: moveCNC(0, 50, machine))
		btnCNCUpLarge = ttk.Button(self, text="Up100", command=lambda: moveCNC(0, 100, machine))
		btnCNCLeftSmall = ttk.Button(self, text="Left5", command=lambda: moveCNC(-5, 0, machine))
		btnCNCLeftMed = ttk.Button(self, text="Left50", command=lambda: moveCNC(-50, 0, machine))
		btnCNCLeftLarge = ttk.Button(self, text="Left100", command=lambda: moveCNC(-100, 0, machine))
		btnCNCDownSmall = ttk.Button(self, text="Down5", command=lambda: moveCNC(0, -5, machine))
		btnCNCDownMed = ttk.Button(self, text="Down50", command=lambda: moveCNC(0, -50, machine))
		btnCNCDownLarge = ttk.Button(self, text="Down100", command=lambda: moveCNC(0, -100, machine))
		btnCNCRightSmall = ttk.Button(self, text="Right5", command=lambda: moveCNC(5, 0, machine))
		btnCNCRightMed = ttk.Button(self, text="Right50", command=lambda: moveCNC(50, 0, machine))
		btnCNCRightLarge = ttk.Button(self, text="Right100", command=lambda: moveCNC(100, 0, machine))
	
		
		btnSetOrigin = ttk.Button(self, text="Set Origin", command=lambda: setCNCOrigin())
		
		btnCNCUpLarge.grid(row=10, column=13, sticky="NEWS")
		btnCNCUpMed.grid(row=11, column=13, sticky="NEWS")
		btnCNCUpSmall.grid(row=12, column=13, sticky="NEWS")
		btnCNCLeftLarge.grid(row=13, column=10, sticky="NEWS")
		btnCNCLeftMed.grid(row=13, column=11, sticky="NEWS")
		btnCNCLeftSmall.grid(row=13, column=12, sticky="NEWS")
		btnCNCDownLarge.grid(row=16, column=13, sticky="NEWS")
		btnCNCDownMed.grid(row=15, column=13, sticky="NEWS")
		btnCNCDownSmall.grid(row=14, column=13, sticky="NEWS")
		btnCNCRightLarge.grid(row=13, column=16, sticky="NEWS")
		btnCNCRightMed.grid(row=13, column=15, sticky="NEWS")
		btnCNCRightSmall.grid(row=13, column=14, sticky="NEWS")
		btnSetOrigin.grid(row=13, column=13, sticky="NEWS")
		

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


	# Order of Operations
		# Initilization Checks
			# Check for Initilization of Table
			# Check for Initilization of Camera
			# Check for Storage Destination
			# Check Camera Settings are not for White Frame
			# Check to make sure XML file doesn't already exist
		# Confirm Sample ID
		# Begin Sampling Run
			# Initiate XML
			# Move Camera to Origin
			# Capture White Frame
			# Calculate Frame Positions
			# Begin Sampling Loop
				# Move Camera to next position
				# Pause for Image Delay
				# Capture Frame
		# Begin Post Processing
			# Download Files from Camera
			# Rename Files
			# Save XML Data
		# Return Camera to Origin
		# Display Completion Window
		# Play Sound
		
			
		

config = getConfig(configpath)
machine = openCNC(config["cnc"]["port"])

#RunApplication Start
app = LeafCNC()

app.tk.mainloop() 
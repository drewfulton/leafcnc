#!/usr/bin/python3

# LeafCNC Application

# Import Libraries and Modules
import tkinter, configparser, os, serial, time, threading, pygame, datetime, math, io
import gphoto2 as gp

from gpiozero import LED
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from multiprocessing.dummy import Pool as ThreadPool
from lxml import etree as ET

# Global Variables
configpath = os.path.dirname(os.path.abspath(__file__))+"/config.ini"
parser = ET.XMLParser(remove_blank_text=True)

# Stores info about the status of all components of system
systemStatus = {}
status = {}
liveViewActive = False
liveViewEvents = {}
# Stores details about active sessionData
sessionData = {}  
imageCount = 1
globalPosition = None
cameraStatusUpdateText = ""	

# CNC Positions
xPos = 0
yPos = 0

XMAX = 200 #should actually be 360 but just testing to avoid the circuit board
YMAX = 470

rateOfTravel = 100 #mm/s
# Display Constants
LARGE_FONT = ("Verdana", 16)
MED_FONT = ("Verdana", 12)
SMALL_FONT = ("Verdana", 9)


# GPIO Pin Settings
focus = LED(17)
shutter = LED(24)


# Functions to Move CNC Machine

def moveCNCbyAmount(dx,dy, machine):
	global xPos
	global yPos
	xPos = xPos + dx
	yPos = yPos + dy
	msg = 'G0 X'+str(xPos)+' Y'+str(yPos)+'\n'
# 	print(str(msg))
	machine.write(msg.encode())
	responseString = machine.readline().decode()
# 	print("Response: "+str(responseString))
	return responseString
	 
def moveCNCtoCoordinates(x, y, machine):
	global xPos
	global yPos
	xPos = x
	yPos = y
	msg = 'G0 X'+str(xPos)+' Y'+str(yPos)+'\n'
# 	print(str(msg))
	machine.write(msg.encode())
	responseString = machine.readline().decode()
# 	print("Response: "+str(responseString))
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
def listFiles(camera, context, path='/'):
    result = []
    # get files
    for name, value in camera.folder_list_files(path, context):
        result.append(os.path.join(path, name))
    # read folders
    folders = []
    for name, value in camera.folder_list_folders(path, context):
        folders.append(name)
    # recurse over subfolders
    for name in folders:
        result.extend(listFiles(camera, context, os.path.join(path, name)))
    return result

def get_file_info(camera, context, path):
    folder, name = os.path.split(path)
    return camera.file_get_info(folder, name, context)

def triggerDarkFrame():
	# Take Sample Image from Camera
	# Connect to Camera
	context = gp.Context()
	camera = initCamera(context)		
	# Get Image Size/Type Settings from Camera
	camConfig = camera.get_config(context) 
	camSettings = {}
	iso = camConfig.get_child_by_name("iso") 
	camSettings["iso"] = iso.get_value()
	shutterspeed = camConfig.get_child_by_name("shutterspeed") 
	camSettings["shutterspeed"] = shutterspeed.get_value()
# 	exposurecompensation = camConfig.get_child_by_name("exposurecompensation")			
# 	camSettings["exposurecompensation"] = exposurecompensation.get_value()
	# Set Camera to 128000 ISO at 1" exposure with +5 exposure compensation
	iso.set_value("100")
	shutterspeed.set_value("1/4000")
# 	exposurecompensation.set_value("5.0")
	camera.set_config(camConfig, context)
	# Capture Image
	filePath = camera.capture(gp.GP_CAPTURE_IMAGE, context)
	# Restore Original Size/Type Settings to Camera
	iso.set_value(camSettings["iso"])
	shutterspeed.set_value(camSettings["shutterspeed"])
# 	exposurecompensation.set_value(camSettings["exposurecompensation"])
	camera.set_config(camConfig, context)
	
	# Exit Camera
	camera.exit(context)
# 	print (filePath.name)
	return (filePath.name)

def triggerImageUSB():
		
	# Connect to Camera
	context = gp.Context()
	camera = initCamera(context)		

	# Capture Image
	filePath = camera.capture(gp.GP_CAPTURE_IMAGE, context)
	
	
	
	camera.exit(context)
		
	return (filePath)
		
def triggerImageCable(imageData):   
		global focus
		global shutter				
		global rolledOver
		focus.on()
		time.sleep(0.25)
		shutter.on()
		time.sleep(0.5)
		shutter.off()
		time.sleep(0.1)
		focus.off()
		
		# Calculate Filename
		for cam in imageData:
			cameraNumber, rotation, positionCount, positionDegree, whiteFrameFilename = cam
			whiteFrameNumber = int(whiteFrameFilename[-8:-4])
			if rolledOver[cameraNumber]:
				positionCount += 1
			currentFrameNumber = str(whiteFrameNumber + int(positionCount))[-4:].zfill(4)
			if currentFrameNumber == "0000":
				rolledOver[cameraNumber] = True
				currentFrameNumber = str(int(currentFrameNumber)+1).zfill(4)
			filename = whiteFrameFilename[:-8]+str(currentFrameNumber)	
			
			xmlTree = xmlAddImage(cameraNumber, rotation, positionCount, positionDegree, "", filename)	

def createFolderStructure():
	# Start File Directory Structure
	if not os.path.exists(config["filepaths"]["imagepath"]+'/'+config["sample"]["id"]+"-"+config["sample"]["datestamp"]):
		os.makedirs(config["filepaths"]["imagepath"]+'/'+config["sample"]["id"]+"-"+config["sample"]["datestamp"])
	print("Downloading to "+ str(config["filepaths"]["imagepath"]+'/'+config["sample"]["id"])+"-"+config["sample"]["datestamp"])

def downloadImages(imageList):
	#Get List of Files from Camera
	context = gp.Context()
	camera = initCamera(context)	
# 	files = listFiles(camera, context)	
# 	if not files:
# 		camStatusUpdates[cameraNumber] = updateCameraDownloadStatus(cameraNumber, "No Files Found on Camera")
# 		print("No Files on "+str(cameraNumber))
# 		return	

	for image in imageList:
		(file, finalfilename) = image
		path, filename = os.path.split(file)
		blah, ext = os.path.splitext(file)			
		target = os.path.join(config["filepaths"]["imagepath"]+'/'+config["sample"]["id"]+"-"+config["sample"]["datestamp"],finalfilename)
		camera_file = camera.file_get(path, filename, gp.GP_FILE_TYPE_NORMAL, context)
		gp.gp_file_save(camera_file, target)
		if (config["filepaths"]["delete"]):
			gp.gp_camera_file_delete(camera, path, filename)
		
	return

def initCamera(context):
	# Connect to Camera
	camera = gp.Camera()
	camera.init(context)
	return camera

def updateCameraDownloadStatus(cameraNumber, status):
	update = "Camera "+cameraNumber[-1:]+": "+status
	return update

def filterFilename(filelist):
	result = []
	for path in filelist:
		folder, name = os.path.split(path)
		result.append(name)
	return result

def livewviewFocusCloser(stepSize):
	global camera
	if stepSize == "Small":
		step = "Near1"
	elif stepSize == "Medium":
		step = "Near2"
	elif stepSize == "Large":
		step = "Near3"
	else:
		step = "Near2"
	print("Focus Nearer: "+str(step))
	camConfig = camera.get_config() 
	focusmode = camConfig.get_child_by_name("manualfocusdrive") 
	focusmode.set_value(step)
	camera.set_config(camConfig)

def livewviewFocusFarther(stepSize):
	global camera
	if stepSize == "Small":
		step = "Far1"
	elif stepSize == "Medium":
		step = "Far2"
	elif stepSize == "Large":
		step = "Far3"
	else:
		step = "Far2"
		
	print("Focus Farther: "+str(step))
	camConfig = camera.get_config() 
	focusmode = camConfig.get_child_by_name("manualfocusdrive") 
	focusmode.set_value(step)
	camera.set_config(camConfig)

def moveFocusCloser(stepSize, count=1):
	if stepSize == "Small":
		step = "Near1"
	elif stepSize == "Medium":
		step = "Near2"
	elif stepSize == "Large":
		step = "Near3"
	else:
		step = "Near2"
		
	# Connect to Camera
	context = gp.Context()
	camera = gp.Camera()
	camera.init(context)
	OK, camera_file = gp.gp_camera_capture_preview(camera)
	camConfig = camera.get_config() 
	focusmode = camConfig.get_child_by_name("manualfocusdrive") 
	focusmode.set_value(step)
	camera.set_config(camConfig)
	focusRound = 0
	while focusRound < count:
		print("Moving Focus Closer")
		camera.set_config(camConfig)
		focusRound += 1
		time.sleep(.5)
	camera.exit(context)

def moveFocusFarther(stepSize, count=1):
	if stepSize == "Small":
		step = "Far1"
	elif stepSize == "Medium":
		step = "Far2"
	elif stepSize == "Large":
		step = "Far3"
	else:
		step = "Far2"
		
	# Connect to Camera
	context = gp.Context()
	camera = gp.Camera()
	camera.init(context)
	OK, camera_file = gp.gp_camera_capture_preview(camera)
	camConfig = camera.get_config() 
	focusmode = camConfig.get_child_by_name("manualfocusdrive") 
	focusmode.set_value(step)
	focusRound = 0
	while focusRound < count:
		print("Moving Focus Farther")
		camera.set_config(camConfig)
		focusRound += 1
		time.sleep(.5)
	camera.exit(context)


# Create Config File and Variables
def createConfig(path):
	# Create config file
	config = configparser.ConfigParser()
	
	config["cnc"] = {"port": "/dev/ttyUSB0", "xOverlap": "40", "yOverlap":"40", "pause":"1", "stackingSize":"Medium"}
	config["camera"] = {"body": "Canon T2i", "lens": "Tokina 100mm", "trigger":"USB", "exposure":"1", "format":"JPG"}
	config["filepaths"] = {"download":"True", "imagePath":'', "xmlPath": '', "delete":"True"}
	config["sample"] = {"cameraHeight":"", "id":"", "stackingMode":"None", "stackingCount":"1", "sizeX":"360","sizeY":"470", "datestamp":""}
	
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


# Miscellaneous Tkinter Functions
def centerWindow(window):
	time.sleep(0.25)
	window.update_idletasks()
	w = window.winfo_screenwidth()
	h = window.winfo_screenheight()
	size = tuple(int(_) for _ in window.geometry().split('+')[0].split('x'))
	x = w/2 - size[0]/2
	y = h/2 - size[1]/2
	window.geometry("%dx%d+%d+%d" % (size + (x,y)))

def closeWindow(window):
	window.destroy()

def playSound(file):
	soundThread = threading.Thread(target=playSoundThread, args=(file,))
	soundThread.start()

def playSoundThread(sound):
	pygame.mixer.init()
	pygame.mixer.music.load("backend/soundeffects/"+sound+".mp3")
	pygame.mixer.music.play()
	time.sleep(3)
	pygame.mixer.quit()

def cancelSession():
	#Doesn't actually do anything for now
	pass

def setEvent(event):
	event.set()
	return



# XML Management Functions
def writeXML(xmlTree):
	xmlTree.write(config["filepaths"]["xmlPath"]+'/'+config["sample"]["id"]+"-"+config["sample"]["datestamp"]+".xml", pretty_print=True)

def initXML():
	
	# Sample Details
	xmlSampleDetails = ET.SubElement(xmlData, "SampleDetails")
	xmlSampleID = ET.SubElement(xmlSampleDetails, "SampleID")
	xmlSampleID.text = config["sample"]["ID"]

	# Session Details
	xmlSessionDetails = ET.SubElement(xmlData, "SessionDetails")
	xmlCameraHeight = ET.SubElement(xmlSessionDetails, "CameraCount")
	xmlCameraHeight.text = str(config["sample"]["cameraHeight"])
	xmlStackingMode = ET.SubElement(xmlSessionDetails, "StackingMode")
	xmlStackingMode.text = str(config["sample"]["stackingMode"])
	xmlStackingCount = ET.SubElement(xmlSessionDetails, "StackingFrameCount")
	xmlStackingCount.text = str(config["sample"]["stackingcount"])
	xmlSampleSizeX = ET.SubElement(xmlSessionDetails, "SampleSizeX")
	xmlSampleSizeX.text = str(config["sample"]["sizeX"])
	xmlSampleSizeY = ET.SubElement(xmlSessionDetails, "SampleSizeY")
	xmlSampleSizeY.text = str(config["sample"]["sizey"])
	xmlCameraBody = ET.SubElement(xmlSessionDetails, "CameraBody")
	xmlCameraBody.text = str(config["camera"]["body"])
	xmlCameraLens = ET.SubElement(xmlSessionDetails, "CameraLens")
	xmlCameraLens.text = str(config["camera"]["lens"])
	xmlCameraOverlapX = ET.SubElement(xmlSessionDetails, "XAxisOverlap")
	xmlCameraOverlapX.text = str(config["cnc"]["xOverlap"])
	xmlCameraOverlapY = ET.SubElement(xmlSessionDetails, "YAxisOverlap")
	xmlCameraOverlapY.text = str(config["cnc"]["yOverlap"])
	xmlExposurePause = ET.SubElement(xmlSessionDetails, "ExposurePauseLength")
	xmlExposurePause.text = str(config["camera"]["exposure"])
	xmlCNCPause = ET.SubElement(xmlSessionDetails, "PauseAfterMovement")
	xmlCNCPause.text = str(config["cnc"]["pause"])
	xmlCameraTrigger = ET.SubElement(xmlSessionDetails, "CameraTriggerMode")
	xmlCameraTrigger.text = str(config["camera"]["trigger"])
	xmlDateStamp = ET.SubElement(xmlSessionDetails, "SessionTimeStamp")
	xmlDateStamp.text = str(config["sample"]["datestamp"])

	# Tasks
	xmlTasks = ET.SubElement(xmlData, "Tasks")
	xmlImageCapture = ET.SubElement(xmlTasks, "Task")
	xmlImageCapture.set("activity", "ImageCapture")

	# Images
	xmlImages = ET.SubElement(xmlData, "Images")

	writeXML(xmlTree)
	
	return xmlTree
	
def xmlLogTime(activity, state, other=""):
	xmlData = xmlTree.getroot()
	if other != "":
		other = "/"+other
	
	findString = "./Tasks/Task[@activity='"+activity+"']"+other
# 	print(findString)
	nodes = xmlData.findall(findString)
	for node in nodes:
		stateNode = ET.SubElement(node, state)
		stateNode.text = str(datetime.datetime.now().strftime('%Y%m%d %H:%M:%S'))
		stateStamp = ET.SubElement(node, state+"Stamp")
		stateStamp.text = str(datetime.datetime.now())
	writeXML(xmlTree)

def xmlTaskStatus(activity, state, other=""):
	xmlData = xmlTree.getroot()
	if other != "":
		other = "/"+other
		
	nodes = xmlData.findall("./Tasks/Task[@activity='"+activity+"']"+other+"/Status")
	if nodes:
		for node in nodes:
			node.text = str(state)
	else:
		nodes = xmlData.findall("./Tasks/Task[@activity='"+activity+"']"+other+"")
		if nodes:
			for node in nodes:
				xmlStatus = ET.SubElement(node, "Status")
				xmlStatus.text = str(state)
		else:
			nodes = xmlData.findall("./Tasks")
			if nodes:
				for node in nodes:
					xmlActivity = ET.SubElement(node, "Task")
					xmlActivity.set("activity", activity)
					xmlStatus = ET.SubElement(xmlActivity, "Status")
					xmlStatus.text = str(state)
	writeXML(xmlTree)

def xmlRestart():
	xmlData = xmlTree.getroot()
	xmlData.clear()
	return xmlTree

def xmlAddImage(position, cameraFileInfo, finalFilename, stackCount=1):
	xmlData = xmlTree.getroot()
	nodes = xmlData.findall("Images")
	for node in nodes:
		xmlImage = ET.SubElement(node, "Image")
		xmlImagePositionX = ET.SubElement(xmlImage, "PositionX")
		xmlImagePositionX.text =  str(position["x"])
		xmlImagePositionY = ET.SubElement(xmlImage, "PositionY")
		xmlImagePositionY.text =  str(position["y"])
		xmlImageFolder = ET.SubElement(xmlImage, "CameraFolder")
		xmlImageFolder.text = str(cameraFileInfo.folder)
		xmlImageFilename = ET.SubElement(xmlImage, "CameraFilename")
		xmlImageFilename.text = str(cameraFileInfo.name[:-4])
		xmlImageFinalFilename = ET.SubElement(xmlImage, "FinalFilename")
		xmlImageFinalFilename.text = str(finalFilename)
		xmlImageExtension = ET.SubElement(xmlImage, "Extension")
		xmlImageExtension.text = str(cameraFileInfo.name[-4:])
		xmlImageStackCount = ET.SubElement(xmlImage, "StackPosition")
		xmlImageStackCount.text = str(stackCount)
	writeXML(xmlTree)
	
	return xmlTree
	
def xmlImageAddDarkFrame(filename):
	xmlData = xmlTree.getroot()
	nodes = xmlData.findall("Images")
	for node in nodes:
		xmlDarkFrame = ET.SubElement(node, "Image")
		xmlDarkFrame.set("Position", "darkframe")
		xmlDFCameraFilename = ET.SubElement(xmlDarkFrame, "CameraFilename")
		xmlDFCameraFilename.text =  str(filename[:-4])
	writeXML(xmlTree)
	return xmlTree
	




# Tkinter Application Overview
class LeafCNC:
	def __init__(self):
		self.tk = Tk()
# 		self.tk.attributes('-fullscreen',True)
		self.tk.title("LeafCNC Controller")
		self.frame = Frame(self.tk)
		self.frame.pack(side="top", fill="both", expand = True)
		self.frame.grid_rowconfigure(0, weight=1)
		self.frame.grid_columnconfigure(0, weight=1)
		self.state = False
		self.tk.bind("<F11>", self.toggle_fullscreen)
		self.tk.bind("<Escape>", self.end_fullscreen)

		self.frames = {}
		FrameList = (StartPage, Settings, Initilization)
		
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
		
	def quitProgram(self, machine, event=None):
		updateConfig(config, configpath)
		closeCNC(machine)
		exit()
		return "break"

# Start Page Class
class StartPage(tkinter.Frame):
	def __init__(self, parent, controller):
		global machine
		global camera
		global imageCount
		global globalPosition

		
		tkinter.Frame.__init__(self,parent)

		# Variables
		self.cameraHeight = StringVar()
		self.cameraHeight.set(config["sample"]["cameraHeight"])
		self.sampleID = StringVar()
		self.sampleID.set(config["sample"]["id"])
		self.stackingMode = StringVar()
		self.stackingMode.set(config["sample"]["stackingMode"])
		self.stackingCount = IntVar()
		self.stackingCount.set(int(config["sample"]["stackingCount"]))
		self.sampleX = IntVar()
		self.sampleX.set(int(config["sample"]["sizeX"]))
		self.sampleY = IntVar()
		self.sampleY.set(int(config["sample"]["sizeY"]))
		self.sessionStatus = StringVar()
		self.previewPath = StringVar()
		self.previewPath.set('')
		
		# Size Columns
		self.grid_columnconfigure(1, minsize=34)
		self.grid_columnconfigure(10, minsize=50)
		self.grid_columnconfigure(12, minsize=50)
		self.grid_columnconfigure(14, minsize=50)
		self.grid_columnconfigure(16, minsize=50)
		self.grid_columnconfigure(18, minsize=50)
		self.grid_columnconfigure(20, minsize=50)
		self.grid_columnconfigure(11, minsize=20)
		self.grid_columnconfigure(13, minsize=20)
		self.grid_columnconfigure(15, minsize=20)
		self.grid_columnconfigure(17, minsize=20)
		self.grid_columnconfigure(19, minsize=20)
		self.grid_columnconfigure(99, minsize=34)

		# Size Rows
		self.grid_rowconfigure(2, minsize=100)
		self.grid_rowconfigure(10, minsize=50)
		self.grid_rowconfigure(20, minsize=50)
		self.grid_rowconfigure(99, minsize=20)
		self.grid_rowconfigure(31, minsize=700)

		# Page Title
		pageTitle = ttk.Label(self, text="Leaf CNC Controller", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, column=1, sticky="WE")
		
		
		# Buttons
		btnInit = ttk.Button(self, text="Table Initilization", command=lambda: controller.show_frame(Initilization))
		btnInit.grid(row=10, column=12, sticky="NEWS")
		btnRunSample = ttk.Button(self, text="Run Sample", command=lambda: startSessionThreading(self.sessionStatus))
		btnRunSample.grid(row=10, column=10, sticky="NEWS")
		btnSettings = ttk.Button(self, text="Settings", command=lambda: controller.show_frame(Settings))
		btnSettings.grid(row=10, column=14, sticky="NEWS")
		btnTest = ttk.Button(self, text="Test Function", command=lambda: self.test())
#		btnTest.grid(row=20, column=10, sticky="NEWS")
		btnTest2 = ttk.Button(self, text="Test Function 2", command=lambda: self.test2())
#		btnTest2.grid(row=20, column=11, sticky="NEWS")
		self.btnLiveView = ttk.Label(self, text="")
		self.btnLiveView.grid(row=30, column=10, sticky="NEWS", columnspan=10)
		self.imgLiveView = ImageTk.PhotoImage(Image.open(os.path.dirname(os.path.abspath(__file__))+"/backend/LiveviewTemplate.jpg"))
		self.btnLiveView.image = self.imgLiveView
		self.btnLiveView.config(text="", image=self.imgLiveView)
		btnStartLiveView = ttk.Button(self, text="Start Liveview", command=lambda: startLiveViewThreading(self.btnLiveView))
		btnStartLiveView.grid(row=10, column=16, sticky="NEWS")
		btnStopLivewView = ttk.Button(self, text="Stop Liveview", command=lambda: liveViewEvents["stopLiveView"].set())
		btnStopLivewView.grid(row=10, column=18, sticky="NEWS")
		
		btnQuit = ttk.Button(self, text="Quit", command=lambda: controller.quitProgram(machine))
		btnQuit.grid(row=10, column=20, sticky="NEWS")

		def startSessionThreading(sessionStatus):
			events = {}
			events["complete"] = threading.Event()
			events["cancel"] = threading.Event()
			events["pause"] = threading.Event()
			events["cncInit"] = threading.Event()
			events["sampleInfoInit"] = threading.Event()
			events["filePathProblem"] = threading.Event()
			events["xmlPathProblem"] = threading.Event()
			events["xmlWarning"] = threading.Event()
			events["manualFocusStacking"] = threading.Event()
			sessionThread = threading.Thread(target=self.startSession, args=( events, sessionStatus))
			interfaceThread = threading.Thread(target=sessionWindow, args=( events, sessionStatus))
			interfaceThread.start()
			sessionThread.start()
			
		
		def sessionWindow(events, sessionStatus):
			global liveViewEvents
			sessionWindow = Toplevel(self)
			sessionWindow.title("Leaf Sampling Session")
			sessionWindow.geometry("550x350")
			centerWindow(sessionWindow)
			sessionWindow.focus_force()

			sessionWindow.grid_rowconfigure(2, minsize=60)
			sessionWindow.grid_rowconfigure(3, minsize=30)
			sessionWindow.grid_rowconfigure(4, minsize=30)
			sessionWindow.grid_rowconfigure(5, minsize=30)
			sessionWindow.grid_rowconfigure(6, minsize=30)
			sessionWindow.grid_rowconfigure(7, minsize=30)
			sessionWindow.grid_columnconfigure(3, minsize=350)


			lblTitle = ttk.Label(sessionWindow, text="Leaf Sampling Status", font=LARGE_FONT, justify="center")
			lblTitle.grid(row=1, sticky="WE", columnspan=100)
		
			lblStatusTitle = ttk.Label(sessionWindow, text="Status:", font=MED_FONT, justify="left")
			lblStatusTitle.grid(row=2, column=2, sticky="W")
		
			lblStatus = ttk.Label(sessionWindow, textvariable=self.sessionStatus, font=MED_FONT, justify="left")
			lblStatus.grid(row=2, column=3, sticky="W")

			btnCancel = ttk.Button(sessionWindow, text="Cancel", command=lambda: [setEvent(events["cancel"])])
			btnCancel.grid(row=8, column=3, columnspan=2, sticky="WE")
		
			while not events["complete"].is_set():
				if events["cancel"].is_set():
					sessionStatus.set("Cancelling...")

				if events["cncInit"].is_set():
					events["pause"].set()
					cncInitPrompt = Toplevel(self)
					cncInitPrompt.title("Inititilize Machine")
					cncInitLine0 = ttk.Label(cncInitPrompt, text="Please Confirm Camera is at Origin Point (0,0) and Correct Height", font=LARGE_FONT).pack()
					cncInitLine1 = ttk.Label(cncInitPrompt, text="Press Continue to proceed with Sampling.", font=MED_FONT).pack()
					cncInitLine2 = ttk.Label(cncInitPrompt, text="Press Cancel to go to Initilization Setup.", font=MED_FONT).pack()
					cncInitContinue = ttk.Button(cncInitPrompt, text="Continue", command=lambda: [closeWindow(cncInitPrompt), events["pause"].clear()]).pack()
					cncInitCancel = ttk.Button(cncInitPrompt, text="Cancel", command=lambda: [closeWindow(cncInitPrompt), events["cancel"].set(), events['cncInit'].clear()]).pack()
					centerWindow(cncInitPrompt)
					events["cncInit"].clear()
				
				if events["sampleInfoInit"].is_set():
					events["pause"].set()
# 					playSound("error")
					sampleInfoInitWindow = Toplevel(self)
					sampleInfoInitWindow.title("Sample Details")
					sampleInfoInitTitle = ttk.Label(sampleInfoInitWindow, text="Enter Sample Information", font=MED_FONT).pack()
					lblSampleID = ttk.Label(sampleInfoInitWindow, text="Sample ID:", font=MED_FONT).pack()
					entrySampleID = ttk.Entry(sampleInfoInitWindow, textvariable=self.sampleID, width=10).pack()
					lblCameraHeight = ttk.Label(sampleInfoInitWindow, text="Camera Height:", font=MED_FONT).pack()
					entryCameraHeight = ttk.Entry(sampleInfoInitWindow, textvariable=self.cameraHeight, width=10).pack()
					lblStackingMode = ttk.Label(sampleInfoInitWindow, text="Focus Stacking Mode:", font=MED_FONT).pack()
					cmbStackingMode = ttk.Combobox(sampleInfoInitWindow, textvariable=self.stackingMode, width=10)
					cmbStackingMode['values'] = ["None","Auto","Manual"]
					cmbStackingMode.pack()
					lblStackingCount = ttk.Label(sampleInfoInitWindow, text="Stacking Count:", font=MED_FONT).pack()
					entryStackingCount = ttk.Entry(sampleInfoInitWindow, textvariable=self.stackingCount, width=10).pack()
					lblSampleSizeX = ttk.Label(sampleInfoInitWindow, text="Sample Height:", font=MED_FONT).pack()
					entrySampleSizeX = ttk.Entry(sampleInfoInitWindow, textvariable=self.sampleX, width=10).pack()
					lblSampleSizeY = ttk.Label(sampleInfoInitWindow, text="Sample Width:", font=MED_FONT).pack()
					entrySampleSizeY = ttk.Entry(sampleInfoInitWindow, textvariable=self.sampleY, width=10).pack()
					sampleInfoInitContinue = ttk.Button(sampleInfoInitWindow, text="Continue", command=lambda: [self.updateSampleInfo(), closeWindow(sampleInfoInitWindow), events["pause"].clear()]).pack()
					sampleInfoInitCancel = ttk.Button(sampleInfoInitWindow, text="Cancel", command=lambda: [closeWindow(sampleInfoInitWindow), events["cancel"].set(), events["pause"].clear()]).pack()
					centerWindow(sampleInfoInitWindow)
					events["sampleInfoInit"].clear()
				
				if events["filePathProblem"].is_set():
					events["pause"].set()
					playSound("error")
					filePathPrompt = Toplevel(self)
					filePathPrompt.title("File Path Problem")
					filePathTitle = ttk.Label(filePathPrompt, text="File Path Problem", font=MED_FONT).pack()
					filePathPromptLine2 = ttk.Label(filePathPrompt, text="Unable to access the folder designated for image downloads.", font=MED_FONT).pack()
					filePathPromptLine3 = ttk.Label(filePathPrompt, text="Please hit Cancel and ensure this folder is correct and mounted.", font=MED_FONT).pack()
					filePathCancel = ttk.Button(filePathPrompt, text="Cancel", command=lambda: [closeWindow(filePathPrompt), events["cancel"].set(), events["pause"].clear()]).pack()
					centerWindow(filePathPrompt)
					events["filePathProblem"].clear()
				
				if events["xmlPathProblem"].is_set():
					events["pause"].set()
					playSound("error")
					xmlPathPrompt = Toplevel(self)
					xmlPathPrompt.title("XML Path Problem")
					xmlPathTitle = ttk.Label(xmlPathPrompt, text="XML Path Problem", font=MED_FONT).pack()
					xmlPathPromptLine2 = ttk.Label(xmlPathPrompt, text="Unable to access the folder designated for XML files.", font=MED_FONT).pack()
					xmlPathPromptLine3 = ttk.Label(xmlPathPrompt, text="Please hit Cancel and ensure this folder is correct and mounted.", font=MED_FONT).pack()
					xmlPathCancel = ttk.Button(xmlPathPrompt, text="Cancel", command=lambda: [closeWindow(xmlPathPrompt), events["cancel"].set(), events["pause"].clear()]).pack()
					centerWindow(xmlPathPrompt)
					events["xmlPathProblem"].clear()
				
				if events["xmlWarning"].is_set():
					events["pause"].set()
					playSound("error")
					xmlWarningPrompt = Toplevel(self)
					xmlWarningPrompt.title("XML Warning")
					xmlWarningTitle = ttk.Label(xmlWarningPrompt, text="XML File Exists", font=MED_FONT).pack()
					xmlWarningPromptLine2 = ttk.Label(xmlWarningPrompt, text="It appears that an XML already exists for a sample with this Sample ID.", font=MED_FONT).pack()
					xmlWarningPromptLine3 = ttk.Label(xmlWarningPrompt, text="Select Continue to continue and add to the existing XML File.", font=MED_FONT).pack()
					xmlWarningPrompteLine4 = ttk.Label(xmlWarningPrompt, text="Select Cancel to cancel and start over.", font=SMALL_FONT).pack()
					xmlWarningContinue = ttk.Button(xmlWarningPrompt, text="Continue", command=lambda: [closeWindow(xmlWarningPrompt), events["pause"].clear()]).pack()
					xmlWarningCancel = ttk.Button(xmlWarningPrompt, text="Cancel", command=lambda: [closeWindow(xmlWarningPrompt), events["cancel"].set(), events["pause"].clear()]).pack()
					centerWindow(xmlWarningPrompt)
					events["xmlWarning"].clear()
				
				if events["manualFocusStacking"].is_set():
					self.manualFocusStackingWindow = Toplevel(self)
					self.manualFocusStackingWindow.title("Manual Focus Stacking")
					self.manualFocusStackingWindow.grid_rowconfigure(1, minsize=30) 	#Title
					self.manualFocusStackingWindow.grid_rowconfigure(2, minsize=30)	#Text
					self.manualFocusStackingWindow.grid_rowconfigure(3, minsize=30)	#text
					self.manualFocusStackingWindow.grid_rowconfigure(4, minsize=30)	#text
					self.manualFocusStackingWindow.grid_rowconfigure(5, minsize=30)	#buttons
					self.manualFocusStackingWindow.grid_rowconfigure(6, minsize=30)	#liveview/text
					self.manualFocusStackingWindow.grid_rowconfigure(7, minsize=30)	#buttons
					self.manualFocusStackingWindow.grid_rowconfigure(8, minsize=30)	#buttons
					self.manualFocusStackingWindow.grid_rowconfigure(9, minsize=30)	#buttons
					self.manualFocusStackingWindow.grid_rowconfigure(10, minsize=30)	#buttons
					self.manualFocusStackingWindow.grid_rowconfigure(11, minsize=30)
					self.manualFocusStackingWindow.grid_columnconfigure(1, minsize=50)
					self.manualFocusStackingWindow.grid_columnconfigure(2, minsize=200)
					self.manualFocusStackingWindow.grid_columnconfigure(3, minsize=512)
					self.manualFocusStackingWindow.grid_columnconfigure(4, minsize=512)
					self.manualFocusStackingWindow.grid_columnconfigure(5, minsize=200)
					self.manualFocusStackingWindow.grid_columnconfigure(6, minsize=50)
					
					
					manFocusStackingTitle = ttk.Label(self.manualFocusStackingWindow, text="Manual Focus Stacking", font=LARGE_FONT)
					manFocusStackingTitle.grid(row=1, column=3, sticky="NEWS")
					manFocusStackingLine1 = ttk.Label(self.manualFocusStackingWindow, text="To Perform Manual Focus Stacking, use the buttons to adjust the focus,", font=MED_FONT)
					manFocusStackingLine1.grid(row=2, column=3, sticky="NEWS")
					manFocusStackingLine2 = ttk.Label(self.manualFocusStackingWindow, text="press Capture to take a picture, and press Next Position to move the ", font=MED_FONT)
					manFocusStackingLine2.grid(row=3, column=3, sticky="NEWS")
					manFocusStackingLine3 = ttk.Label(self.manualFocusStackingWindow, text="camera to the next position.", font=MED_FONT)
					manFocusStackingLine3.grid(row=4, column=3, sticky="NEWS")
# 					btnStartLiveView = ttk.Button(manualFocusStackingWindow, text="Start Liveview", command=lambda: startLiveViewThreading(self.btnLiveViewFocusStacking))
# 					btnStartLiveView.grid(row=5, column=3, sticky="NWS")
# 					btnStopLivewView = ttk.Button(manualFocusStackingWindow, text="Stop Liveview", command=lambda: self.stopLiveView())
# 					btnStopLivewView.grid(row=5, column=3, sticky="NES")
					
					self.btnLiveViewFocusStacking = ttk.Label(self.manualFocusStackingWindow, text="", width=150)
					self.btnLiveViewFocusStacking.grid(row=6, column=3, sticky="NEWS", rowspan=4, columnspan=2)
					imgLiveView = ImageTk.PhotoImage(Image.open(os.path.dirname(os.path.abspath(__file__))+"/backend/LiveviewTemplate.jpg"))
					self.btnLiveViewFocusStacking.image = imgLiveView
					self.btnLiveViewFocusStacking.config(text="", image=imgLiveView)
					lblFocusCloser = ttk.Label(self.manualFocusStackingWindow, text="Move Focus Up", font=LARGE_FONT)
					lblFocusCloser.grid(row=6, column=2, sticky="NEWS")
					btnFocusCloserSmall = ttk.Button(self.manualFocusStackingWindow, text="Small", width=5, command=lambda: [liveViewEvents["focusCloserSmall"].set()])
					btnFocusCloserSmall.grid(row=7, column=2, sticky="NEWS")
					btnFocusCloserMedium = ttk.Button(self.manualFocusStackingWindow, text="Medium", width=10, command=lambda: [liveViewEvents["focusCloserMedium"].set()])
					btnFocusCloserMedium.grid(row=8, column=2, sticky="NEWS")
					btnFocusCloserLarge = ttk.Button(self.manualFocusStackingWindow, text="Large", width=15, command=lambda: [liveViewEvents["focusCloserLarge"].set()])
					btnFocusCloserLarge.grid(row=9, column=2, sticky="NEWS")
					lblFocusFarther = ttk.Label(self.manualFocusStackingWindow, text="Move Focus Down", font=LARGE_FONT)
					lblFocusFarther.grid(row=6, column=5, sticky="NEWS")
					btnFocusFartherSmall = ttk.Button(self.manualFocusStackingWindow, text="Small", width=5, command=lambda: [liveViewEvents["focusFartherSmall"].set()])
					btnFocusFartherSmall.grid(row=7, column=5, sticky="NEWS")
					btnFocusFartherMedium = ttk.Button(self.manualFocusStackingWindow, text="Medium", width=10, command=lambda: [liveViewEvents["focusFartherMedium"].set()])
					btnFocusFartherMedium.grid(row=8, column=5, sticky="NEWS")
					btnFocusFartherLarge = ttk.Button(self.manualFocusStackingWindow, text="Large", width=15, command=lambda: [liveViewEvents["focusFartherLarge"].set()])
					btnFocusFartherLarge.grid(row=9, column=5, sticky="NEWS")
					btnFocusStackingCapture = ttk.Button(self.manualFocusStackingWindow, text="Capture", command=lambda: [liveViewEvents["capturingImage"].set()])
					btnFocusStackingCapture.grid(row=10, column=3, sticky="NEWS")
					btnFocusStackingNextPosition = ttk.Button(self.manualFocusStackingWindow, text="Next Position", command=lambda: [events["pause"].clear()])
					btnFocusStackingNextPosition.grid(row=10, column=4, sticky="NEWS")
					
					centerWindow(self.manualFocusStackingWindow)
					startLiveViewThreading(self.btnLiveViewFocusStacking)
					
					events["manualFocusStacking"].clear()
				
			
			closeWindow(sessionWindow)
			self.sessionStatus.set("")
			events["complete"].clear()
			playSound("complete")
	
		def startLiveViewThreading(target):
			global liveViewEvents
			liveViewEvents["focusCloserLarge"] = threading.Event()
			liveViewEvents["focusCloserMedium"] = threading.Event()
			liveViewEvents["focusCloserSmall"] = threading.Event()
			liveViewEvents["focusFartherLarge"] = threading.Event()
			liveViewEvents["focusFartherMedium"] = threading.Event()
			liveViewEvents["focusFartherSmall"] = threading.Event()
			liveViewEvents["capturingImage"] = threading.Event()
			liveViewEvents["stopLiveView"] = threading.Event()
			liveViewThread = threading.Thread(target=self.startLiveView, args=( target,))
			liveViewThread.start()
	
	
	def test(self):
		global liveViewEvents
		liveViewEvents["focusCloserLarge"].set()
		
		pass
		
	def test2(self):
		pass
	
		
	def updateSampleInfo(self, event=None):
		config['sample']['id'] = str(self.sampleID.get())
		config['sample']['cameraHeight'] = str(self.cameraHeight.get())
		config['sample']['stackingMode'] = str(self.stackingMode.get())
		config['sample']['stackingCount'] = str(self.stackingCount.get())
		config['sample']['sizeX'] = str(self.sampleX.get())
		config['sample']['sizeY'] = str(self.sampleY.get())
		updateConfig(config, configpath)

	def startLiveView(self, target):
		# Live View Testing - Start
		global liveViewActive
		global camera
		global context
		global imageCount
		global globalPosition
		global liveViewEvents
		global imageList
		global stackCount
		liveViewActive = True
		
		stackCount = 1

		# Connect to Camera
		context = gp.Context()
		camera = gp.Camera()
		camera.init(context)
		
		while not liveViewEvents["stopLiveView"].is_set():
			if liveViewEvents["capturingImage"].is_set():
				target.image = ImageTk.PhotoImage(Image.open(os.path.dirname(os.path.abspath(__file__))+"/backend/CapturingImage.jpg"))
				img = target.image
				target.config(text="", image=img)
				camera.exit(context)
				cameraInfo = triggerImageUSB()
				finalFilename = str(config["sample"]["id"])+"-"+str(config["sample"]["datestamp"])+"-"+str(imageCount).zfill(3)+str(cameraInfo.name[-4:])
				imageList.append((cameraInfo.folder+"/"+cameraInfo.name, finalFilename))
				time.sleep(int(config["camera"]["exposure"]))
				imageCount += 1	
				xmlTree = xmlAddImage(globalPosition, cameraInfo, finalFilename, stackCount)
				stackCount += 1
				liveViewEvents["capturingImage"].clear()
			elif liveViewEvents["stopLiveView"].is_set():
				break
			else:
				if liveViewEvents["focusCloserLarge"].is_set():
					livewviewFocusCloser("Large")	
					liveViewEvents["focusCloserLarge"].clear()
				if liveViewEvents["focusCloserMedium"].is_set():
					livewviewFocusCloser("Medium")	
					liveViewEvents["focusCloserMedium"].clear()
				if liveViewEvents["focusCloserSmall"].is_set():
					livewviewFocusCloser("Small")	
					liveViewEvents["focusCloserSmall"].clear()
				if liveViewEvents["focusFartherLarge"].is_set():
					livewviewFocusFarther("Large")	
					liveViewEvents["focusFartherLarge"].clear()
				if liveViewEvents["focusFartherMedium"].is_set():
					livewviewFocusFarther("Medium")	
					liveViewEvents["focusFartherMedium"].clear()
				if liveViewEvents["focusFartherSmall"].is_set():
					livewviewFocusFarther("Small")	
					liveViewEvents["focusFartherSmall"].clear()
				target = self.capturePreview(camera, target)
				time.sleep(.05)
		liveViewEvents["stopLiveView"].clear()
		camera.exit(context)
		target.image = ImageTk.PhotoImage(Image.open(os.path.dirname(os.path.abspath(__file__))+"/backend/LiveviewTemplate.jpg"))
		imgLiveView = target.image
		target.config(text="", image=imgLiveView)

	def stopLiveView(self, livewViewEvents):
		# Live View Testing - Stop
		liveViewEvents["stopLiveView"].set()

	def startSession(self, events, sessionStatus):
		global rolledOver
		global machine
		global XMAX
		global YMAX
		global xPos
		global yPos
		global rateOfTravel
		global imageCount
		global positionCount
		global position
		global imageList
		
		# Check to see if everything is ready
# 		status["camerasInit"] = False
# 		status["cameraSettings"] = False
# 		status["tableInit"] = False
		status["filepathInit"] = False
		status["xmlpathInit"] = False
		status["xmlCheck"] = False


		# Check to see that camera is connected
# 		if status["cameras"] > 0:
# 			status["camerasInit"] = True
# 		else: 
# 			events["noCamerasPrompt"].set()
# 			events["pause"].set()
# 			while events["pause"].is_set():
# 				if events["cancel"].is_set():
# 					cancelSession()
# 					break
# 				pass
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return


		# Check to see if File Download Path is available
		if config["filepaths"]["download"] == "False":
			status["filepathInit"] = True
		else:
			if config["filepaths"]["imagePath"] == '':
				status["filepathInit"] = False
				events["filePathProblem"].set()
				events["pause"].set()
				while events["pause"].is_set():
					if events["cancel"].is_set():
						cancelSession()
						break
				status["filepathInit"] = True
			elif os.path.isdir(config["filepaths"]["imagePath"]):
				status["filepathInit"] = True
			else:
				events["filePathProblem"].set()
				events["pause"].set()
				while events["pause"].is_set():
					if events["cancel"].is_set():
						cancelSession()
						break
				status["filepathInit"] = True
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return
								
		# Check to see if XML Path is available
		if config["filepaths"]["xmlPath"] == '':
			status["xmlpathInit"] = False
			events["xmlPathProblem"].set()
			events["pause"].set()
			while events["pause"].is_set():
				if events["cancel"].is_set():
					cancelSession()
					break
			status["xmlpathInit"] = True
		elif os.path.isdir(config["filepaths"]["xmlPath"]):
			status["xmlpathInit"] = True
		else:
			events["xmlPathProblem"].set()
			events["pause"].set()
			while events["pause"].is_set():
				if events["cancel"].is_set():
					cancelSession()
					break
			status["xmlpathInit"] = True
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return
								
		# Check to see camera settings are not White Frame Settings (1" at 6400 ISO)
# 		status["cameraSettings"] = False
# 		while not status["cameraSettings"]:
# 			# Connect to Camera
# 			context = gp.Context()
# 			camera = initCamera(cameraNumber, context)		
# 	
# 			# Get Image Size/Type Settings from Camera
# 			camConfig = camera.get_config(context) 
# 			camera.exit(context)
# 			camSettings = {}
# 			iso = camConfig.get_child_by_name("iso") 
# 			camSettings["iso"] = iso.get_value()
# 			shutterspeed = camConfig.get_child_by_name("shutterspeed") 
# 			camSettings["shutterspeed"] = shutterspeed.get_value()
# 			exposurecompensation = camConfig.get_child_by_name("exposurecompensation")			
# 			camSettings["exposurecompensation"] = exposurecompensation.get_value()
# 			imagequality = camConfig.get_child_by_name("imagequality") 
# 			camSettings["imagequality"] = imagequality.get_value() 		#"0"
# 		
# 			if str(camSettings["iso"]) == "6400" or str(camSettings["exposurecompensation"]) == "5" or str(camSettings["imagequality"]) != "NEF+Fine":
# 				camerasToFix.append(cameraNumber)
# 		
# 			if len(camerasToFix) > 0:
# 				events["fixCameraSettings"].set()
# 				events["pause"].set()
# 				while events["pause"].is_set():
# 					if events["cancel"].is_set():
# 						cancelSession()
# 						break
# 			else:	
# 				status["cameraSettings"] = True
# 
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return

		# Prompt User to Verify Table is Ready
		events["cncInit"].set()
		events["pause"].set()
		while events["pause"].is_set():
			if events["cancel"].is_set():
				cancelSession()
				break
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return
		
		# Prompt User for Sample ID Info
		events["sampleInfoInit"].set()
		events["pause"].set()
		while events["pause"].is_set():
			if events["cancel"].is_set():
				cancelSession()
				break
		

		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return

		# Check to see if XML file already exists.
		status["xmlCheck"] = False
		while not status["xmlCheck"]:
			if os.path.isfile(config["filepaths"]["xmlPath"]+"/"+config["sample"]["id"]+".xml"):
				events["xmlWarning"].set()
				while events["pause"].is_set():
					if events["cancel"].is_set():
						cancelSession()
						break

					status["xmlCheck"] = True
			else:
				status["xmlCheck"] = True
		
		if events["cancel"].is_set():
			events["complete"].set()
			cancelSession()	
			return
		
		# Start Process
		sessionStatus.set("Initilizing XML Session")

		startTimeStamp = str(datetime.datetime.now().strftime('%Y%m%d_%H%M'))
		config["sample"]["datestamp"] = startTimeStamp
		updateConfig(config, configpath)
		
		# Initiate XML Data
		xmlTree = initXML()
		xmlTree = xmlLogTime("ImageCapture", "Start")
		xmlTree = xmlTaskStatus("ImageCapture", "Processing")

		if events["cancel"].is_set():
			cancelSession()
			return

		# Trigger Dark Frame
		sessionStatus.set("Capturing Initial Dark Frame")
		darkFrameFilename = triggerDarkFrame()
		
		xmlTree = xmlImageAddDarkFrame(darkFrameFilename)
		
		

		# Start Photos and Rotation
		xPos = 0
		yPos = 0
		imageCount = 1
		positionCount = 1
		imageList = []
		
		
		
		# Calculate Frames Per X
		framesPerX = 2
		# Calculate Frames Per Y	
		framesPerY = 2
		# Generate List of Positions
		positions = []
		
		calcX = 0
		calcY = 0
		while calcX < XMAX:
			while calcY < YMAX:
				pos = {}
				pos["x"] = calcX
				pos["y"] = calcY
				print("Pos: "+str(pos))
				positions.append(pos)
				calcY = calcY + (YMAX/framesPerY)
			calcX = calcX + (XMAX/framesPerX)
			calcY = 0
		print("Positions: "+str(positions))
		for position in positions:
		
			sessionStatus.set("Capturing Image at Position #"+str(positionCount)+" of "+str(len(positions)))
			distanceToTravel = math.sqrt((xPos-int(position["x"]))**2 + (yPos - int(position["y"]))**2)
			
			timetoTravel = distanceToTravel/rateOfTravel
			responseString = moveCNCtoCoordinates(position["x"], position["y"], machine)	
			time.sleep(timetoTravel)
			time.sleep(int(config["cnc"]["pause"]))
			# Trigger Camera
			if config["sample"]["stackingMode"] == "None":
				cameraInfo = triggerImageUSB()
				finalFilename = str(config["sample"]["id"])+"-"+str(config["sample"]["datestamp"])+"-"+str(imageCount).zfill(3)+str(cameraInfo.name[-4:])
				imageList.append((cameraInfo.folder+"/"+cameraInfo.name, finalFilename))
				time.sleep(int(config["camera"]["exposure"]))
				imageCount +=1	
				positionCount +=1		
				xmlTree = xmlAddImage(position, cameraInfo, finalFilename)
				if events["cancel"].is_set():
					cancelSession()
					break
			elif config["sample"]["stackingMode"] == "Auto":
				stackCount = 1
				while stackCount <= int(config["sample"]["stackingCount"]):
					sessionStatus.set("Capturing Image #"+str(stackCount)+"/"+str(config["sample"]["stackingCount"])+" at Position #"+str(positionCount)+" of "+str(len(positions)))
					cameraInfo = triggerImageUSB()
					print("Captured: "+cameraInfo.name)
					finalFilename = str(config["sample"]["id"])+"-"+str(config["sample"]["datestamp"])+"-"+str(imageCount).zfill(3)+str(cameraInfo.name[-4:])
					imageList.append((cameraInfo.folder+"/"+cameraInfo.name, finalFilename))
					time.sleep(int(config["camera"]["exposure"]))
					imageCount +=1	
					xmlTree = xmlAddImage(position, cameraInfo, finalFilename, stackCount)
					stackCount += 1
					if events["cancel"].is_set():
						cancelSession()
						break
					
					# move focus closer one step
					moveFocusCloser(config["cnc"]["stackingSize"])
				sessionStatus.set("Resetting Focus Position")
				while stackCount > 1:
					moveFocusFarther(config["cnc"]["stackingSize"])
					stackCount -= 1
				positionCount +=1		

			elif config["sample"]["stackingMode"] == "Manual":
				# Launch Live View/Manual Window
				global globalPosition
				globalPosition = position
				events["pause"].set()
				events["manualFocusStacking"].set()
				while events["pause"].is_set():
					if events["cancel"].is_set():
						cancelSession()
						break
				liveViewEvents["stopLiveView"].set()
				centerWindow(self.manualFocusStackingWindow)
				positionCount +=1		
				if events["cancel"].is_set():
					cancelSession()
					return
		
		if events["cancel"].is_set():
			events["complete"].set()	
			cancelSession()
			return
			
		# Return Camera to Origin
		sessionStatus.set("Returning Camera to Origin")
		print(str(sessionStatus.get()))
		
		responseString = moveCNCtoCoordinates(0, 0, machine)
		
		if events["cancel"].is_set():
			cancelSession()
			events["complete"].set()	
			return
			
		# Display Photography Completion Prompt
		xmlTree = xmlTaskStatus("ImageCapture", "Complete")
		xmlTree = xmlLogTime("ImageCapture", "Complete")
		sessionStatus.set("Photography Complete!")
		print(str(sessionStatus.get()))
	
		# Download Images
		if config["filepaths"].getboolean("download"):
			# Download Instructions
			sessionStatus.set("Downloading Images...  This may take a while...")
			print(str(sessionStatus.get()))
			
			xmlTree = xmlTaskStatus("DownloadingImages", "Processing")
			xmlTree = xmlLogTime("DownloadingImages", "Start")

			createFolderStructure()
			downloadImages(imageList)

			xmlTree = xmlTaskStatus("DownloadingImages", "Complete")
			xmlTree = xmlLogTime("DownloadingImages", "Complete")
				
				
		if events["cancel"].is_set():
			cancelSession()
			events["complete"].set()	
			return

		# Reset Status Variables and Updates
# 		status["camerasInit"] = False
# 		status["cameraSettings"] = False
# 		status["tableInit"] = False
		status["filepathInit"] = False
		status["xmlpathInit"] = False
		status["xmlCheck"] = False
		sessionData.clear()
		xmlTree = xmlRestart()
		
		events["complete"].set()	
		
			
		return
			
	def capturePreview(self, camera, target, focus=None):
		OK, camera_file = gp.gp_camera_capture_preview(camera)
		imageData = camera_file.get_data_and_size()			
		imgLiveView = ImageTk.PhotoImage(Image.open(io.BytesIO(imageData)))
		target.image = imgLiveView
		target.config(text="", image=imgLiveView)
		return target



# Settings Page
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
		self.imageFormat = StringVar()
		self.imageFormat.set(config['camera']['format'])
		self.exposureLength = StringVar()
		self.exposureLength.set(str(config['camera']['exposure']))
		self.xOverlap = IntVar()
		self.xOverlap.set(config['cnc']['xOverlap'])
		self.yOverlap = IntVar()
		self.yOverlap.set(config['cnc']['yOverlap'])
		self.pauseLength = StringVar()
		self.pauseLength.set(config['cnc']['pause'])
		self.download = BooleanVar()
		self.download.set(config['filepaths'].getboolean("download"))
		self.imagePath = StringVar()
		self.imagePath.set(config['filepaths']['imagePath'])
		self.xmlPath = StringVar()
		self.xmlPath.set(config['filepaths']['xmlPath'])
		self.deleteImages = BooleanVar()
		self.deleteImages.set(config['filepaths'].getboolean('delete'))
		self.stackingSize = StringVar()
		self.stackingSize.set(str(config['cnc']['stackingSize']))
		
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
		self.grid_rowconfigure(10, minsize=20)
		self.grid_rowconfigure(11, minsize=10)
		self.grid_rowconfigure(10, minsize=20)
		self.grid_rowconfigure(12, minsize=10)
		self.grid_rowconfigure(13, minsize=20)
		self.grid_rowconfigure(14, minsize=10)
		self.grid_rowconfigure(15, minsize=20)
		self.grid_rowconfigure(16, minsize=10)
		self.grid_rowconfigure(17, minsize=20)
		self.grid_rowconfigure(18, minsize=10)
		self.grid_rowconfigure(19, minsize=20)

		self.grid_rowconfigure(20, minsize=10)
		self.grid_rowconfigure(21, minsize=20)
		self.grid_rowconfigure(22, minsize=10)
		self.grid_rowconfigure(23, minsize=20)
		self.grid_rowconfigure(24, minsize=10)
		self.grid_rowconfigure(25, minsize=20)
		self.grid_rowconfigure(26, minsize=10)
		self.grid_rowconfigure(27, minsize=20)
		
		# Page Title
		pageTitle = ttk.Label(self, text="LeafCNC Settings", font=LARGE_FONT)
		pageTitle.grid(row=0, columnspan=100, sticky="WE")


		# Camera Settings
		lblCameraBody = ttk.Label(self, text="Camera Body", font=MED_FONT)
		cmbCameraBody = ttk.Combobox(self, textvariable=self.cameraBody, width=10)
		cmbCameraBody['values'] = ["Canon T2i"]
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
		lblImageFormat = ttk.Label(self, text="Image Format", font=MED_FONT)
		cmbImageFormat = ttk.Combobox(self, textvariable=self.imageFormat, width=10)
		cmbImageFormat['values'] = ["JPG","RAW"]
		lblImageFormat.grid(row=18, column=10, sticky="WE")
		cmbImageFormat.grid(row=18, column=11, sticky="WE")
		
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
		lblStackingSize = ttk.Label(self, text="Focus Stacking Size", font=MED_FONT)
		cmbStackingSize = ttk.Combobox(self, textvariable=self.stackingSize, width=10)
		cmbStackingSize['values'] = ["Small", "Medium", "Large"]
		lblStackingSize.grid(row=16, column=20, sticky="WE")
		cmbStackingSize.grid(row=16, column=21, sticky="WE")

		# File Paths
		folderIcon = ImageTk.PhotoImage(Image.open("/home/pi/leafcnc/backend/folderIcon-small.png"))
# 		lblDownloadFiles = ttk.Label(self, text="Download Files from Camera", font=MED_FONT)
# 		lblDownloadFiles.grid(row=20, column=10, sticky="EW")
		chkDownloadFiles = ttk.Checkbutton(self, var=self.download, text="Download Files from Camera", onvalue=True, offvalue=False, command=lambda: [self.updateVariable()] )
		chkDownloadFiles.grid(row=20, column=11, sticky="EW")
		chkDeleteFiles = ttk.Checkbutton(self, var=self.download, text="Delete Files from Camera after Download", onvalue=True, offvalue=False, command=lambda: [self.updateVariable()] )
		chkDeleteFiles.grid(row=22, column=11, sticky="EW")
		lblImagePath = ttk.Label(self, text="Image Storage Path", font=MED_FONT)
		lblImagePath.grid(row=24, column=10, sticky="EW")
		fileImagePath = ttk.Entry(self, textvariable=self.imagePath, width=30)
		fileImagePath.grid(row=24, column=11, sticky="EW")
		btnImagePath = ttk.Button(self, image=folderIcon, command=lambda: selectDirectory(self.imagePath))
		btnImagePath.image = folderIcon
		btnImagePath.grid(row=24, column=12, sticky="W")
		lblxmlPath = ttk.Label(self, text="XML Storage Path", font=SMALL_FONT)
		lblxmlPath.grid(row=26, column=10, columnspan=2, sticky="EW")
		filexmlPath = ttk.Entry(self, textvariable=self.xmlPath, width=30)
		filexmlPath.grid(row=26, column=11, sticky="EW")
		btnxmlPath = ttk.Button(self, image=folderIcon, command=lambda: selectDirectory(self.xmlPath))
		btnxmlPath.image = folderIcon
		btnxmlPath.grid(row=26, column=12, sticky="W")

		# Save and Return 
		btnStartPage = ttk.Button(self, text="Save", command=lambda: [self.updateVariable(), controller.show_frame(StartPage)])
		btnStartPage.grid(row=100, column=1, sticky="WE")

		def selectDirectory(var):
			directory = filedialog.askdirectory()
			var.set(directory)
			return var
		
	def updateVariable(self, event=None):
		config['camera']['body'] = str(self.cameraBody.get())
		config['camera']['lens'] = str(self.lens.get())
		config['camera']['trigger'] = str(self.triggerMethod.get())
		config['camera']['exposure'] = str(self.exposureLength.get())
		config['cnc']['xOverlap'] = str(self.xOverlap.get())
		config['cnc']['yOverlap'] = str(self.yOverlap.get())
		config['cnc']['pause'] = str(self.pauseLength.get())
		config['cnc']['stackingSize'] = str(self.stackingSize.get())
		config['filepaths']['download'] = str(self.download.get())
		config['filepaths']['imagePath'] = str(self.imagePath.get())
		config['filepaths']['xmlPath'] = str(self.xmlPath.get())
		updateConfig(config, configpath)


# Initilization Page
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
		btnCNCUpSmall = ttk.Button(self, text="Up5", command=lambda: moveCNCbyAmount(0, 5, machine))
		btnCNCUpMed = ttk.Button(self, text="Up50", command=lambda: moveCNCbyAmount(0, 50, machine))
		btnCNCUpLarge = ttk.Button(self, text="Up100", command=lambda: moveCNCbyAmount(0, 100, machine))
		btnCNCLeftSmall = ttk.Button(self, text="Left5", command=lambda: moveCNCbyAmount(-5, 0, machine))
		btnCNCLeftMed = ttk.Button(self, text="Left50", command=lambda: moveCNCbyAmount(-50, 0, machine))
		btnCNCLeftLarge = ttk.Button(self, text="Left100", command=lambda: moveCNCbyAmount(-100, 0, machine))
		btnCNCDownSmall = ttk.Button(self, text="Down5", command=lambda: moveCNCbyAmount(0, -5, machine))
		btnCNCDownMed = ttk.Button(self, text="Down50", command=lambda: moveCNCbyAmount(0, -50, machine))
		btnCNCDownLarge = ttk.Button(self, text="Down100", command=lambda: moveCNCbyAmount(0, -100, machine))
		btnCNCRightSmall = ttk.Button(self, text="Right5", command=lambda: moveCNCbyAmount(5, 0, machine))
		btnCNCRightMed = ttk.Button(self, text="Right50", command=lambda: moveCNCbyAmount(50, 0, machine))
		btnCNCRightLarge = ttk.Button(self, text="Right100", command=lambda: moveCNCbyAmount(100, 0, machine))
	
		
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
	

config = getConfig(configpath)
machine = openCNC(config["cnc"]["port"])
xmlData = ET.Element("data")
xmlTree = ET.ElementTree(xmlData)

#RunApplication Start
app = LeafCNC()

app.tk.mainloop() 
# leafcnc
Leaf CNC and Camera Control
Created By Fultonensis Consulting for Benjamin Blonder

This is a lab-based solution to automate capturing high-resolution photographs of leaf veins by capturing multiple images both in the X and Y axes, as well as providing the flexibility of Z axis manipulation or software control for focus stacking.  A Canon DSLR camera will be used with a 100mm macro lens.  Leaf samples will be sandwiched between glass plates, placed on the bed of the machine, and lit from below so only transmitted light will be captured.  Samples will be sized up to roughly 30cm x 30cm. 

This software controls the CNC machine and the camera.

Prerequisites
	Gphoto2
		Install with script found at: https://github.com/gonzalo/gphoto2-updater
		
	Apt-Get Installs
		libxml2-dev 
		libxslt-dev
		python-dev
		python3-lxml
	Pip3 Installs
		pyserial
		Pillow
		gphoto2
		
		
Installed for Testing Purposes (To Be Removed Later)
	bCNC (https://github.com/vlachoudis/bCNC)
	
	
	
Max X = 360
Max Y = -470


Electronics Notes
	Power Requirements
		12V
			CNC Machine (has AC Adapter)
			Monitor for Camera
			Monitor for Pi
			
		7.4V 
			Camera (has AC Adapter)
		
		5V
			Raspberry Pi (has AC Adapter)
			Monitor for Camera
			Monitor for Pi
			Lightbox (has AC Adapter)
			
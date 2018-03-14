import subprocess
import glob
import os, sys
from PyQt4 import QtGui, QtCore

'''    
# Personal notes 'n' stuff

      #numSec="ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1"

      #...WEBM_CREATOR/ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 [INSERT VIDEO HERE].mp4

      # We can use this command, along with copies of ffmpeg & ffprobe in create.py directory, to create executable:
      # sudo pyinstaller -F  --add-data 'ffmpeg1:.' --add-data 'ffprobe1:.' create.py
'''

# Changes our current working directory to same one that script resides in. Necessary for pyinstaller executable.
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

# Print current working directory
print(os.getcwd())

# Lots of terrible global variables. Let's promise ourselves to fix this later, mkay?
stopped = False
videosList = []
numWEBM = 5
lenLimit = 0
totalSeconds = 0
webmDuration = 8
numFiles = 0
webmWidth = 500
selectedVideo = ""
returnedVideoList = False 
someprocess = QtCore.QProcess()

# We'll need this to access ffmpeg & ffprobe once pyinstaller has created one-file executable
# Returns some sort of temp directory
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Here's where we can find ffmpeg & ffprobe
ffmpeg_path = resource_path('ffmpeg1')
ffprobe_path = resource_path('ffprobe1')

# Use ffmpeg to create WEBM and read its stdout. To-Do:Use some regex later for progress bar
def createWebm(fileName, startTime):
    # Here's what the output files will be called
    fileName_webm = os.path.splitext(fileName)[0] + '_' + str(numFiles) + '.webm'

    # Lets ffmpeg know how big to make our WEBM
    scaleString = 'scale=' + str(webmWidth) + ':-2'
    
    args = ['-y',
        '-v', 'info',
        '-ss',  str(startTime),
        '-t',   str(webmDuration),
        '-i' ,  fileName,
        '-vf',  scaleString,
        '-c:v',  'libvpx',
        '-b:v', '1500K',
        '-c:a', 'libvorbis',
        '-an',  fileName_webm]

    GUI.setStatusText("Currently creating: " + fileName_webm)
    someprocess.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    
    # We need this to register clicks on the GUI during ffmpeg process
    app.processEvents()

    # Check to make sure user hasn't pressed stop. Notsureifneeded.jpg
    if (stopped == False):
        someprocess.execute(ffmpeg_path, args)
        someprocess.waitForFinished(-1)
        output = someprocess.readAllStandardOutput()

# Searches current directory for .mp4,.wmv,.avi, and .mpeg videos
def createVideoList():
    for fileType in ["*.mp4", "*.wmv","*.avi", "*.mpeg"]:
        aVideo = glob.glob(fileType)
        if (len(aVideo) > 0):
            videosList.extend(aVideo) 
    global returnedVideoList
    returnedVideoList = True
    return (videosList)

# Takes video name, splits video into intervals, creates WEBM starting at each interval
def processVideo(aVideo):
    global totalSeconds, stopped

    # We can use ffprobe to check the number of seconds in the video
    totalSeconds = subprocess.check_output([
        ffprobe_path      ,
        '-v'              , 'quiet',
        '-show_entries'   , 'format=duration',
        '-of'             , 'csv=%s' % ("p=0"),
        '-i'              ,  aVideo
    ])

    # Y u do dis? Have to look into why this is necessary.
    totalSeconds = float(totalSeconds.decode("utf-8"))
    
    # Makes sure WEBM length "L" isn't created at startTime + L > Length of video
    getLenLimit()

    # Let's skip first 60% of video since it's more exciting that way. TO-DO: Set opt for this later.
    startTime = ( (totalSeconds) * 60 ) / 100
    interval  = ( int(totalSeconds) - startTime ) / numWEBM

    for i in range(numWEBM):
        app.processEvents() 
        if (stopped == False):
            if startTime >= lenLimit:
                break
            global numFiles
            numFiles += 1
            createWebm(aVideo, startTime)
            startTime += interval
        else:
            app.processEvents() 
            GUI.setStatusText("Process killed.")

# Makes sure WEBM length "L" isn't created at startTime + L > Length of video
def getLenLimit():
    global lenLimit
    lenLimit = totalSeconds - webmDuration - 1

# Starts going through all the videos and initiates WEBM creation process
def init():
    global stopped
    stopped = False
    for video in videosList:
        if (stopped == False):
            global numFiles
            numFiles = 0
            processVideo(video)
        else:
            app.processEvents() 
            GUI.setStatusText("Process killed.")
    if (stopped == False):
        GUI.setStatusText("Finished!")

class Window(QtGui.QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.setWindowTitle("WEBM & GIF Creator")
        self.setGeometry(400, 300, 500, 265)
        self.home()

    def home(self):
        # Value to shift slider/label position in y-direction. Just for convenience.
        ySHFT=50
        #================================================================#
        # List to display all the videos in current directory
        self.listWidget = QtGui.QListWidget(self)
        self.listWidget.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.listWidget.itemSelectionChanged.connect(self.setSelected)
        self.listWidget.move(215,10)
        self.listWidget.resize(280,200)
        #================================================================#
        # Duration sliders & Labels
        self.durationSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.durationSlider.setMinimum(1)
        self.durationSlider.setMaximum(30)
        self.durationSlider.setSliderPosition(10)
        self.durationSlider.move(5,90+ySHFT)
        self.durationSlider.resize(170,20)
        self.durationSlider.valueChanged.connect(self.editDurationLabel)

        self.durationLabel = QtGui.QLabel(self)
        self.durationLabel.move(5,70+ySHFT)
        self.durationLabel.resize(200,20)
        #================================================================#
        # Size sliders & Labels
        self.sizeSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.sizeSlider.setMinimum(300)
        self.sizeSlider.setMaximum(3000)
        self.sizeSlider.setSliderPosition(500)
        self.sizeSlider.move(5,135+ySHFT)
        self.sizeSlider.resize(170,20)
        self.sizeSlider.valueChanged.connect(self.editSizeLabel)

        self.sizeLabel = QtGui.QLabel(self)
        self.sizeLabel.move(5,110+ySHFT)
        self.sizeLabel.resize(200,20)
        #================================================================#
        # Number Webms sliders & Labels
        self.numWEBMSlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.numWEBMSlider.setMinimum(1)
        self.numWEBMSlider.setMaximum(50)
        self.numWEBMSlider.setSliderPosition(5)
        self.numWEBMSlider.move(5,183+ySHFT)
        self.numWEBMSlider.resize(170,20)
        self.numWEBMSlider.valueChanged.connect(self.editNumWEBMLabel)

        self.numWEBMLabel = QtGui.QLabel(self)
        self.numWEBMLabel.move(5,155+ySHFT)
        self.numWEBMLabel.resize(200,30)
        #================================================================#
        # Status label during WEBM creation
        self.statusLabel = QtGui.QLabel(self)
        self.statusLabel.move(215,210)
        self.statusLabel.resize(280,30)
        #================================================================#
        # Start button for creating WEBMs from all items in list
        startBtn = QtGui.QPushButton("Create WEBM \n(ALL)", self)
        startBtn.clicked.connect(self.createMedia)
        startBtn.resize(110,50)
        startBtn.move(0,5)
        #================================================================#
        # Start button for creating WEBMs only from selected videos
        startSingleBtn = QtGui.QPushButton("Create WEBM \n(SELECTED)", self)
        startSingleBtn.clicked.connect(self.createSelectedMedia)
        startSingleBtn.resize(110,50)
        startSingleBtn.move(0,50)
        #================================================================#
        # Button attempts to kill the ffmpeg process. Doesn't always work.
        stopBtn = QtGui.QPushButton("Stop process", self)
        stopBtn.clicked.connect(self.stopProcess)
        stopBtn.resize(110,50)
        stopBtn.move(105,5)
        #================================================================#
        # Initialize the values for each label
        self.populateListLabel()
        self.editDurationLabel()
        self.editSizeLabel()
        self.editNumWEBMLabel()
        self.show()

    # Determine the video currently selected in the video list
    def setSelected(self):
        global selectedVideo
        selectedVideo = self.listWidget.selectedItems()[0].text()

    # Attempts to kill WEBM creation process
    def stopProcess(self):
        global someprocess, stopped
        someprocess.kill()
        stopped = True

    # Sets label to user selected WEBM duration from slider value
    def editDurationLabel(self):
        self.durationLabel.setText("WEBM Duration: " + str(self.durationSlider.value()) + " seconds")
        self.editWebmDuration()

    # Sets webm duration to corresponding slider value
    def editWebmDuration(self):
        global webmDuration
        webmDuration = self.durationSlider.value()

    # Set the WEBM width label text to slider value
    def editSizeLabel(self):
        self.sizeLabel.setText("WEBM Width: " + str(self.sizeSlider.value()) + " px")
        self.editSize() 

    # Set WEBM width variable to corresponding slider value
    def editSize(self):
        global webmWidth
        webmWidth = self.sizeSlider.value()

    # Sets WEBM number label text to slider value
    def editNumWEBMLabel(self):
        self.numWEBMLabel.setText("Number of WEBMs: " + str(self.numWEBMSlider.value()))
        self.editNumWEBM() 

    # Sets number of WEBMs variable to corresponding slider value
    def editNumWEBM(self):
        global numWEBM
        numWEBM = self.numWEBMSlider.value()

    # Sets the status label text to current WEBM we're creating
    def setStatusText(self, status):
        #self.statusLabel.setText(status)
        self.statusLabel.setText(status)

    # If there's videos in current folder, we show them in the list widget
    def populateListLabel(self):
        videos_array = createVideoList()
        print(len(videos_array))
        if (len(videos_array) > 0):
            for video in videos_array:
                print(video)
                item = QtGui.QListWidgetItem()
                item.setText(video)
                self.listWidget.addItem(item)
        else:
            print(len(videos_array))
            item = QtGui.QListWidgetItem()
            self.listWidget.addItem("No videos found")
    
    # Starts creating WEBMs from all videos in list
    def createMedia(self):
        init()

    # Starts creating WEBMs only from selected video in list
    def createSelectedMedia(self):
        processVideo(selectedVideo)

app = QtGui.QApplication(sys.argv)
GUI = Window()
def run():
    app.exec_()

run()


















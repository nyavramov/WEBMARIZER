import subprocess
import glob
import os, sys
import platform
from PyQt5 import QtGui, QtCore, QtWidgets
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

#sudo pyinstaller -F  --add-data 'ffmpeg1:.' --add-data 'ffprobe1:.' webmarizer.py

# Lots of terrible global variables. Let's promise ourselves to fix this later, mkay?
stopped = False
bitrate = 1500
videosList = []
numWEBM = 5
lenLimit = 0
totalSeconds = 0
fileSize = 0
outputDuration = 8
numFiles = 0
outputWidth = 500
returnedVideoList = False 
selectedVideo = ""
audioEnabled = False
audioDisable = '-an'
targetSizeSet = False
output_type = 'GIF'

FFmpegProcess = QtCore.QProcess()

'''
      fileName="${1}"; start="${2}"; outputName=${fileName%.*}

      echo "Creating ${outputName}_${numFiles}.gif at time: ${start} seconds."

      ffmpeg -ss "${start}" -t "${duration}" -v error -i "${fileName}" \
            -vf "$filters,palettegen" \-y palette.png # Create palette for video
      ffmpeg -ss "${start}" -t "${duration}" -v error -i "${fileName}" \
            -i palette.png -lavfi "$filters [x]; [x][1:v] paletteuse" -y \
            "${outputName}_${numFiles}.gif" # Create GIF
      args_palette = [
        '-ss',  str(startTime),
        '-t',   str(outputDuration),
        '-i' ,  fileName,
        '-vf',  filters +',palettegen',
        '-y',   'palette.png'
    ]

      rm "palette.png" #Remove palette
'''

# We'll need this to access ffmpeg & ffprobe once pyinstaller has created one-file executable
# Returns some sort of temp directory
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_path, relative_path)
    return path

# Here's where we can find ffmpeg & ffprobe. Check platform first, though.
if (platform.system() == 'Windows'):
    ffmpeg_path = resource_path('ffmpeg.exe')
    ffprobe_path = resource_path('ffprobe.exe')
else:
    ffmpeg_path = resource_path('ffmpeg')
    ffprobe_path = resource_path('ffprobe')

def createGif(fileName, startTime):
    fileName_gif = os.path.splitext(fileName)[0] + '_' + str(numFiles) + '.gif'
    scaleString = 'scale=' + str(outputWidth) + ':-2'
    filters='fps=20,scale=' + str(outputWidth) + ':-1:flags=lanczos'
    
    # 1st Generate a pallete with ffmpeg
    args_palette = [
        '-ss',  str(startTime),
        '-t',   str(outputDuration),
        '-i' ,  fileName,
        '-vf',  filters+",palettegen",
        '-y',   'palette.png'
    ]

    # 2nd Generate the gif using the palette
    args_gif = [
        '-ss',  str(startTime),
        '-t',   str(outputDuration),
        '-i' ,  fileName,
        '-i',   'palette.png',
        '-fs',  str(fileSize/1000) + "M",
        '-lavfi', filters+"[x];[x][1:v]paletteuse",
        '-y', fileName_gif
    ]

    print("THE FILE SIZE IS: " + str(fileSize/1000) + "M")

    GUI.setStatusText("Currently creating: " + fileName_gif)
    FFmpegProcess.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()

    if (stopped == False):
        FFmpegProcess.execute(ffmpeg_path, args_palette)
        FFmpegProcess.waitForFinished(-1)
        FFmpegProcess.execute(ffmpeg_path, args_gif)
        FFmpegProcess.waitForFinished(-1)
        os.remove("palette.png")


# Use ffmpeg to create WEBM and read its stdout. To-Do:Use some regex later for progress bar
def createWebm(fileName, startTime):
    fileName_webm = os.path.splitext(fileName)[0] + '_' + str(numFiles) + '.webm'
    scaleString = 'scale=' + str(outputWidth) + ':-2'
    args = ['-y',
        '-ss',  str(startTime),
        '-t',   str(outputDuration),
        '-i' ,  fileName,
        '-vf',  scaleString,
        '-c:v',  'libvpx',
        '-b:v', str(bitrate)+"K",
        '-b:a', '96K',
        '-c:a', 'libvorbis']

    if not audioEnabled:
        args.append(audioDisable)
    
    args.append(fileName_webm)

    GUI.setStatusText("Currently creating: " + fileName_webm)
    FFmpegProcess.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()
    if (stopped == False):
        FFmpegProcess.execute(ffmpeg_path, args)
        FFmpegProcess.waitForFinished(-1)

# Searches current directory for .mp4,.wmv,.avi, and .mpeg videos
def createVideoList():
    for fileType in ["*.mp4", "*.wmv","*.avi", "*.mpeg"]:
        aVideo = glob.glob(fileType)
        if (len(aVideo) > 0):
            videosList.extend(aVideo) 
    global returnedVideoList
    returnedVideoList = True
    return (videosList)

#numSec="ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1"
# Takes video name, splits video into intervals, creates WEBM starting at each interval
def processVideo(aVideo):
    global totalSeconds, stopped

    args = [
        ffprobe_path      ,
        '-v'              , 'quiet',
        '-show_entries'   , 'format=duration',
        '-of'             , 'csv=%s' % ("p=0"),
        '-i'              ,  aVideo
    ]

    # We can use ffprobe to check the number of seconds in the video
    totalSeconds = subprocess.check_output(args)

    # Y u do dis? Have to look into why this is necessary.
    totalSeconds = float(totalSeconds.decode("utf-8"))
    print(totalSeconds)
    # Makes sure WEBM length "L" isn't created at startTime + L > Length of video
    getLenLimit()

    # knowyourmeme.com/memes/the-wadsworth-constant
    WadsWorthConstant = 30

    # Let's skip first 30% of video. Add opt for this later.
    startTime = ( (totalSeconds) * WadsWorthConstant) / 100
    interval  = ( int(totalSeconds) - startTime ) / numWEBM

    for i in range(numWEBM):
        app.processEvents() 
        if (stopped == False): 
            if startTime >= lenLimit:
                break
            global numFiles
            numFiles += 1
            if output_type == 'WEBM':
                createWebm(aVideo, startTime)
            else:
                createGif(aVideo, startTime)

            startTime += interval
        else:
            app.processEvents() 
            GUI.setStatusText("Process killed.")

# Makes sure WEBM length "L" isn't created at startTime + L > Length of video
def getLenLimit():
    global lenLimit
    lenLimit = totalSeconds - outputDuration - 1

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

# Form implementation generated from reading ui file 'webmarizer_template.ui'
# Created by: PyQt5 UI code generator 5.10.1
# WARNING! All changes made in this file will be lost!
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(803, 597)
        MainWindow.setStyleSheet("background-color:rgb(244, 240, 244);\n"
        "padding:0px;\n")
        MainWindow.setFixedSize(803, 597)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.listWidget = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(440, 40, 351, 501))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy)
        self.listWidget.setStyleSheet("background-color:#fff;")
        self.listWidget.setObjectName("listWidget")
        self.videoListTitleLabel = QtWidgets.QLabel(self.centralwidget)
        self.videoListTitleLabel.setGeometry(QtCore.QRect(590, 10, 71, 30))
        self.videoListTitleLabel.setObjectName("videoListTitleLabel")
        self.statusLabel = QtWidgets.QLabel(self.centralwidget)
        self.statusLabel.setGeometry(QtCore.QRect(440, 550, 351, 31))
        self.statusLabel.setText("")
        self.statusLabel.setObjectName("statusLabel")
        self.generalOptionsTitleLabel = QtWidgets.QLabel(self.centralwidget)
        self.generalOptionsTitleLabel.setGeometry(QtCore.QRect(160, 10, 170,30))
        self.generalOptionsTitleLabel.setObjectName("generalOptionsTitleLabel")
        self.createBtn = QtWidgets.QPushButton(self.centralwidget)
        self.createBtn.setGeometry(QtCore.QRect(20, 510, 121, 41))
        self.createBtn.setObjectName("createBtn")
        self.startSingleBtn = QtWidgets.QPushButton(self.centralwidget)
        self.startSingleBtn.setGeometry(QtCore.QRect(160, 510, 121, 41))
        self.startSingleBtn.setObjectName("startSingleBtn")
        self.stopBtn = QtWidgets.QPushButton(self.centralwidget)
        self.stopBtn.setGeometry(QtCore.QRect(300, 510, 121, 41))
        self.stopBtn.setObjectName("stopBtn")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(20, 40, 401, 461))
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.durationLabel = QtWidgets.QLabel(self.widget)
        self.durationLabel.setEnabled(True)
        self.durationLabel.setTextFormat(QtCore.Qt.RichText)
        self.durationLabel.setObjectName("durationLabel")
        self.verticalLayout.addWidget(self.durationLabel)
        self.durationSlider = QtWidgets.QSlider(self.widget)
        self.durationSlider.setMinimum(1)
        self.durationSlider.setMaximum(30)
        self.durationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.durationSlider.setObjectName("durationSlider")
        self.verticalLayout.addWidget(self.durationSlider)
        self.sizeLabel = QtWidgets.QLabel(self.widget)
        self.sizeLabel.setEnabled(True)
        self.sizeLabel.setTextFormat(QtCore.Qt.RichText)
        self.sizeLabel.setObjectName("sizeLabel")
        self.verticalLayout.addWidget(self.sizeLabel)
        self.sizeSlider = QtWidgets.QSlider(self.widget)
        self.sizeSlider.setMinimum(300)
        self.sizeSlider.setMaximum(3000)
        self.sizeSlider.setOrientation(QtCore.Qt.Horizontal)
        self.sizeSlider.setObjectName("sizeSlider")
        self.verticalLayout.addWidget(self.sizeSlider)
        self.numWEBMLabel = QtWidgets.QLabel(self.widget)
        self.numWEBMLabel.setEnabled(True)
        self.numWEBMLabel.setTextFormat(QtCore.Qt.RichText)
        self.numWEBMLabel.setObjectName("numWEBMLabel")
        self.verticalLayout.addWidget(self.numWEBMLabel)
        self.numWEBMSlider = QtWidgets.QSlider(self.widget)
        self.numWEBMSlider.setMinimum(1)
        self.numWEBMSlider.setMaximum(50)
        self.numWEBMSlider.setOrientation(QtCore.Qt.Horizontal)
        self.numWEBMSlider.setObjectName("numWEBMSlider")
        self.verticalLayout.addWidget(self.numWEBMSlider)
        self.bitrateLabel = QtWidgets.QLabel(self.widget)
        self.bitrateLabel.setEnabled(True)
        self.bitrateLabel.setTextFormat(QtCore.Qt.RichText)
        self.bitrateLabel.setObjectName("bitrateLabel")
        self.verticalLayout.addWidget(self.bitrateLabel)
        self.bitRateSlider = QtWidgets.QSlider(self.widget)
        self.bitRateSlider.setMinimum(1000)
        self.bitRateSlider.setMaximum(15000)
        self.bitRateSlider.setOrientation(QtCore.Qt.Horizontal)
        self.bitRateSlider.setObjectName("bitRateSlider")
        self.verticalLayout.addWidget(self.bitRateSlider)
        self.targetFileSizeLabel = QtWidgets.QLabel(self.widget)
        self.targetFileSizeLabel.setEnabled(True)
        self.targetFileSizeLabel.setTextFormat(QtCore.Qt.RichText)
        self.targetFileSizeLabel.setObjectName("targetFileSizeLabel")
        self.verticalLayout.addWidget(self.targetFileSizeLabel)
        self.fileSizeSlider = QtWidgets.QSlider(self.widget)
        self.fileSizeSlider.setMinimum(100)
        self.fileSizeSlider.setMaximum(15000)
        self.fileSizeSlider.setOrientation(QtCore.Qt.Horizontal)
        self.fileSizeSlider.setObjectName("fileSizeSlider")
        self.verticalLayout.addWidget(self.fileSizeSlider)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.audioCheckBox = QtWidgets.QCheckBox(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.audioCheckBox.sizePolicy().hasHeightForWidth())
        self.audioCheckBox.setSizePolicy(sizePolicy)
        self.audioCheckBox.setText("")
        self.audioCheckBox.setObjectName("audioCheckBox")
        self.horizontalLayout_2.addWidget(self.audioCheckBox)
        self.enableAudioLabel = QtWidgets.QLabel(self.widget)
        self.enableAudioLabel.setEnabled(True)
        self.enableAudioLabel.setTextFormat(QtCore.Qt.RichText)
        self.enableAudioLabel.setObjectName("enableAudioLabel")
        self.horizontalLayout_2.addWidget(self.enableAudioLabel)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.targetFileSizeCheckBox = QtWidgets.QCheckBox(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.audioCheckBox.sizePolicy().hasHeightForWidth())
        self.targetFileSizeCheckBox.setSizePolicy(sizePolicy)
        self.targetFileSizeCheckBox.setText("")
        self.targetFileSizeCheckBox.setObjectName("targetFileSizeCheckBox")
        self.horizontalLayout.addWidget(self.targetFileSizeCheckBox)
        self.targetSizeCheckmarkLabel = QtWidgets.QLabel(self.widget)
        self.targetSizeCheckmarkLabel.setEnabled(True)
        self.targetSizeCheckmarkLabel.setTextFormat(QtCore.Qt.RichText)
        self.targetSizeCheckmarkLabel.setObjectName("targetSizeCheckmarkLabel")
        self.horizontalLayout.addWidget(self.targetSizeCheckmarkLabel)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.durationSlider.raise_()
        self.listWidget.raise_()
        self.durationLabel.raise_()
        self.sizeSlider.raise_()
        self.sizeLabel.raise_()
        self.numWEBMSlider.raise_()
        self.numWEBMLabel.raise_()
        self.audioCheckBox.raise_()
        self.targetSizeCheckmarkLabel.raise_()
        self.targetFileSizeCheckBox.raise_()
        self.videoListTitleLabel.raise_()
        self.statusLabel.raise_()
        self.generalOptionsTitleLabel.raise_()
        self.durationSlider.raise_()
        self.createBtn.raise_()
        self.startSingleBtn.raise_()
        self.stopBtn.raise_()
        self.gifModeCheckBox = QtWidgets.QCheckBox(self.widget)
        sizePolicy.setHeightForWidth(self.gifModeCheckBox.sizePolicy().hasHeightForWidth())
        self.gifModeCheckBox.setSizePolicy(sizePolicy)
        self.gifModeCheckBox.setText("")
        self.gifModeCheckBox.setObjectName("gifModeCheckBox")
        self.gifModeCheckBox.setEnabled(True)
        self.gifModeCheckBox.stateChanged.connect(self.enableGifMode)
        self.horizontalLayout_2.addWidget(self.gifModeCheckBox)
        self.gifModeLabel = QtWidgets.QLabel(self.widget)
        self.gifModeLabel.setEnabled(True)
        self.gifModeLabel.setTextFormat(QtCore.Qt.RichText)
        self.gifModeLabel.setObjectName("gifModeLabel")
        self.horizontalLayout_2.addWidget(self.gifModeLabel)
        self.listWidget.itemSelectionChanged.connect(self.setSelected)
        self.listWidget.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.durationSlider.valueChanged.connect(self.editDurationLabel)
        self.sizeSlider.valueChanged.connect(self.editSizeLabel)
        self.numWEBMSlider.valueChanged.connect(self.editNumWEBMLabel)
        self.createBtn.clicked.connect(self.createMedia)
        self.startSingleBtn.clicked.connect(self.createSelectedMedia)
        self.bitRateSlider.valueChanged.connect(self.editBitrateLabel)
        self.audioCheckBox.stateChanged.connect(self.editAudioCheckBox)
        self.targetFileSizeCheckBox.stateChanged.connect(self.editTargetFileSizeCheckBox)
        self.fileSizeSlider.valueChanged.connect(self.editTargetFileSizeSliderLabel)
        self.stopBtn.clicked.connect(self.stopProcess)
        self.durationSlider.setSliderPosition(10)
        self.sizeSlider.setSliderPosition(500)
        self.numWEBMSlider.setSliderPosition(5)
        self.bitRateSlider.setSliderPosition(1500)
        self.fileSizeSlider.setSliderPosition(4000)
        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.populateListLabel()
        self.editDurationLabel()
        self.editSizeLabel()
        self.editNumWEBMLabel()
        self.editBitrateLabel()
        self.editTargetFileSizeSliderLabel()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "WEBMARIZER"))
        self.videoListTitleLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:12pt;\">Videos</span></p></body></html>"))
        self.generalOptionsTitleLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:12pt;\">General Options</span></p></body></html>"))
        self.createBtn.setText(_translate("MainWindow", "Create WEBM\n"
        "(All videos)"))
        self.startSingleBtn.setText(_translate("MainWindow", "Create WEBM \n"
        "(Selected videos)"))
        self.stopBtn.setText(_translate("MainWindow", "Stop Process"))
        self.durationLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Webm Duration: </span></p></body></html>"))
        self.sizeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">WEBM Width:</span></p></body></html>"))
        self.numWEBMLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Number of WEBMs:</span></p></body></html>"))
        self.bitrateLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Bitrate:</span></p></body></html>"))
        self.targetFileSizeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Target File Size:</span></p></body></html>"))
        
        if (platform.system() == 'Windows'): # For some reason Mac OSX and Windows font sizes differ? 
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Gif Mode</span></p></body></html>"))
        else:
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Gif Mode</span></p></body></html>"))

    # Determine the video currently selected in the video list
    def setSelected(self):
        global selectedVideo
        selectedVideo = self.listWidget.selectedItems()[0].text()

    # Attempts to kill WEBM creation process
    def stopProcess(self):
        global FFmpegProcess, stopped
        FFmpegProcess.kill()
        stopped = True

    def enableGifMode(self):
        global output_type
        if (self.gifModeCheckBox.isChecked()):
            output_type = 'GIF'
            self.durationLabel.setText("GIF Duration: " + str(self.durationSlider.value()) + " seconds")
            self.sizeLabel.setText("GIF Width: " + str(self.sizeSlider.value()) + " px")
            self.numWEBMLabel.setText("Number of GIFs: " + str(self.numWEBMSlider.value()))
        else:
            output_type = 'WEBM'
            self.editDurationLabel()
            self.editSizeLabel()
            self.editNumWEBMLabel()
        print("Current Mode: " + output_type)


    # Sets label to user selected WEBM duration from slider value
    def editDurationLabel(self):
        self.durationLabel.setText("WEBM Duration: " + str(self.durationSlider.value()) + " seconds")
        self.editoutputDuration()

    # Sets webm duration to corresponding slider value
    def editoutputDuration(self):
        global outputDuration
        outputDuration = self.durationSlider.value()
        if targetSizeSet:
            self.editFileSize()

    # Set the bitrate label value
    def editBitrateLabel(self):
        if targetSizeSet:
            self.bitrateLabel.setText("Bitrate: " + str(self.bitRateSlider.value()) + " kbits/s (Slider disabled)")
        else:
            self.bitrateLabel.setText("Bitrate: " + str(self.bitRateSlider.value()) + " kbits/s")
        self.editBitrate()
    
    # Changes bitrate to corresponding slider value
    def editBitrate(self):
        global bitrate
        bitrate = self.bitRateSlider.value()

    # Changes boolean for audio enabled
    def editAudioCheckBox(self):
        global audioEnabled
        audioEnabled = self.audioCheckBox.isChecked()

    # Changes value of target file size 
    def editTargetFileSizeCheckBox(self):
        global targetSizeSet
        targetSizeSet = self.targetFileSizeCheckBox.isChecked()
        self.editTargetFileSizeSliderLabel()
        self.editBitrateLabel()

    # Set the target file size label
    def editTargetFileSizeSliderLabel(self):    
        if targetSizeSet:
            self.targetFileSizeLabel.setText("Target File Size: " + str(self.fileSizeSlider.value()/1000) + " MB")
            self.editFileSize()
            self.bitRateSlider.setEnabled(False)
            self.fileSizeSlider.setEnabled(True)
        else:
            self.fileSizeSlider.setEnabled(False)
            self.bitRateSlider.setEnabled(True)
            self.targetFileSizeLabel.setText("Target File Size: Disabled")

    # Change value of file size to corresponding slider value
    def editFileSize(self):
        global fileSize
        fileSize = self.fileSizeSlider.value()
        video_bitrate = ( ( fileSize * 8 * 1000 ) / outputDuration ) - 96000 #96 kbps audio bitrate
        self.bitRateSlider.setSliderPosition(video_bitrate / 1000)

    # Set the WEBM width label text to slider value
    def editSizeLabel(self):
        self.sizeLabel.setText("WEBM Width: " + str(self.sizeSlider.value()) + " px")
        self.editSize() 

    # Set WEBM width variable to corresponding slider value
    def editSize(self):
        global outputWidth
        outputWidth = self.sizeSlider.value()

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
                item = QtWidgets.QListWidgetItem()
                item.setText(video)
                self.listWidget.addItem(item)
        else:
            print(len(videos_array))
            item = QtWidgets.QListWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.listWidget.addItem("No videos found")

    # Starts creating WEBMs from all videos in list
    def createMedia(self):
        init()

    # Starts creating WEBMs only from selected video in list
    def createSelectedMedia(self):
        processVideo(selectedVideo)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    GUI = Ui_MainWindow()
    GUI.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


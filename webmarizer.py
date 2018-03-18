import subprocess
import glob
import os, sys
import platform
from PyQt5 import QtGui, QtCore, QtWidgets
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

#sudo pyinstaller -F  --add-data 'ffmpeg:.' --add-data 'ffprobe:.' webmarizer.py

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
output_type = 'WEBM'
single_mode = False
time_array = [0,0,0]

FFmpegProcess = QtCore.QProcess()

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
        '-i',   'palette.png'
    ]

    gif_opt_withSize = [
        '-fs', str(fileSize/1000) + "M",
        '-lavfi', filters+"[x];[x][1:v]paletteuse",
        '-y', fileName_gif
    ]

    gif_opts_noSize = [
        '-lavfi', filters+"[x];[x][1:v]paletteuse",
        '-y', fileName_gif
    ]

    if targetSizeSet:
        args_gif.extend(gif_opt_withSize)
    else:
        args_gif.extend(gif_opts_noSize)

    print("THE FILE SIZE IS: " + str(fileSize/1000) + "M")
    print("Args palette: " + str(args_palette))
    print("Args gif: " + str(args_gif))

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
    global totalSeconds, stopped, numWEBM

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

    if single_mode:
        numWEBM = 1

    for i in range(numWEBM):
        app.processEvents() 
        if (stopped == False): 
            if startTime >= lenLimit:
                break
            global numFiles
            numFiles += 1
            
            if output_type == 'WEBM':
                if single_mode:
                    custom_start_time = (time_array[0] * 3600) + (time_array[1] * 60) + time_array[2]
                    print(time_array[0])
                    print(time_array[1])
                    print(time_array[2])
                    createWebm(aVideo, custom_start_time)
                else:
                    createWebm(aVideo, startTime)
            else:
                if single_mode:
                    custom_start_time = (time_array[0] * 3600) + (time_array[1] * 60) + time_array[2]
                    createGif(aVideo, custom_start_time)
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
        MainWindow.resize(829, 330)
        MainWindow.setStyleSheet("background-color:rgb(244, 240, 244);\n"
        "padding:0px;\n")
        MainWindow.setDocumentMode(False)
        MainWindow.setTabShape(QtWidgets.QTabWidget.Triangular)
        MainWindow.setUnifiedTitleAndToolBarOnMac(True)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(0, -30, 831, 341))
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.tabWidget.setFont(font)
        self.tabWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tabWidget.setAutoFillBackground(False)
        self.tabWidget.setStyleSheet("QTabBar::tab {  width: 300px; }\n"
        "\n"
        "QTabWidget::tab-bar {\n"
        "    top:30;\n"
        "    padding-left:0;\n"
        "    background:white;\n"
        "    width:835px;\n"
        "}\n"
        "\n"
        "QTabWidget::pane {\n"
        "    border: 0 solid white;\n"
        "}")
        self.tabWidget.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setObjectName("tabWidget")
        self.generalTab = QtWidgets.QWidget()
        self.generalTab.setAutoFillBackground(False)
        self.generalTab.setStyleSheet("QTabBar {\n"
        "    qproperty-drawBase: 0;\n"
        "}")
        self.generalTab.setObjectName("generalTab")
        self.layoutWidget = QtWidgets.QWidget(self.generalTab)
        self.layoutWidget.setGeometry(QtCore.QRect(20, 40, 381, 211))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.durationLabel = QtWidgets.QLabel(self.layoutWidget)
        self.durationLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        font.setBold(False)
        font.setWeight(50)
        self.durationLabel.setFont(font)
        self.durationLabel.setStyleSheet("")
        self.durationLabel.setTextFormat(QtCore.Qt.RichText)
        self.durationLabel.setObjectName("durationLabel")
        self.verticalLayout.addWidget(self.durationLabel)
        self.durationSlider = QtWidgets.QSlider(self.layoutWidget)
        self.durationSlider.setStyleSheet("QSlider::handle:horizontal {\n"
        "    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);\n"
        "    border: 1px solid #5c5c5c;\n"
        "    width: 18px;\n"
        "    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
        "    border-radius: 3px;\n"
        "}\n"
        "\n"
        "QSlider::groove:horizontal {\n"
        "    border: 1px solid #999999;\n"
        "    height: 9px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
        "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);\n"
        "    margin: 2px 0;\n"
        "\n"
        "}")
        self.durationSlider.setMinimum(1)
        self.durationSlider.setMaximum(30)
        self.durationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.durationSlider.setObjectName("durationSlider")
        self.verticalLayout.addWidget(self.durationSlider)
        spacerItem = QtWidgets.QSpacerItem(20, 25, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.verticalLayout.addItem(spacerItem)
        self.sizeLabel = QtWidgets.QLabel(self.layoutWidget)
        self.sizeLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.sizeLabel.setFont(font)
        self.sizeLabel.setTextFormat(QtCore.Qt.RichText)
        self.sizeLabel.setObjectName("sizeLabel")
        self.verticalLayout.addWidget(self.sizeLabel)
        self.sizeSlider = QtWidgets.QSlider(self.layoutWidget)
        self.sizeSlider.setStyleSheet("QSlider::handle:horizontal {\n"
        "    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);\n"
        "    border: 1px solid #5c5c5c;\n"
        "    width: 18px;\n"
        "    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
        "    border-radius: 3px;\n"
        "}\n"
        "\n"
        "QSlider::groove:horizontal {\n"
        "    border: 1px solid #999999;\n"
        "    height: 9px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
        "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);\n"
        "    margin: 2px 0;\n"
        "\n"
        "}")
        self.sizeSlider.setMinimum(300)
        self.sizeSlider.setMaximum(3000)
        self.sizeSlider.setOrientation(QtCore.Qt.Horizontal)
        self.sizeSlider.setObjectName("sizeSlider")
        self.verticalLayout.addWidget(self.sizeSlider)
        spacerItem1 = QtWidgets.QSpacerItem(20, 25, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.verticalLayout.addItem(spacerItem1)
        self.numWEBMLabel = QtWidgets.QLabel(self.layoutWidget)
        self.numWEBMLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.numWEBMLabel.setFont(font)
        self.numWEBMLabel.setTextFormat(QtCore.Qt.RichText)
        self.numWEBMLabel.setObjectName("numWEBMLabel")
        self.verticalLayout.addWidget(self.numWEBMLabel)
        self.numWEBMSlider = QtWidgets.QSlider(self.layoutWidget)
        self.numWEBMSlider.setStyleSheet("QSlider::handle:horizontal {\n"
        "    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);\n"
        "    border: 1px solid #5c5c5c;\n"
        "    width: 18px;\n"
        "    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
        "    border-radius: 3px;\n"
        "}\n"
        "\n"
        "QSlider::groove:horizontal {\n"
        "    border: 1px solid #999999;\n"
        "    height: 9px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
        "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);\n"
        "    margin: 2px 0;\n"
        "\n"
        "}")
        self.numWEBMSlider.setMinimum(1)
        self.numWEBMSlider.setMaximum(50)
        self.numWEBMSlider.setOrientation(QtCore.Qt.Horizontal)
        self.numWEBMSlider.setObjectName("numWEBMSlider")
        self.verticalLayout.addWidget(self.numWEBMSlider)
        self.listWidget = QtWidgets.QListWidget(self.generalTab)
        self.listWidget.setGeometry(QtCore.QRect(430, 70, 381, 171))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.listWidget.setFont(font)
        self.listWidget.setStyleSheet("background-color:#fff;\n"
        "border:1px solid blue;")
        self.listWidget.setWordWrap(True)
        self.listWidget.setObjectName("listWidget")
        self.videoListTitleLabel = QtWidgets.QLabel(self.generalTab)
        self.videoListTitleLabel.setGeometry(QtCore.QRect(590, 35, 61, 31))
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        font.setBold(True)
        font.setWeight(75)
        self.videoListTitleLabel.setFont(font)
        self.videoListTitleLabel.setObjectName("videoListTitleLabel")
        self.tabWidget.addTab(self.generalTab, "")
        self.advancedTab = QtWidgets.QWidget()
        self.advancedTab.setObjectName("advancedTab")
        self.layoutWidget_2 = QtWidgets.QWidget(self.advancedTab)
        self.layoutWidget_2.setGeometry(QtCore.QRect(420, 40, 371, 102))
        self.layoutWidget_2.setObjectName("layoutWidget_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget_2)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.bitrateLabel = QtWidgets.QLabel(self.layoutWidget_2)
        self.bitrateLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.bitrateLabel.setFont(font)
        self.bitrateLabel.setTextFormat(QtCore.Qt.RichText)
        self.bitrateLabel.setObjectName("bitrateLabel")
        self.verticalLayout_6.addWidget(self.bitrateLabel)
        self.bitRateSlider = QtWidgets.QSlider(self.layoutWidget_2)
        self.bitRateSlider.setStyleSheet("QSlider::handle:horizontal {\n"
        "    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);\n"
        "    border: 1px solid #5c5c5c;\n"
        "    width: 18px;\n"
        "    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
        "    border-radius: 3px;\n"
        "}\n"
        "\n"
        "QSlider::groove:horizontal {\n"
        "    border: 1px solid #999999;\n"
        "    height: 9px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
        "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);\n"
        "    margin: 2px 0;\n"
        "\n"
        "}")
        self.bitRateSlider.setMinimum(1000)
        self.bitRateSlider.setMaximum(15000)
        self.bitRateSlider.setOrientation(QtCore.Qt.Horizontal)
        self.bitRateSlider.setObjectName("bitRateSlider")
        self.verticalLayout_6.addWidget(self.bitRateSlider)
        self.verticalLayout_4.addLayout(self.verticalLayout_6)
        self.targetFileSizeLabel = QtWidgets.QLabel(self.layoutWidget_2)
        self.targetFileSizeLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.targetFileSizeLabel.setFont(font)
        self.targetFileSizeLabel.setTextFormat(QtCore.Qt.RichText)
        self.targetFileSizeLabel.setObjectName("targetFileSizeLabel")
        self.verticalLayout_4.addWidget(self.targetFileSizeLabel)
        self.fileSizeSlider = QtWidgets.QSlider(self.layoutWidget_2)
        self.fileSizeSlider.setStyleSheet("QSlider::handle:horizontal {\n"
        "    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);\n"
        "    border: 1px solid #5c5c5c;\n"
        "    width: 18px;\n"
        "    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
        "    border-radius: 3px;\n"
        "}\n"
        "\n"
        "QSlider::groove:horizontal {\n"
        "    border: 1px solid #999999;\n"
        "    height: 9px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
        "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);\n"
        "    margin: 2px 0;\n"
        "\n"
        "}")
        self.fileSizeSlider.setMinimum(100)
        self.fileSizeSlider.setMaximum(15000)
        self.fileSizeSlider.setOrientation(QtCore.Qt.Horizontal)
        self.fileSizeSlider.setObjectName("fileSizeSlider")
        self.verticalLayout_4.addWidget(self.fileSizeSlider)
        self.verticalLayout_2.addLayout(self.verticalLayout_4)
        self.layoutWidget1 = QtWidgets.QWidget(self.advancedTab)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 40, 401, 152))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.targetFileSizeCheckBox = QtWidgets.QCheckBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.targetFileSizeCheckBox.sizePolicy().hasHeightForWidth())
        self.targetFileSizeCheckBox.setSizePolicy(sizePolicy)
        self.targetFileSizeCheckBox.setText("")
        self.targetFileSizeCheckBox.setObjectName("targetFileSizeCheckBox")
        self.horizontalLayout_7.addWidget(self.targetFileSizeCheckBox)
        self.targetSizeCheckmarkLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.targetSizeCheckmarkLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.targetSizeCheckmarkLabel.setFont(font)
        self.targetSizeCheckmarkLabel.setTextFormat(QtCore.Qt.RichText)
        self.targetSizeCheckmarkLabel.setObjectName("targetSizeCheckmarkLabel")
        self.horizontalLayout_7.addWidget(self.targetSizeCheckmarkLabel)
        self.verticalLayout_3.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.audioCheckBox = QtWidgets.QCheckBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.audioCheckBox.sizePolicy().hasHeightForWidth())
        self.audioCheckBox.setSizePolicy(sizePolicy)
        self.audioCheckBox.setText("")
        self.audioCheckBox.setObjectName("audioCheckBox")
        self.horizontalLayout_8.addWidget(self.audioCheckBox)
        self.enableAudioLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.enableAudioLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.enableAudioLabel.setFont(font)
        self.enableAudioLabel.setTextFormat(QtCore.Qt.RichText)
        self.enableAudioLabel.setObjectName("enableAudioLabel")
        self.horizontalLayout_8.addWidget(self.enableAudioLabel)
        self.verticalLayout_3.addLayout(self.horizontalLayout_8)
        self.verticalLayout_5.addLayout(self.verticalLayout_3)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.gifModeCheckBox = QtWidgets.QCheckBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gifModeCheckBox.sizePolicy().hasHeightForWidth())
        self.gifModeCheckBox.setSizePolicy(sizePolicy)
        self.gifModeCheckBox.setText("")
        self.gifModeCheckBox.setObjectName("gifModeCheckBox")
        self.horizontalLayout.addWidget(self.gifModeCheckBox)
        self.gifModeLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.gifModeLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.gifModeLabel.setFont(font)
        self.gifModeLabel.setTextFormat(QtCore.Qt.RichText)
        self.gifModeLabel.setObjectName("gifModeLabel")
        self.horizontalLayout.addWidget(self.gifModeLabel)
        self.verticalLayout_5.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.startTimeCheckBox = QtWidgets.QCheckBox(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.startTimeCheckBox.sizePolicy().hasHeightForWidth())
        self.startTimeCheckBox.setSizePolicy(sizePolicy)
        self.startTimeCheckBox.setText("")
        self.startTimeCheckBox.setObjectName("startTimeCheckBox")
        self.horizontalLayout_2.addWidget(self.startTimeCheckBox)
        self.startTimeLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.startTimeLabel.setEnabled(True)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.startTimeLabel.setFont(font)
        self.startTimeLabel.setTextFormat(QtCore.Qt.RichText)
        self.startTimeLabel.setObjectName("startTimeLabel")
        self.horizontalLayout_2.addWidget(self.startTimeLabel)
        self.timeEdit = QtWidgets.QTimeEdit(self.layoutWidget1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.timeEdit.sizePolicy().hasHeightForWidth())
        self.timeEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.timeEdit.setFont(font)
        self.timeEdit.setInputMethodHints(QtCore.Qt.ImhNone)
        self.timeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 1), QtCore.QTime(0, 0, 0)))
        self.timeEdit.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.timeEdit.setCalendarPopup(False)
        self.timeEdit.setTimeSpec(QtCore.Qt.LocalTime)
        self.timeEdit.setObjectName("timeEdit")
        self.horizontalLayout_2.addWidget(self.timeEdit)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        self.tabWidget.addTab(self.advancedTab, "")
        self.statusLabel = QtWidgets.QLabel(self.centralwidget)
        self.statusLabel.setGeometry(QtCore.QRect(430, 270, 351, 31))
        self.statusLabel.setText("")
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setObjectName("statusLabel")
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setGeometry(QtCore.QRect(10, 250, 411, 61))
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.createBtn = QtWidgets.QPushButton(self.centralwidget)
        self.createBtn.setGeometry(QtCore.QRect(10, 260, 123, 61))
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.createBtn.setFont(font)
        self.createBtn.setObjectName("createBtn")
        self.startSingleBtn = QtWidgets.QPushButton(self.centralwidget)
        self.startSingleBtn.setGeometry(QtCore.QRect(140, 260, 131, 61))
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.startSingleBtn.setFont(font)
        self.startSingleBtn.setObjectName("startSingleBtn")
        self.stopBtn = QtWidgets.QPushButton(self.centralwidget)
        self.stopBtn.setGeometry(QtCore.QRect(280, 260, 131, 61))
        font = QtGui.QFont()
        font.setFamily("Thonburi")
        self.stopBtn.setFont(font)
        self.stopBtn.setObjectName("stopBtn")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        self.listWidget.itemSelectionChanged.connect(self.setSelected)
        self.listWidget.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.durationSlider.valueChanged.connect(self.editDurationLabel)
        self.sizeSlider.valueChanged.connect(self.editSizeLabel)
        self.numWEBMSlider.valueChanged.connect(self.editNumWEBMLabel)
        self.createBtn.clicked.connect(self.createMedia)
        self.startSingleBtn.clicked.connect(self.createSelectedMedia)
        self.bitRateSlider.valueChanged.connect(self.editBitrateLabel)
        self.audioCheckBox.stateChanged.connect(self.editAudioCheckBox)
        self.gifModeCheckBox.stateChanged.connect(self.enableGifMode)
        self.targetFileSizeCheckBox.stateChanged.connect(self.editTargetFileSizeCheckBox)
        self.fileSizeSlider.valueChanged.connect(self.editTargetFileSizeSliderLabel)
        self.startTimeCheckBox.stateChanged.connect(self.singleMode)
        self.timeEdit.timeChanged.connect(self.singleMode)
        self.stopBtn.clicked.connect(self.stopProcess)
        self.durationSlider.setSliderPosition(10)
        self.sizeSlider.setSliderPosition(500)
        self.numWEBMSlider.setSliderPosition(5)
        self.bitRateSlider.setSliderPosition(1500)
        self.fileSizeSlider.setSliderPosition(4000)
        self.populateListLabel()
        self.editDurationLabel()
        self.editSizeLabel()
        self.editNumWEBMLabel()
        self.editBitrateLabel()
        self.editTargetFileSizeSliderLabel()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "WEBMARIZER"))
        self.durationLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">WEBM Duration: </span></p></body></html>"))
        self.sizeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">WEBM Width:</span></p></body></html>"))
        self.numWEBMLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Number of WEBMs:</span></p></body></html>"))
        self.videoListTitleLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Videos</span></p></body></html>"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.generalTab), _translate("MainWindow", "General Options"))
        self.bitrateLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Bitrate:</span></p></body></html>"))
        self.targetFileSizeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Target File Size (MB):</span></p></body></html>"))
        self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Target File Size</span></p></body></html>"))
        self.startTimeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Single GIF/WEBM starting at time:</span></p></body></html>"))
        self.timeEdit.setDisplayFormat(_translate("MainWindow", "hh:mm:ss"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.advancedTab), _translate("MainWindow", "Advanced Options"))
        self.createBtn.setText(_translate("MainWindow", "Create WEBM\n"
        "(All videos)"))
        self.startSingleBtn.setText(_translate("MainWindow", "Create WEBM \n"
        "(Selected videos)"))
        self.stopBtn.setText(_translate("MainWindow", "Stop Process"))
        if (platform.system() == 'Windows'): # For some reason Mac OSX and Windows font sizes differ? 
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable GIF Mode</span></p></body></html>"))
        else:
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable GIF Mode</span></p></body></html>"))
        
    # Determine the video currently selected in the video list
    def setSelected(self):
        global selectedVideo
        selectedVideo = self.listWidget.selectedItems()[0].text()
        print(selectedVideo)

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

    # If the user specifies a specific start time for GIF/WEBM
    def singleMode(self):
        global single_mode, time_array
        if (self.startTimeCheckBox.isChecked()):
            single_mode = True
            time_array[0] = self.timeEdit.time().hour()
            time_array[1] = self.timeEdit.time().minute()
            time_array[2] = self.timeEdit.time().second()
            self.numWEBMSlider.setEnabled(False)
            self.numWEBMSlider.setSliderPosition(1)
            self.numWEBMLabel.setText("Disabled (Single GIF/WEBM mode enabled)")
            print(time_array)
        else:
            single_mode = False
            self.numWEBMSlider.setEnabled(True)
            self.enableGifMode() # Return the label back to proper value

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


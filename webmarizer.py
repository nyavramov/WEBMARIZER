import subprocess
import glob
import os, sys
import platform
from PyQt5 import QtGui, QtCore, QtWidgets
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

#sudo pyinstaller -F  --add-data 'ffmpeg:.' --add-data 'ffprobe:.' webmarizer.py

# Lots of terrible global variables. Let's promise ourselves to fix this later, mkay?
stopped = False
thumbnailMode = False
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
thumbnailNumTilesSide = 2
wadsworthConstant = 30
wadsworthEnabled = True
FFmpegProcess = QtCore.QProcess()

# We'll need this to access ffmpeg & ffprobe once pyinstaller has created one-file executable
# Returns some sort of temp directory
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_path, relative_path)
    return path

# Here's where we can find ffmpeg & ffprobe. Check platform first, though.
def getDependencyPath(dependency):
    if (platform.system() == 'Windows'):
        if (dependency == 'ffmpeg'):
            path = resource_path('ffmpeg.exe')
        else:
            path = resource_path('ffprobe.exe')
    else:
        if (dependency == 'ffmpeg'):
            path = resource_path('ffmpeg')
        else:
            path = resource_path('ffprobe')
    return path


def createGif(fileName, startTime, ffmpeg_path):
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
def createWebm(fileName, startTime, ffmpeg_path):
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
    print("\n\n\n" + str(args) + "\n\n\n")
    GUI.setStatusText("Currently creating: " + fileName_webm)
    FFmpegProcess.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()
    if (stopped == False):
        FFmpegProcess.waitForFinished(-1)
        FFmpegProcess.execute(ffmpeg_path, args)
        FFmpegProcess.waitForFinished(-1)

# Searches current directory for .mp4,.wmv,.avi, .mpeg, and .mkv videos
def createVideoList():
    for fileType in ["*.mp4", "*.wmv","*.avi", "*.mpeg", "*.mkv"]:
        aVideo = glob.glob(fileType)
        if (len(aVideo) > 0):
            videosList.extend(aVideo) 
    global returnedVideoList
    returnedVideoList = True
    return (videosList)

def join_videos(video, ffmpeg_path):
    GUI.setStatusText("Stiching WEBMs. This may take a while.")
    FFmpegProcess.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()
    fileCount = 1
    previousColumnOutput = ''
    rowArray = []
    
    for row in range((thumbnailNumTilesSide)):
        firstInColumn = True
        for column in range(0,(thumbnailNumTilesSide-1)):       
            if firstInColumn:
                fileName1 = os.path.splitext(video)[0] + '_' + str(fileCount) + '.webm'
                fileCount = fileCount + 1
            else:
                fileName1 = previousColumnOutput
            fileName2 = os.path.splitext(video)[0] + '_' + str(fileCount) + '.webm'
            output    = os.path.splitext(video)[0] + '_' + str(fileCount) + '_' + str(row) + '.webm'
            previousColumnOutput = output
            
            
            args = ['-y',
            '-i' ,  fileName1,
            '-i' ,  fileName2,
            '-c:v',  'libvpx',
            '-b:v', str(bitrate)+"K",
            '-b:a', '96K',
            '-c:a', 'libvorbis']

            extendSettings1 = ['-filter_complex', '[0:v][1:v]hstack[v];[0:a][1:a]amerge=inputs=2[a]',
            '-map', '[v]',
            '-map', '[a]',
            '-ac', '2']

            extendSettings2 = ['-filter_complex', 'hstack']

            if not audioEnabled:
                args.append(audioDisable)
                for setting in extendSettings2:
                    args.append(setting)
            else:
                for setting in extendSettings1:
                    args.append(setting)
                

                
            print(fileName1)
            print(fileName2)
            print(output+"\n")
            #print("Row:    " + str(row))
            #print("Column: " + str(column))

            args.append(output)
            #print(args)
            FFmpegProcess.execute(ffmpeg_path, args)
            FFmpegProcess.waitForFinished(-1)
            fileCount = fileCount + 1
            firstInColumn = False
            if (column == (thumbnailNumTilesSide-1)-1):
                print("lol")
                rowArray.append(output)
            print(rowArray)
             
    firstPair = True
    previousRow = ''
    for index in range(len(rowArray)-1):
        print("Current index is: " + str(index))
        if firstPair:
            fileName1 = rowArray[index]
        else: 
            fileName1 = previousRow
        firstPair = False

        if (index < len(rowArray)-1):
            print(rowArray)
            print("Length: " + str(len(rowArray)))
            print("Index: " + str(index))
            fileName2 = rowArray[index+1]
        else:
            print("This should never ever happen!")


        output = os.path.splitext(video)[0] + '_row_' + str(index) + '.webm'
        if (index == (len(rowArray) - 2)):
            print("ayooo")
            output = os.path.splitext(video)[0] + '_THUMBNAIL.webm'
        previousRow = output
        
        args2 = ['-y',
        '-i' ,  fileName1,
        '-i' ,  fileName2,
        '-c:v', 'libvpx',
        '-b:v', str(bitrate)+"K",
        '-b:a', '96K',
        '-c:a', 'libvorbis']
        
        extendSettings1 = ['-filter_complex', '[0:v][1:v]vstack[v];[0:a][1:a]amerge=inputs=2[a]',
        '-map', '[v]',
        '-map', '[a]',
        '-ac', '2']

        extendSettings2 = ['-filter_complex', 'vstack']
        
        if not audioEnabled:
            args2.append(audioDisable)
            for setting in extendSettings2:
                args2.append(setting)
        else:
            for setting in extendSettings1:
                args2.append(setting)
        args2.append(output)
        print("\n\n\n\n\n"+str(args2)+"\n\n\n\n\n")
        print(fileName1)
        print(fileName2)
        print(output+'\n')
        FFmpegProcess.execute(ffmpeg_path, args2)
        FFmpegProcess.waitForFinished(-1)

# Takes video name, splits video into intervals, creates WEBM starting at each interval
def processVideo(aVideo):
    if aVideo == '':
        GUI.setStatusText("Please select a video from list when creating WEBM/GIF from single video.")
        return
    global totalSeconds, stopped, numWEBM
    ffmpeg_path = getDependencyPath('ffmpeg')
    ffprobe_path = getDependencyPath('ffprobe')
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
    
    # Makes sure WEBM length "L" isn't created at startTime + L > Length of video
    getLenLimit()

    # Let's skip first 30% of video. Add opt for this later.
    startTime = ( (totalSeconds) * wadsworthConstant) / 100
    interval  = ( int(totalSeconds) - startTime ) / numWEBM

    if thumbnailMode:
        interval  = ( int(totalSeconds) - startTime ) / (thumbnailNumTilesSide**2)
        numWEBM = 1 #Fix this later - poor control of logic flow. Same with range loop.

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
                    createWebm(aVideo, custom_start_time,ffmpeg_path)
                elif thumbnailMode:
                    print(thumbnailNumTilesSide**2)
                    global bitrate, outputWidth
                    for j in range((thumbnailNumTilesSide**2)):
                        createWebm(aVideo, startTime, ffmpeg_path)
                        startTime += interval
                        numFiles  += 1
                    join_videos(aVideo,ffmpeg_path)
                else:
                    createWebm(aVideo, startTime, ffmpeg_path)
            else:
                if single_mode:
                    custom_start_time = (time_array[0] * 3600) + (time_array[1] * 60) + time_array[2]
                    createGif(aVideo, custom_start_time,ffmpeg_path)
                else:
                    createGif(aVideo, startTime,ffmpeg_path)

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
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        #===================================================================#
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(829, 330)
        MainWindow.setDocumentMode(False)
        MainWindow.setTabShape(QtWidgets.QTabWidget.Triangular)
        MainWindow.setUnifiedTitleAndToolBarOnMac(True)
        MainWindow.setStyleSheet("""
            background-color: rgb(255, 255, 255);
            padding:0px;
        """)
        #===================================================================#
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        #===================================================================#
        sizePolicy       = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy       = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        #===================================================================#
        spacerItem       = QtWidgets.QSpacerItem(20, 25, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        spacerItem1      = QtWidgets.QSpacerItem(20, 25, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        spacerItem2      = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        #===================================================================#
        self.tabWidget   = QtWidgets.QTabWidget(self.centralwidget)
        #===================================================================#
        self.generalTab  = QtWidgets.QWidget()
        self.advancedTab = QtWidgets.QWidget()
        #===================================================================#
        self.layoutWidget   = QtWidgets.QWidget(self.generalTab)
        self.layoutWidget1  = QtWidgets.QWidget(self.advancedTab)
        self.layoutWidget_2 = QtWidgets.QWidget(self.advancedTab)
        #===================================================================#
        self.verticalLayout   = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget_2)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        #===================================================================#
        self.horizontalLayout   = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        #===================================================================#
        self.videoListTitleLabel      = QtWidgets.QLabel(self.generalTab)
        self.statusLabel              = QtWidgets.QLabel(self.centralwidget)
        self.durationLabel            = QtWidgets.QLabel(self.layoutWidget)
        self.sizeLabel                = QtWidgets.QLabel(self.layoutWidget)
        self.numWEBMLabel             = QtWidgets.QLabel(self.layoutWidget)
        self.startTimeLabel           = QtWidgets.QLabel(self.layoutWidget1)
        self.gifModeLabel             = QtWidgets.QLabel(self.layoutWidget1)
        self.enableAudioLabel         = QtWidgets.QLabel(self.layoutWidget1)
        self.thumbnailModeLabel       = QtWidgets.QLabel(self.layoutWidget1)
        self.targetSizeCheckmarkLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.targetFileSizeLabel      = QtWidgets.QLabel(self.layoutWidget_2)
        self.bitrateLabel             = QtWidgets.QLabel(self.layoutWidget_2)
        self.wadsworthLabel           = QtWidgets.QLabel(self.layoutWidget1)
        #===================================================================#
        self.numWEBMSlider  = QtWidgets.QSlider(self.layoutWidget)
        self.durationSlider = QtWidgets.QSlider(self.layoutWidget)
        self.sizeSlider     = QtWidgets.QSlider(self.layoutWidget)
        self.fileSizeSlider = QtWidgets.QSlider(self.layoutWidget_2)
        self.bitRateSlider  = QtWidgets.QSlider(self.layoutWidget_2)
        #===================================================================#
        self.stopBtn        = QtWidgets.QPushButton(self.centralwidget)
        self.startSingleBtn = QtWidgets.QPushButton(self.centralwidget)
        self.createBtn      = QtWidgets.QPushButton(self.centralwidget)
        #===================================================================#
        self.timeEdit = QtWidgets.QTimeEdit(self.layoutWidget1)
        #===================================================================#
        self.listWidget = QtWidgets.QListWidget(self.generalTab)
        #===================================================================#
        self.thumbnailModeCheckBox  = QtWidgets.QCheckBox(self.layoutWidget1)
        self.startTimeCheckBox      = QtWidgets.QCheckBox(self.layoutWidget1)
        self.gifModeCheckBox        = QtWidgets.QCheckBox(self.layoutWidget1)
        self.audioCheckBox          = QtWidgets.QCheckBox(self.layoutWidget1)
        self.targetFileSizeCheckBox = QtWidgets.QCheckBox(self.layoutWidget1)
        self.wadsworthCheckBox      = QtWidgets.QCheckBox(self.layoutWidget1)
        #===================================================================#
        self.thumbnailDropdown = QtWidgets.QComboBox(self.layoutWidget1)
        #===================================================================#
        font = QtGui.QFont()
        #===================================================================#
        self.stopBtn.setObjectName("stopBtn")
        self.statusLabel.setObjectName("statusLabel")
        self.thumbnailModeLabel.setObjectName("thumbnailModeLabel")
        self.thumbnailModeCheckBox.setObjectName("thumbnailModeCheckBox")
        self.startTimeCheckBox.setObjectName("startTimeCheckBox")
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout.setObjectName("verticalLayout")
        self.layoutWidget.setObjectName("layoutWidget")
        self.tabWidget.setObjectName("tabWidget")
        self.generalTab.setObjectName("generalTab")
        self.durationLabel.setObjectName("durationLabel")
        self.durationSlider.setObjectName("durationSlider")
        self.sizeLabel.setObjectName("sizeLabel")
        self.sizeSlider.setObjectName("sizeSlider")
        self.numWEBMLabel.setObjectName("numWEBMLabel")
        self.numWEBMSlider.setObjectName("numWEBMSlider")
        self.videoListTitleLabel.setObjectName("videoListTitleLabel")
        self.advancedTab.setObjectName("advancedTab")
        self.layoutWidget_2.setObjectName("layoutWidget_2")
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.bitrateLabel.setObjectName("bitrateLabel")
        self.bitRateSlider.setObjectName("bitRateSlider")
        self.targetFileSizeLabel.setObjectName("targetFileSizeLabel")
        self.fileSizeSlider.setObjectName("fileSizeSlider")
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.targetFileSizeCheckBox.setObjectName("targetFileSizeCheckBox")
        self.targetSizeCheckmarkLabel.setObjectName("targetSizeCheckmarkLabel")
        self.audioCheckBox.setObjectName("audioCheckBox")
        self.enableAudioLabel.setObjectName("enableAudioLabel")
        self.gifModeCheckBox.setObjectName("gifModeCheckBox")
        self.gifModeLabel.setObjectName("gifModeLabel")
        self.startTimeLabel.setObjectName("startTimeLabel")
        self.timeEdit.setObjectName("timeEdit")
        self.wadsworthCheckBox.setObjectName("wadsworthCheckBox")
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.createBtn.setObjectName("createBtn")
        self.startSingleBtn.setObjectName("startSingleBtn")
        #===================================================================#
        tabStyleString = """
            QTabBar::tab {
                width: 300px;
            }

            QTabWidget::tab-bar {
                top:30;
                padding-left:0;
                background:transparent;
                width:835px;
            }
        
            QTabWidget::pane {
                border: 0 solid white;
            }
        """
        sliderStyleString = """
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9595ff, stop:1 #1e95ff);
            border: 1px solid #5c5c5c;
            width: 18px;
            margin: -2px 0;
            border-radius: 3px;
        }

        QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 9px; 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
            margin: 2px 0;
        }
        """
        #===================================================================#
        font.setFamily("Thonburi")
        font.setBold(False)
        font.setWeight(50)
        #===================================================================#
        self.tabWidget.setFont(font)
        self.tabWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tabWidget.setAutoFillBackground(False)
        self.tabWidget.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setGeometry(QtCore.QRect(0, -30, 831, 341))
        self.tabWidget.addTab(self.generalTab, "")
        self.tabWidget.addTab(self.advancedTab, "")
        self.tabWidget.setStyleSheet(tabStyleString)
        #===================================================================#
        self.generalTab.setAutoFillBackground(False)
        self.generalTab.setStyleSheet("""
            QTabBar {
                qproperty-drawBase: 0;
            }
        """)
        #===================================================================#
        self.layoutWidget.setGeometry(QtCore.QRect(20, 40, 381, 211))
        #===================================================================#
        sizePolicy.setHeightForWidth(self.wadsworthCheckBox.sizePolicy().hasHeightForWidth())
        self.wadsworthCheckBox.setSizePolicy(sizePolicy)
        self.wadsworthCheckBox.setText("")
        #===================================================================#
        self.wadsworthLabel.setEnabled(True)
        self.wadsworthLabel.setFont(font)
        self.wadsworthLabel.setTextFormat(QtCore.Qt.RichText)
        self.wadsworthLabel.setObjectName("wadsworthLabel")
        #===================================================================#
        self.durationLabel.setEnabled(True)
        self.durationLabel.setFont(font)
        self.durationLabel.setStyleSheet("")
        self.durationLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.durationSlider.setMinimum(1)
        self.durationSlider.setMaximum(30)
        self.durationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.durationSlider.setStyleSheet(sliderStyleString)
        #===================================================================#
        self.sizeLabel.setEnabled(True)
        self.sizeLabel.setFont(font)
        self.sizeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.sizeSlider.setMinimum(300)
        self.sizeSlider.setMaximum(3000)
        self.sizeSlider.setOrientation(QtCore.Qt.Horizontal)
        self.sizeSlider.setStyleSheet(sliderStyleString)
        #===================================================================#
        self.numWEBMLabel.setEnabled(True)
        self.numWEBMLabel.setFont(font)
        self.numWEBMLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.numWEBMSlider.setMinimum(1)
        self.numWEBMSlider.setMaximum(50)
        self.numWEBMSlider.setOrientation(QtCore.Qt.Horizontal)
        self.numWEBMSlider.setStyleSheet(sliderStyleString)        
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.listWidget.setGeometry(QtCore.QRect(430, 70, 381, 171))
        self.listWidget.setSizePolicy(sizePolicy)
        self.listWidget.setFont(font)
        self.listWidget.setWordWrap(True)
        self.listWidget.setObjectName("listWidget")
        self.listWidget.setStyleSheet("""
            background-color:#fff;
            border:1px solid black;
        """)
        #===================================================================#
        self.videoListTitleLabel.setGeometry(QtCore.QRect(580, 40, 81, 21))
        self.videoListTitleLabel.setFont(font)
        #===================================================================#
        self.layoutWidget_2.setGeometry(QtCore.QRect(420, 40, 371, 102))
        #===================================================================#
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addWidget(self.durationLabel)
        self.verticalLayout.addWidget(self.durationSlider)
        self.verticalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.numWEBMLabel)
        self.verticalLayout.addWidget(self.numWEBMSlider)
        self.verticalLayout.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.sizeLabel)
        self.verticalLayout.addWidget(self.sizeSlider)
        #===================================================================#
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.addLayout(self.verticalLayout_4)
        #===================================================================#
        self.verticalLayout_3.addLayout(self.horizontalLayout_7)
        self.verticalLayout_3.addLayout(self.horizontalLayout_8)
        #===================================================================#
        self.verticalLayout_4.addLayout(self.verticalLayout_6)
        self.verticalLayout_4.addWidget(self.targetFileSizeLabel)
        self.verticalLayout_4.addWidget(self.fileSizeSlider)
        #===================================================================#
        self.verticalLayout_5.addLayout(self.verticalLayout_3)
        self.verticalLayout_5.addLayout(self.horizontalLayout)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        self.verticalLayout_5.addLayout(self.horizontalLayout_4)
        self.verticalLayout_5.addLayout(self.horizontalLayout_3)
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        #===================================================================#
        self.verticalLayout_6.addWidget(self.bitRateSlider)
        self.verticalLayout_6.addWidget(self.bitrateLabel)
        #===================================================================#
        self.horizontalLayout.addWidget(self.gifModeCheckBox)
        self.horizontalLayout.addWidget(self.gifModeLabel)
        #===================================================================#
        self.horizontalLayout_2.addWidget(self.startTimeCheckBox)
        self.horizontalLayout_2.addWidget(self.startTimeLabel)
        self.horizontalLayout_2.addWidget(self.timeEdit)
        self.horizontalLayout_2.addItem(spacerItem2)
        #===================================================================#
        self.horizontalLayout_3.addWidget(self.thumbnailModeCheckBox)
        self.horizontalLayout_3.addWidget(self.thumbnailModeLabel)
        self.horizontalLayout_3.addWidget(self.thumbnailDropdown)
        #===================================================================#
        self.horizontalLayout_4.addWidget(self.wadsworthCheckBox)
        self.horizontalLayout_4.addWidget(self.wadsworthLabel)
        #===================================================================#
        self.thumbnailDropdown.setIconSize(QtCore.QSize(16, 16))
        self.thumbnailDropdown.setObjectName("thumbnailDropdown")
        self.thumbnailDropdown.addItem("")
        self.thumbnailDropdown.addItem("")
        self.thumbnailDropdown.addItem("")
        self.thumbnailDropdown.addItem("")
        self.thumbnailDropdown.addItem("")
        self.thumbnailDropdown.setStyleSheet('''
            QComboBox {
                border-style: solid;
                selection-color:black;
                background-color:#f9f9f9;
                border:1px solid black;
                border-radius: 5;
                padding: 1px 0px 1px 10px;
            }

            QComboBox::down-arrow {
                width: 14px;
                color:white;
            }
        ''')
        #===================================================================#
        self.horizontalLayout_7.addWidget(self.targetFileSizeCheckBox)
        self.horizontalLayout_7.addWidget(self.targetSizeCheckmarkLabel)
        #===================================================================#
        self.horizontalLayout_8.addWidget(self.audioCheckBox)
        self.horizontalLayout_8.addWidget(self.enableAudioLabel)
        #===================================================================#
        self.bitrateLabel.setEnabled(True)
        self.bitrateLabel.setFont(font)
        self.bitrateLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.bitRateSlider.setStyleSheet(sliderStyleString)
        self.bitRateSlider.setMinimum(1000)
        self.bitRateSlider.setMaximum(15000)
        self.bitRateSlider.setOrientation(QtCore.Qt.Horizontal)
        #===================================================================#
        self.targetFileSizeLabel.setEnabled(True)
        self.targetFileSizeLabel.setFont(font)
        self.targetFileSizeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.fileSizeSlider.setStyleSheet(sliderStyleString)
        self.fileSizeSlider.setMinimum(100)
        self.fileSizeSlider.setMaximum(15000)
        self.fileSizeSlider.setOrientation(QtCore.Qt.Horizontal)
        #===================================================================#
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 40, 401, 221))
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.targetFileSizeCheckBox.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.targetFileSizeCheckBox.setSizePolicy(sizePolicy)
        self.targetFileSizeCheckBox.setText("")
        #===================================================================#
        self.targetSizeCheckmarkLabel.setEnabled(True)
        self.targetSizeCheckmarkLabel.setFont(font)
        self.targetSizeCheckmarkLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.audioCheckBox.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.audioCheckBox.setSizePolicy(sizePolicy)
        self.audioCheckBox.setText("")
        #===================================================================#
        self.enableAudioLabel.setEnabled(True)
        self.enableAudioLabel.setFont(font)
        self.enableAudioLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gifModeCheckBox.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.gifModeCheckBox.setSizePolicy(sizePolicy)
        self.gifModeCheckBox.setText("")
        #===================================================================#
        self.gifModeLabel.setEnabled(True)
        self.gifModeLabel.setFont(font)
        self.gifModeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.startTimeCheckBox.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.startTimeCheckBox.setSizePolicy(sizePolicy)
        self.startTimeCheckBox.setText("")
        #===================================================================#
        self.startTimeLabel.setEnabled(True)
        self.startTimeLabel.setFont(font)
        self.startTimeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.timeEdit.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.timeEdit.setSizePolicy(sizePolicy)
        self.timeEdit.setFont(font)
        self.timeEdit.setInputMethodHints(QtCore.Qt.ImhNone)
        self.timeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 1), QtCore.QTime(0, 0, 0)))
        self.timeEdit.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.timeEdit.setCalendarPopup(False)
        self.timeEdit.setTimeSpec(QtCore.Qt.LocalTime)
        #===================================================================#
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.thumbnailModeCheckBox.sizePolicy().hasHeightForWidth())
        #===================================================================#
        self.thumbnailModeCheckBox.setSizePolicy(sizePolicy)
        self.thumbnailModeCheckBox.setText("")
        #===================================================================#
        self.thumbnailModeLabel.setEnabled(True)
        self.thumbnailModeLabel.setFont(font)
        self.thumbnailModeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.statusLabel.setGeometry(QtCore.QRect(430, 270, 351, 31))
        self.statusLabel.setText("")
        self.statusLabel.setWordWrap(True)
        #===================================================================#
        self.createBtn.setGeometry(QtCore.QRect(10, 260, 123, 61))
        self.createBtn.setFont(font)
        #===================================================================#
        self.startSingleBtn.setGeometry(QtCore.QRect(140, 260, 131, 61))
        self.startSingleBtn.setFont(font)
        #===================================================================#
        self.stopBtn.setGeometry(QtCore.QRect(280, 260, 131, 61))
        self.stopBtn.setFont(font)
        #===================================================================#
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
        self.thumbnailModeCheckBox.stateChanged.connect(self.thumbnailMode)
        self.wadsworthCheckBox.stateChanged.connect(self.enableWadsworth)
        self.timeEdit.timeChanged.connect(self.singleMode)
        self.stopBtn.clicked.connect(self.stopProcess)
        self.thumbnailDropdown.currentIndexChanged.connect(self.editThumbnailMode)
        
        self.durationSlider.setSliderPosition(10)
        self.sizeSlider.setSliderPosition(500)
        self.numWEBMSlider.setSliderPosition(5)
        self.bitRateSlider.setSliderPosition(1500)
        self.fileSizeSlider.setSliderPosition(4000)
        self.wadsworthCheckBox.setChecked(True)
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
        
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.generalTab), _translate("MainWindow", "General Options"))
        self.bitrateLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Bitrate:</span></p></body></html>"))
        self.targetFileSizeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Target File Size (MB):</span></p></body></html>"))
        self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Target File Size</span></p></body></html>"))
       
        self.timeEdit.setDisplayFormat(_translate("MainWindow", "hh:mm:ss"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.advancedTab), _translate("MainWindow", "Advanced Options"))
        self.createBtn.setText(_translate("MainWindow", "Create WEBM\n"
        "(All videos)"))
        self.startSingleBtn.setText(_translate("MainWindow", "Create WEBM \n"
        "(Selected videos)"))
        self.stopBtn.setText(_translate("MainWindow", "Stop Process"))
        self.thumbnailDropdown.setItemText(0, _translate("MainWindow", "2x2"))
        self.thumbnailDropdown.setItemText(1, _translate("MainWindow", "3x3"))
        self.thumbnailDropdown.setItemText(2, _translate("MainWindow", "4x4"))
        self.thumbnailDropdown.setItemText(3, _translate("MainWindow", "5x5"))
        self.thumbnailDropdown.setItemText(4, _translate("MainWindow", "6x6"))
        if (platform.system() == 'Windows'): # For some reason Mac OSX and Windows font sizes differ? 
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable GIF Mode</span></p></body></html>"))
            self.thumbnailModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable THumbnail Mode</span></p></body></html>"))
            self.wadsworthLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Enable Wadsworth Constant (Skip first ~30%)</span></p></body></html>"))
            self.videoListTitleLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Videos</span></p></body></html>"))
            self.startTimeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:8pt;\">Single GIF/WEBM starting at time:</span></p></body></html>"))
        else:
            self.enableAudioLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Audio</span></p></body></html>"))
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Target File Size</span></p></body></html>"))
            self.gifModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable GIF Mode</span></p></body></html>"))
            self.thumbnailModeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Thumbnail Mode</span></p></body></html>"))
            self.wadsworthLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Enable Wadsworth Constant (Skip first ~30%)</span></p></body></html>"))
            self.videoListTitleLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Videos</span></p></body></html>"))
            self.startTimeLabel.setText(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:16pt;\">Single GIF/WEBM starting at time:</span></p></body></html>"))
        
    # Determine the video currently selected in the video list
    def setSelected(self):
        global selectedVideo
        selectedVideo = self.listWidget.selectedItems()[0].text()
        

    # Attempts to kill WEBM creation process
    def stopProcess(self):
        global FFmpegProcess, stopped
        FFmpegProcess.kill()
        stopped = True

    def editThumbnailMode(self):
        global thumbnailNumTilesSide
        if (self.thumbnailDropdown.currentText() == '2x2'):
            thumbnailNumTilesSide = 2
        elif (self.thumbnailDropdown.currentText() == '3x3'):
            thumbnailNumTilesSide = 3
        elif (self.thumbnailDropdown.currentText() == '4x4'):
            thumbnailNumTilesSide = 4
        elif (self.thumbnailDropdown.currentText() == '5x5'):
            thumbnailNumTilesSide = 5
        elif (self.thumbnailDropdown.currentText() == '6x6'):
            thumbnailNumTilesSide = 6

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

    def enableWadsworth(self):
        global wadsworthConstant
        if (self.wadsworthCheckBox.isChecked()):
            wadsworthConstant = 30
            print("Wadsworth constant is enabled. Skipping first 30% of video.")
        else:
            wadsworthConstant = 0
            print("Wadsworth constant is disabled. Starting from beginning of video.")


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
            print("Selected Time: " + str(time_array))
        else:
            single_mode = False
            self.numWEBMSlider.setEnabled(True)
            self.enableGifMode() # Return the label back to proper value

    def thumbnailMode(self):
        global thumbnailMode
        if (self.thumbnailModeCheckBox.isChecked()):
            thumbnailMode = True
        else:
            thumbnailMode = False

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
        if (len(videos_array) > 0):
            for video in videos_array:
                item = QtWidgets.QListWidgetItem()
                item.setText(video)
                self.listWidget.addItem(item)
        else:
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


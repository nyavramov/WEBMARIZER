import subprocess
import glob
import os, sys
import platform
from PyQt5 import QtGui, QtCore, QtWidgets

# Command for creating pyinstaller executable:
# sudo pyinstaller -F --add-data 'ffmpeg:.' --add-data 'ffprobe:.' webmarizer.py

# CD to the current directory of the script/executable 
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

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

# Create a GIF by first creating a palette, then making GIF from that palette
# To-do: add option to control framerate
def createGif(params):
    fileNameNoExtension = os.path.splitext(params['fileName'])[0]
    fileName_gif = fileNameNoExtension + '_' + str(params['numFiles']) + '.gif'

    # Set the size of the GIF and filters
    scaleString = 'scale=' + str(params['outputWidth']) + ':-2'
    filters='fps=20,scale=' + str(params['outputWidth']) + ':-1:flags=lanczos'
    
    # 1st Generate a pallete with ffmpeg
    paletteArgs = [
        '-ss',  str(params['startTime']),
        '-t',   str(params['outputDuration']),
        '-i' ,  params['fileName'],
        '-vf',  filters+",palettegen",
        '-y',   'palette.png'
    ]

    # 2nd Generate the gif using the palette
    gifArgs = [
        '-ss', str(params['startTime']),
        '-t' , str(params['outputDuration']),
        '-i' , params['fileName'],
        '-i' , 'palette.png'
    ]

    # Options if the user has requested specific GIF size
    gifOptsWithFileSize = [
        '-fs', str(params['fileSize']/1000) + "M",
        '-lavfi', filters+"[x];[x][1:v]paletteuse",
        '-y', fileName_gif
    ]

    # Options if the user has not requested specific GIF size
    gifOptsWithoutFileSize = [
        '-lavfi', filters+"[x];[x][1:v]paletteuse",
        '-y', fileName_gif
    ]

    # Append either of above options to args array, depending on whether 
    # file size is set
    if GUI.getFileSizeCheckboxState():
        gifArgs.extend(gifOptsWithFileSize)
    else:
        gifArgs.extend(gifOptsWithoutFileSize)

    GUI.setStatusText("Currently creating: " + fileName_gif)

    # Set channel so we can see FFmpeg output
    params['FFmpegProcess'].setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()

    # Currently, no way of stopping FFmpeg from GUI since GUI is frozen
    # See multithreading for potential solution
    if (params['stopped'] == False):
        params['FFmpegProcess'].execute(params['ffmpeg_path'], paletteArgs)
        params['FFmpegProcess'].waitForFinished(-1)
        params['FFmpegProcess'].execute(params['ffmpeg_path'], gifArgs)
        params['FFmpegProcess'].waitForFinished(-1)
        os.remove("palette.png")

# Use ffmpeg to create WEBM and read its stdout. To-Do:Use some regex later for progress bar
def createWebm(params):
    fileNameNoExtension = os.path.splitext(params['fileName'])[0]
    fileName_webm = fileNameNoExtension + '_' + str(params['numFiles']) + '.webm'

    scaleString = 'scale=' + str(params['outputWidth']) + ':-2'
    
    # General arguments to pass to FFmpeg
    args = [
        '-y'  ,
        '-ss' , str(params['startTime']),
        '-t'  , str(params['outputDuration']),
        '-i'  , params['fileName'],
        '-vf' , scaleString,
        '-c:v', 'libvpx',
        '-b:v', str(params['bitrate'])+"K",
        '-b:a', '96K',
        '-c:a', 'libvorbis'
    ]

    # If audio is not enabled, set FFmpeg's -an flag
    if not params['audioEnabled']:
        args.append('-an')
    
    # Set FFmpeg's output name
    args.append(fileName_webm)

    GUI.setStatusText("Currently creating: " + fileName_webm)

    params['FFmpegProcess'].setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()

    if (params['stopped'] == False):
        params['FFmpegProcess'].execute(params['ffmpeg_path'], args)
        params['FFmpegProcess'].waitForFinished(-1)
        params['FFmpegProcess'].kill() # When we're done, kill process

# Searches current directory for .mp4,.wmv,.avi, .mpeg, and .mkv videos
def createVideoList():
    videosList = []
    for fileType in ["*.mp4", "*.wmv","*.avi", "*.mpeg", "*.mkv"]:
        aVideo = glob.glob(fileType)
        if (len(aVideo) > 0):
            videosList.extend(aVideo) 
    return (videosList)

''' 
Join Videos Algorithm: 

Let [] represent a video clip. Example: For a 3x3 thumbnail, our matrix will have 9 of these clips. 
To create this matrix, we start by creating 3 individual rows with 3 clips per row.

# Creating a row looks like this:
    [] + [] = [][] --> [][] + [] = [][][]. 
    We do this 3 times to create 3 rows.

Then we concatenate 3 rows in a similar way: Start by taking 2 rows and concatenating them.
  [][][]  (Row 1)
+ [][][]  (Row 2)

Then, we add the third row to the 2 already concatenated rows:
  [][][] (Row 1)
  [][][] (Row 2)
+ [][][] (Row 3)
    
'''
# Handles joining videos together for thumbnail mode option
def join_videos(params):
    # Set GUI message while we stich WEBMs together & set channel so we can see FFmpeg output in terminal
    GUI.setStatusText("Stitching WEBMs. This may take a while.")
    params['FFmpegProcess'].setProcessChannelMode(QtCore.QProcess.MergedChannels)
    app.processEvents()

    # Use this to keep track of which video we are currently appending
    fileCount = 1

    # For each video in the row, we'll make one video row that gets progressively wider
    previousColumnOutput = ''

    # At the end of each column, we're going to add the finished row to the rowArray
    rowArray = []
    
    # Create rows first
    for row in range((params['thumbnailNumTilesSide'])):
        firstInColumn = True 
        for column in range(0,(params['thumbnailNumTilesSide']-1)): 
            # Special case: If we are in first column, concat 2 individual clips together      
            if firstInColumn:
                fileName1 = os.path.splitext(params['fileName'])[0] + '_' + str(fileCount) + '.webm'
                fileCount = fileCount + 1
            # If not in first column, use previously concatenated clips in the row and add new clip
            else:
                fileName1 = previousColumnOutput

            fileName2 = os.path.splitext(params['fileName'])[0] + '_' + str(fileCount) + '.webm'
            output    = os.path.splitext(params['fileName'])[0] + '_' + str(fileCount) + '_' + str(row) + '.webm'
            
            # Save previous column output so that we can use it as fileName1 in next iteration
            previousColumnOutput = output

            # General FFmpeg settings
            args = [
                '-y'  ,
                '-i'  ,  fileName1,
                '-i'  ,  fileName2,
                '-c:v', 'libvpx',
                '-b:v', str(params['bitrate'])+"K",
                '-b:a', '96K',
                '-c:a', 'libvorbis'
            ]

            # Settings when audio enabled
            extendSettings1 = [
                '-filter_complex', '[0:v][1:v]hstack[v];[0:a][1:a]amerge=inputs=2[a]',
                '-map', '[v]',
                '-map', '[a]',
                '-ac', '2'
            ]

            # Setting when audio disabled
            extendSettings2 = [
                '-filter_complex', 'hstack'
            ]

            # Append correct settings depending on whether audio is enabled
            if not params['audioEnabled']:
                args.append('-an')
                for setting in extendSettings2:
                    args.append(setting)
            else:
                for setting in extendSettings1:
                    args.append(setting)
            
            # Add what we'd like output to be called to FFmpeg args array
            args.append(output)

            # Execute the concatenation process
            params['FFmpegProcess'].execute(params['ffmpeg_path'], args)
            params['FFmpegProcess'].waitForFinished(-1)
            
            # Increment fileCount so we know which WEBM to use as input
            fileCount = fileCount + 1
            firstInColumn = False

            # If we've reached end of the row, add that completed row to the row array so
            # we can concatenate rows later
            if (column == (params['thumbnailNumTilesSide']-1)-1):
                rowArray.append(output)
            print(rowArray)
          
    firstPair = True # Serves same purpose as firstInColumn above (handling special case)
    previousRow = ''

    # Concatenate all the rows together
    for row in range(len(rowArray)-1):
        if firstPair:
            fileName1 = rowArray[row]
        else: 
            fileName1 = previousRow

        firstPair = False

        # If we haven't reached last row, let 2nd input file be next row
        if (row < len(rowArray) - 1):
            fileName2 = rowArray[row+1]

        output = os.path.splitext(params['fileName'])[0] + '_row_' + str(row) + '.webm'
        
        # If we've reached the last 2 rows, set output to be videoName_thumbnail.webm
        if (row == (len(rowArray) - 2)):
            output = os.path.splitext(params['fileName'])[0] + '_THUMBNAIL.webm'
        previousRow = output
        
        # General FFmpeg settings 
        args2 = [
            '-y'  ,
            '-i'  ,  fileName1,
            '-i'  ,  fileName2,
            '-c:v', 'libvpx',
            '-b:v', str(params['bitrate'])+"K",
            '-b:a', '96K',
            '-c:a', 'libvorbis'
        ]
        
        # Settings when audio is enabled
        extendSettings1 = [
            '-filter_complex', '[0:v][1:v]vstack[v];[0:a][1:a]amerge=inputs=2[a]',
            '-map', '[v]',
            '-map', '[a]',
            '-ac', '2'
        ]

        # Settings when audio is disabled
        extendSettings2 = [
            '-filter_complex', 'vstack'
        ]
        
        # Append appropriate settings depending on audio 
        if not params['audioEnabled']:
            args2.append('-an')
            for setting in extendSettings2:
                args2.append(setting)
        else:
            for setting in extendSettings1:
                args2.append(setting)

        # Add what we'd like output to be called to FFmpeg args array
        args2.append(output)

        # Execute the vertical stacking of rows
        params['FFmpegProcess'].execute(params['ffmpeg_path'], args2)
        params['FFmpegProcess'].waitForFinished(-1)
    
# Create a parameter dictionary to hold media information
# Useful so we don't have to pass a bunch of vars between functions
def composeMediaParamDictionary(aVideo):
    # Initialize dictionary
    params = {}

    # Get the path to ffmpeg & probe executables
    ffmpeg_path = getDependencyPath('ffmpeg')
    ffprobe_path = getDependencyPath('ffprobe')

    # Compose param array for FFprobe to use
    FFprobeArgs = [
        ffprobe_path      ,
        '-v'              , 'quiet',
        '-show_entries'   , 'format=duration',
        '-of'             , 'csv=%s' % ("p=0"),
        '-i'              ,  aVideo
    ]

    # Spawn process
    FFmpegProcess = QtCore.QProcess()

    # Pass process to Qt
    GUI.setProcess(FFmpegProcess)

    # Check how many WEBMs/GIFs user wants
    numOutputs = GUI.getNumOutputs()

    # Keep track of current WEBM number for naming purposes. Init to 0
    numFiles = 0

    # Get width of WEBM/GIF
    outputWidth = GUI.getWidth()

    # Check what duration user wants for WEBM/GIF
    outputDuration = GUI.getOutputDuration()

    # We can use FFprobe to check the number of seconds in the video
    totalSeconds = subprocess.check_output(FFprobeArgs)

    # Y u do dis? Have to look into why decoding this is necessary.
    totalSeconds = float(totalSeconds.decode("utf-8"))

    # Get the bitrate
    bitrate = GUI.getBitrate()

    # Get the target file size if targetFileSize is enabled
    # Only used for GIFs, since bitrate will determine file size for WEBMs
    if GUI.getFileSizeCheckboxState():
        fileSize = GUI.getFileSize()
    else:
        fileSize = -1

    # Check whether audio is enabled 
    audioEnabled = GUI.getAudioEnabledState()
    
    # Makes sure WEBM length "L" isn't created at startTime + L > Length of video
    lenLimit = getLenLimit(totalSeconds, outputDuration)

    # Check value of wadsworth constant
    wadsworthConstant = GUI.getWadsworth()

    # Check if single mode is on or off
    single_mode = GUI.getSingleModeState()

    # Set the time where WEBM/GIF starts
    if single_mode:
        startTime = GUI.getCustomStartTime()
    else:
        startTime = ( (totalSeconds) * wadsworthConstant) / 100

    # Calculate time interval between WEBMs/GIFs
    interval  = ( int(totalSeconds) - startTime ) / numOutputs

    # Check what kind of output user wants
    output_type = GUI.getOutputType()

    # Check if thumbnail mode is on or off
    thumbnailMode = GUI.getThumbnailModeState()

    # In case thumbnail mode is enabled, get number of tiles per side of thumbnail
    thumbnailNumTilesSide = GUI.getNumVideoTilesSide()

    # Recalculate custom interval and output number if thumbnailMode is enabled
    if thumbnailMode:
        interval  = ( int(totalSeconds) - startTime ) / (thumbnailNumTilesSide**2)
        numOutputs = GUI.getNumVideoTilesSide() ** 2

    # If we're only creating single WEBM/GIF, set output num to 1
    if single_mode:
        numOutputs = 1

    # Use this to check if user has stopped the program
    stopped = GUI.getProcessStoppedStatus()

    # Set all key:value pairs for param dictionary
    params = {
        'fileName'              : aVideo, 
        'ffmpeg_path'           : ffmpeg_path,
        'ffprobe_path'          : ffprobe_path,
        'FFmpegProcess'         : FFmpegProcess,
        'numOutputs'            : numOutputs,
        'numFiles'              : numFiles,
        'outputWidth'           : outputWidth,
        'fileSize'              : fileSize,
        'outputDuration'        : outputDuration,
        'totalSeconds'          : totalSeconds,
        'lenLimit'              : lenLimit,
        'wadsworthConstant'     : wadsworthConstant,
        'single_mode'           : single_mode,
        'startTime'             : startTime,
        'interval'              : interval,
        'output_type'           : output_type,
        'thumbnailMode'         : thumbnailMode,
        'bitrate'               : bitrate,
        'audioEnabled'          : audioEnabled,
        'stopped'               : stopped,
        'thumbnailNumTilesSide' : thumbnailNumTilesSide
    }

    return params

# Takes video name, splits video into intervals, creates WEBM or GIF starting at each interval
def processVideo(aVideo):
    # Check to make sure user has selected a video
    if aVideo == '':
        GUI.setStatusText("Please select a video from list when creating WEBM/GIF from single video.")
        return

    params = composeMediaParamDictionary(aVideo)

    # Check if user has stopped the program
    if params['stopped']:
        app.processEvents() 
        GUI.setStatusText("Process killed.")
        return
    
    # Iteratively create the number of GIFs/WEBMs that user requested
    for output in range(params['numOutputs']):
        app.processEvents() 
        params['numFiles'] += 1

        # If we're trying to create output past the end of video, break
        if params['startTime'] >= params['lenLimit']:
            break

        if params['output_type'] == 'WEBM':
            createWebm(params)
        elif params['output_type'] == 'GIF':
            createGif(params)

        params['startTime'] += params['interval']
    
    if params['thumbnailMode']:
        join_videos(params)

# Makes sure WEBM length "L" isn't created at startTime + L > Length of video
def getLenLimit(totalSeconds, outputDuration):
    lenLimit = totalSeconds - outputDuration - 1
    return lenLimit

# Starts going through all the videos in our list and initiates WEBM/GIF creation process
def init(videosList):
    for video in videosList:
        # If video making not cancelled, process vid
        if not GUI.getProcessStoppedStatus():
            processVideo(video)
        else:
            app.processEvents() 
            GUI.setStatusText("Process killed.")
    if not GUI.getProcessStoppedStatus():
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
        self.widthLabel               = QtWidgets.QLabel(self.layoutWidget)
        self.numOutputsLabel          = QtWidgets.QLabel(self.layoutWidget)
        self.startTimeLabel           = QtWidgets.QLabel(self.layoutWidget1)
        self.gifModeLabel             = QtWidgets.QLabel(self.layoutWidget1)
        self.enableAudioLabel         = QtWidgets.QLabel(self.layoutWidget1)
        self.thumbnailModeLabel       = QtWidgets.QLabel(self.layoutWidget1)
        self.targetSizeCheckmarkLabel = QtWidgets.QLabel(self.layoutWidget1)
        self.bitrateLabel             = QtWidgets.QLabel(self.layoutWidget_2)
        self.targetFileSizeLabel      = QtWidgets.QLabel(self.layoutWidget_2)
        self.wadsworthLabel           = QtWidgets.QLabel(self.layoutWidget1)
        #===================================================================#
        self.numOutputsSlider = QtWidgets.QSlider(self.layoutWidget)
        self.durationSlider   = QtWidgets.QSlider(self.layoutWidget)
        self.widthSlider      = QtWidgets.QSlider(self.layoutWidget)
        self.fileSizeSlider   = QtWidgets.QSlider(self.layoutWidget_2)
        self.bitRateSlider    = QtWidgets.QSlider(self.layoutWidget_2)
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
        self.widthLabel.setObjectName("sizeLabel")
        self.widthSlider.setObjectName("sizeSlider")
        self.numOutputsLabel.setObjectName("numOutputsLabel")
        self.numOutputsSlider.setObjectName("numOutputsSlider")
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
        self.widthLabel.setEnabled(True)
        self.widthLabel.setFont(font)
        self.widthLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.widthSlider.setMinimum(300)
        self.widthSlider.setMaximum(3000)
        self.widthSlider.setOrientation(QtCore.Qt.Horizontal)
        self.widthSlider.setStyleSheet(sliderStyleString)
        #===================================================================#
        self.numOutputsLabel.setEnabled(True)
        self.numOutputsLabel.setFont(font)
        self.numOutputsLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.numOutputsSlider.setMinimum(1)
        self.numOutputsSlider.setMaximum(50)
        self.numOutputsSlider.setOrientation(QtCore.Qt.Horizontal)
        self.numOutputsSlider.setStyleSheet(sliderStyleString)        
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
        self.verticalLayout.addWidget(self.numOutputsLabel)
        self.verticalLayout.addWidget(self.numOutputsSlider)
        self.verticalLayout.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.widthLabel)
        self.verticalLayout.addWidget(self.widthSlider)
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
        self.verticalLayout_6.addWidget(self.bitrateLabel)
        self.verticalLayout_6.addWidget(self.bitRateSlider)
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
        self.bitRateSlider.setMinimum(20)
        self.bitRateSlider.setMaximum(15000)
        self.bitRateSlider.setOrientation(QtCore.Qt.Horizontal)
        #===================================================================#
        self.targetFileSizeLabel.setEnabled(True)
        self.targetFileSizeLabel.setFont(font)
        self.targetFileSizeLabel.setTextFormat(QtCore.Qt.RichText)
        #===================================================================#
        self.fileSizeSlider.setStyleSheet(sliderStyleString)
        self.fileSizeSlider.setMinimum(50)
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

        # Connect functions to GUI inputs
        self.listWidget.itemSelectionChanged.connect(self.setSelected)
        self.listWidget.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.durationSlider.valueChanged.connect(self.editDurationLabel)
        self.widthSlider.valueChanged.connect(self.editWidthLabel)
        self.numOutputsSlider.valueChanged.connect(self.editnumOutputsLabel)
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
        
        # Set a few default values
        self.videos_array          = createVideoList() # Gets videos in current folder
        self.stopped               = False             # Check if user has interrupted the program
        self.outputDuration        = 10                # Check length of WEBM/GIF
        self.numOutputs            = 5                 # Check number of outputs
        self.wadsworthConstant     = True              # Check if we're skipping first 30% of the video
        self.time_array            = [0, 0, 0]         # Used for calculating a custom start time in single mode
        self.customStartTime       = 0                 # Calculated from time_array, inits to 0
        self.single_mode           = False             # Check if user wants a single webm at specific time 
        self.thumbnailNumTilesSide = 2                 # Used to calculate total number of tiles in NxN grid
        self.output_type           = 'WEBM'            # Check what kind of output, WEBM or GIF, user wants
        self.thumbnailMode         = False             # Used to check if we're making a big N by N thumbnail 
        self.targetSizeSet         = False             # Check if user has enabled a target file size
        self.audioEnabled          = True              # Used to check if user wants audio in WEBM or not
        self.bitrate               = 1500              # Helps specify what bitrate user needs for WEBM
        self.selectedVideo         = ""                # Used to save selected video from list widget

        # Set defaults for GUI slider positions, checkboxes, and labels
        self.durationSlider.setSliderPosition(10)
        self.widthSlider.setSliderPosition(500)
        self.numOutputsSlider.setSliderPosition(5)
        self.bitRateSlider.setSliderPosition(1500)
        self.fileSizeSlider.setSliderPosition(4000)
        self.wadsworthCheckBox.setChecked(True)
        self.editTargetFileSizeCheckBox()
        self.populateListLabel()
        self.editDurationLabel()
        self.editWidthLabel()
        self.editnumOutputsLabel()
        self.editBitrateLabel()
        self.editTargetFileSizeSliderLabel()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "WEBMARIZER"))
        #===================================================================#
        self.durationLabel.setText(_translate("MainWindow",'''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">WEBM Duration: </span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.widthLabel.setText(_translate("MainWindow", '''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">WEBM Width:</span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.numOutputsLabel.setText(_translate("MainWindow",'''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">Number of WEBMs:</span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.generalTab),
            _translate("MainWindow", "General Options"))
        #===================================================================#
        self.bitrateLabel.setText(_translate("MainWindow",'''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">Bitrate:</span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.targetFileSizeLabel.setText(_translate("MainWindow",'''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">Target File Size (MB):</span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.targetSizeCheckmarkLabel.setText(_translate("MainWindow",'''
            <html>
            <head/>
                <body>
                    <p><span style=\" font-size:16pt;\">Enable Target File Size</span></p>
                </body>
            </html>
        '''))
        #===================================================================#
        self.timeEdit.setDisplayFormat(_translate("MainWindow",
            "hh:mm:ss"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.advancedTab),
            _translate("MainWindow", "Advanced Options"))
        self.createBtn.setText(_translate("MainWindow",
            "Create WEBM\n(All videos)"))
        self.startSingleBtn.setText(_translate("MainWindow",
            "Create WEBM \n(Selected videos)"))
        self.stopBtn.setText(_translate("MainWindow",
            "Stop Process"))
        self.thumbnailDropdown.setItemText(0, _translate("MainWindow",
            "2x2"))
        self.thumbnailDropdown.setItemText(1, _translate("MainWindow",
            "3x3"))
        self.thumbnailDropdown.setItemText(2, _translate("MainWindow",
            "4x4"))
        self.thumbnailDropdown.setItemText(3, _translate("MainWindow",
            "5x5"))
        self.thumbnailDropdown.setItemText(4, _translate("MainWindow",
            "6x6"))

        #===================================================================#
        #                       WINDOWS GUI SETTINGS                        #
        #===================================================================#
        if (platform.system() == 'Windows'): # For some reason Mac OSX and Windows font sizes differ? 
            self.enableAudioLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\"font-size:8pt;\">Enable Audio</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\"font-size:8pt;\">Enable Target File Size</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.gifModeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:8pt;\">"Enable GIF Mode</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.thumbnailModeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:8pt;\">Enable THumbnail Mode</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.wadsworthLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:8pt;\">Enable Wadsworth Constant (Skip first ~30%)</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.videoListTitleLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:8pt;\">Videos</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.startTimeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:8pt;\">Single GIF/WEBM starting at time:</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
        else:
            #####################################################################
            #                       MAC/Linux GUI SETTINGS                      #
            #####################################################################
            self.enableAudioLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:16pt;\">Enable Audio</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.targetSizeCheckmarkLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:16pt;\">Enable Target File Size</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.gifModeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:16pt;\">Enable GIF Mode</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.thumbnailModeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\"font-size:16pt;\">Enable Thumbnail Mode</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.wadsworthLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\"font-size:16pt;\">Enable Wadsworth Constant (Skip first ~30%)</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.videoListTitleLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:16pt;\">Videos</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
            self.startTimeLabel.setText(_translate("MainWindow",'''
                <html>
                <head/>
                    <body>
                        <p><span style=\" font-size:16pt;\">Single GIF/WEBM starting at time:</span></p>
                    </body>
                </html>
            '''))
            #===================================================================#
    # Determine the video currently selected in the video list
    def setSelected(self):
        self.selectedVideo = self.listWidget.selectedItems()[0].text()
    
    # Attempt to pass externally created process to GUI that we can run .kill on it on button press.
    # So far, GUI freezing has prevented this. Look into multi-threading to solve
    def setProcess(self, FFmpegProcess):
        self.FFmpegProcess = FFmpegProcess

    # Attempts to kill WEBM creation process
    def stopProcess(self):
        self.FFmpegProcess.kill()
        self.stopped = False

    # Return whether process has been stopped or not
    # To-do: Fix this. I think we're going to need a separate thread so GUI doesn't freeze
    # during FFmpeg process. 
    def getProcessStoppedStatus(self):
        return self.stopped

    # Sets number of tiles per side in thumbnail to corresponding dropdown value
    def editThumbnailMode(self):
        if (self.thumbnailDropdown.currentText() == '2x2'):
            self.thumbnailNumTilesSide = 2
        elif (self.thumbnailDropdown.currentText() == '3x3'):
            self.thumbnailNumTilesSide = 3
        elif (self.thumbnailDropdown.currentText() == '4x4'):
            self.thumbnailNumTilesSide = 4
        elif (self.thumbnailDropdown.currentText() == '5x5'):
            self.humbnailNumTilesSide = 5
        elif (self.thumbnailDropdown.currentText() == '6x6'):
            self.thumbnailNumTilesSide = 6

    # Return num tiles per side
    def getNumVideoTilesSide(self):
        self.editThumbnailMode()
        return self.thumbnailNumTilesSide

    # Sets output_type to either GIF or WEBM, then change button & slider labels 
    def enableGifMode(self):
        if (self.gifModeCheckBox.isChecked()):
            self.createBtn.setText("Create GIF\n(All videos)")
            self.startSingleBtn.setText("Create GIF \n(Selected videos)")
            self.output_type = 'GIF'
            self.durationLabel.setText("GIF Duration: " + str(self.durationSlider.value()) + " seconds")
            self.widthLabel.setText("GIF Width: " + str(self.widthSlider.value()) + " px")
            self.numOutputsLabel.setText("Number of GIFs: " + str(self.numOutputsSlider.value()))
            self.audioCheckBox.setChecked(False)
            self.thumbnailModeCheckBox.setChecked(False)
        else:
            self.createBtn.setText("Create WEBM\n(All videos)")
            self.startSingleBtn.setText("Create WEBM \n(Selected videos)")
            self.output_type = 'WEBM'
            self.editDurationLabel()
            self.editWidthLabel()
            self.editnumOutputsLabel()
        print("Current Mode: " + self.output_type)

    # Return the output type (GIF/WEBM) that user wants
    def getOutputType(self):
        self.enableGifMode()
        return self.output_type

    # Determines whether we skip first 30% of video or not. To-do: make this customizeable.
    def enableWadsworth(self):
        if (self.wadsworthCheckBox.isChecked()):
            self.wadsworthConstant = 30
            print("Wadsworth constant is enabled. Skipping first 30% of video.")
        else:
            self.wadsworthConstant = 0
            print("Wadsworth constant is disabled. Starting from beginning of video.")

    # Get the value of wadsworth 
    def getWadsworth(self):
        self.enableWadsworth()
        return self.wadsworthConstant

    # If user specifies specific start time for GIF/WEBM set hrs, mins, and seconds from GUI
    # Also disable number of outputs slider since only making 1 GIF/WEBM
    def singleMode(self):
        if (self.startTimeCheckBox.isChecked()):
            self.single_mode = True
            self.time_array[0] = self.timeEdit.time().hour()
            self.time_array[1] = self.timeEdit.time().minute()
            self.time_array[2] = self.timeEdit.time().second()
            self.numOutputsSlider.setEnabled(False)
            self.numOutputsSlider.setSliderPosition(1)
            self.numOutputsLabel.setText("Disabled (Single GIF/WEBM mode enabled)")
            self.thumbnailModeCheckBox.setChecked(False)
            print("Selected Time: " + str(self.time_array))
        else:
            self.single_mode = False
            self.numOutputsSlider.setEnabled(True)
            self.enableGifMode() # Return the label back to proper value

    # Get the time requested by user for Single mode
    def getCustomStartTime(self):
        self.customStartTime = (self.time_array[0] * 3600) + (self.time_array[1] * 60) + self.time_array[2]
        return self.customStartTime

    # Determine whether single mode is enabled and return bool true if it is
    def getSingleModeState(self):
        return self.single_mode

    # Sets thumbnailMode bool based on GUI checkbox value
    def thumbnailMode(self):
        if (self.thumbnailModeCheckBox.isChecked()):
            self.thumbnailMode = True
            self.gifModeCheckBox.setChecked(False)
            self.startTimeCheckBox.setChecked(False)
        else:
            self.thumbnailMode = False

    # Returns thumbnailMode bool
    def getThumbnailModeState(self):
        return self.thumbnailMode

    # Sets label to user selected WEBM duration from slider value
    def editDurationLabel(self):
        self.durationLabel.setText("WEBM Duration: " + str(self.durationSlider.value()) + " seconds")
        self.editoutputDuration()

    # Sets webm duration to corresponding slider value
    def editoutputDuration(self):
        self.outputDuration = self.durationSlider.value()
        if self.targetSizeSet:
            self.editFileSize()

    # Returns the output duration specific by user
    def getOutputDuration(self):
        return self.outputDuration

    # Set the bitrate label value
    def editBitrateLabel(self):
        if self.targetSizeSet:
            self.bitrateLabel.setText("Bitrate: " + str(self.bitRateSlider.value()) + " kbits/s (Slider disabled)")
        else:
            self.bitrateLabel.setText("Bitrate: " + str(self.bitRateSlider.value()) + " kbits/s")
        self.editBitrate()
    
    # Changes bitrate to corresponding slider value
    def editBitrate(self):
        self.bitrate = self.bitRateSlider.value()

    # Return user-specific bitrate
    def getBitrate(self):
        return self.bitrate

    # Changes boolean for audio enabled
    def editAudioCheckBox(self):
        self.audioEnabled = self.audioCheckBox.isChecked()
        if self.audioEnabled:
            self.gifModeCheckBox.setChecked(False)
            
    # Return whether the user has enabled audio or not
    def getAudioEnabledState(self):
        return self.audioEnabled

    # Changes value of target file size 
    def editTargetFileSizeCheckBox(self):
        self.targetSizeSet = self.targetFileSizeCheckBox.isChecked()
        self.editTargetFileSizeSliderLabel()
        self.editBitrateLabel()

    # Return the boolean value of the checkbox
    def getFileSizeCheckboxState(self):
        return self.targetSizeSet

    # Set the target file size label
    def editTargetFileSizeSliderLabel(self):    
        if self.targetSizeSet:
            self.editFileSize()
            self.bitRateSlider.setEnabled(False)
            self.fileSizeSlider.setEnabled(True)
            self.targetFileSizeLabel.setText("Target File Size: " + str(self.fileSizeSlider.value()/1000) + " MB")
        else:
            self.fileSizeSlider.setEnabled(False)
            self.bitRateSlider.setEnabled(True)
            self.targetFileSizeLabel.setText("Target File Size: Disabled")

    # Change value of file size to corresponding slider value
    def editFileSize(self):
        self.fileSize = self.fileSizeSlider.value()
        self.video_bitrate = ( ( self.fileSize * 8 * 1000 ) / self.outputDuration ) - 96000 #96 kbps audio bitrate
        self.bitRateSlider.setSliderPosition(self.video_bitrate / 1000)

    # Set the WEBM width label text to slider value
    def editWidthLabel(self):
        self.widthLabel.setText("WEBM Width: " + str(self.widthSlider.value()) + " px")
        self.editWidth() 

    # Set WEBM width variable to corresponding slider value
    def editWidth(self):
        self.outputWidth = self.widthSlider.value()

    # Get the width of the WEBM/GIF
    def getWidth(self):
        return self.outputWidth

    # Get the file size of the WEBM/GIF
    def getFileSize(self):
        return self.fileSize

    # Sets WEBM number label text to slider value
    def editnumOutputsLabel(self):
        self.numOutputsLabel.setText("Number of WEBMs: " + str(self.numOutputsSlider.value()))
        self.editnumOutputs()

    # Sets number of WEBMs variable to corresponding slider value
    def editnumOutputs(self):
        self.numOutputs = self.numOutputsSlider.value()
        
    # Get the number of outputs set by the user
    def getNumOutputs(self):
        return self.numOutputs

    # Sets the status label text to current WEBM we're creating
    def setStatusText(self, status):
        #self.statusLabel.setText(status)
        self.statusLabel.setText(status)

    # If there's videos in current folder, we show them in the list widget
    def populateListLabel(self):
        if (len(self.videos_array) > 0):
            for video in self.videos_array:
                item = QtWidgets.QListWidgetItem()
                item.setText(video)
                self.listWidget.addItem(item)
        else:
            item = QtWidgets.QListWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.listWidget.addItem("No videos found")

    # Starts creating WEBMs from all videos in list
    def createMedia(self):
        init(self.videos_array)

    # Starts creating WEBMs only from selected video in list
    # To-do: Add ability to select multiple videos from list using command/shift/ctrl etc
    def createSelectedMedia(self):
        processVideo(self.selectedVideo)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    GUI = Ui_MainWindow()
    GUI.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


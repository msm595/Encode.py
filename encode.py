#!/usr/bin/env python3.1


import os, json, time
from tkinter import *
import tkinter.filedialog as filedialog
from tkinter.ttk import *
from subprocess import call, PIPE, Popen, STDOUT
from re import compile

'''
Edit the paths below to your configuration:
'''

class Paths():
    def __init__(self):
        self.x264_8     = 'x264_8bit.exe'
        self.x264_10    = 'x264_10bit.exe'
        self.avs2yuv    = 'avs2yuv.exe'
        self.vfr        = 'D:\\tools\\Encode\\vfr.py'
        self.python     = 'python.exe'
        self.neroAacEnc = 'neroAacEnc.exe'
        self.eac3to     = 'eac3to.exe'
        self.mkvmerge   = 'mkvmerge.exe'


class Settings(): #the default settings for each job
    def __init__(self):
        self.deleteTemp = False #delete created temporary files? True or False
        self.pcmProperties = '-blu-ray -16 -big -2 -override' #what format are the pcms?
        self.oFps = '30000/1001' #original fps
        self.fFps = '24000/1001' #final fps
        self.crf  = 18
        self.bitDepth = 8
        self.size = (848, 480)
        self.audioQuality = 0.55

'''
Don't edit below this point unless you know what you are doing.
'''

#Globals
p = Paths()

sizeRe = compile("^([^#]*Resize)\(\s*(\d+),\s*(\d+)\s*\)")
tenRe = compile("^#10bit (.*)$")

"""
EventEmitter class

Handles events

"""
class EventEmitter():
    def __init__(self):
        self.__l = {} #listeners
        #self._max = 10 #max amt of listeners
        #self._i = 0 # num of listeners
        self.__debugMode = False
    

    def on(self, event, listener):
        self.addListener(event, listener)
        #return self #for chaining

    def addListener(self, event, listener):
        self.__debug("AddListener:", event, listener)
        if event not in self.__l:
            self.__l[event] = set()
        
        self.__l[event].add(listener)
        self.emit('newListener', listener)
        #self._i += 1

        #if self._i >= self._max:
        #    print "[WARNING] There are currently " + str(self._i) + " listeners"
    
    def once(self, event, listener):
        self.__debug("Once:",event, listener)
        self.addListener(event, self.__makeOnce(event, listener))
    
    def __makeOnce(self, event, listener):
        def callback(*args):
            self.removeListener(event, callback)
            listener(*args)
        return callback
    
    def removeListener(self, event, listener):
        self.__debug("Remove:",event, listener)
        if event not in self.__l:
            return
        if listener not in self.__l[event]:
            return
        self.__l[event].remove(listener)
        
    def removeAllListeners(self, event=None):
        if event == none:
            self.__l.clear()
            #self._i = 0
        elif event in self.__l:
            self.__l[event].clear()
            #self._i -= 1
    
    def listeners(self, event):
        if event in self.__l:
            return self.__l[event]
        return None
    
    def emit(self, event, *args):
        self.__debug("Emit:",event)
        if event in self.__l:
            copy = self.__l[event].copy()
            for listener in copy:
                listener(*args)
    
    def __debug(self, *s):
        if not self.__debugMode:
            return
        ss = ""
        for sss in s:
            ss = ss + " " + str(sss)
        print("[EventEmitter] " + ss)
    
    def setDebug(self, d):
        self.__debugMode = d


"""
Log class

Extension of EventEmitter with a few convenient methods.

"""
class Log(EventEmitter):
    def __init__(self):
        EventEmitter.__init__(self)
    
    def info(self, msg):
        self.emit('info', msg)
    
    def warning(self, msg):
        self.emit('warning', msg)
    
    def error(self, msg):
        self.emit('error', msg)
    
    def write(self, msg):
        self.emit('write', msg)


"""
Job class

Handles the data for each job, emits to the log

"""
class Job():
    def __init__(self, avs, log, ident, settings):
        self.path = os.path.dirname(avs)
        self.id   = ident
        self.avs  = None
        self.oAvs = avs
        self.aud  = None
        self.s    = settings
        self.tDel = []
        #self.toDo = []
        self.log  = log

        self.name = None

        #self.createAvs(avs)

        self.log.info('Job %d created' % (self.id))
        self.findAudio()
    
    def actPath(self, file):
        return os.path.normpath(os.path.join(self.path, file))

    def createAvs(self):
        avs = self.oAvs
        self.log.info('Creaing avs file for job %d.' % (self.id))

        width, height = self.s.size

        sName = '.'.join(avs.split('.')[:-1])
        newAvsName = "%s %dp %sbit.avs" % (sName, height, self.s.bitDepth)

        if os.path.isfile(newAvsName):
            self.log.warning('\tAvs file already exists, skipping.')
            self.avs = newAvsName
            self.name = '.'.join(self.oAvs.split('.')[:-1])
            self.tDel.append(self.avs)
            return

        avsLines = []
        with open(self.oAvs) as avs:
            avsLines = [f.strip() for f in avs.readlines()]
        

        #TODO: make more effecient
        newAvs = [sizeRe.sub(lambda s: s.group(1)+'('+str(width)+', '+str(height)+')', f) for f in avsLines]
        if self.s.bitDepth > 8:
            newAvs = [tenRe.sub(lambda s: s.group(1), f) for f in newAvs]

        with open(newAvsName, 'w', encoding='utf-8') as output:
            [output.write(l+"\n") for l in newAvs]

        self.avs = newAvsName
        self.name = '.'.join(self.oAvs.split('.')[:-1])
        self.tDel.append(self.avs)

    def findAudio(self):
        files = os.listdir(self.path)
        audio = [f for f in files if f.endswith(('.pcm', '.wav', '.aac'))]
        #if len(audio) == 0:
        #    self.log.warning("Job with '" + self.avs + "' has no audio file")
        if len(audio) == 1:
            self.log.info("Auto selecting audio file '" + audio[0] + "' for job " + str(self.id))
            self.aud = self.actPath(audio[0])
        
        #self.log.emit('needAudioSelection', self.path, self.id)
    
    def hasAudioFile(self):
        return self.aud != None
    
    def delete(self):
        if not self.s.deleteTemp:
            return
        
        #TODO: delete all fines in self.tDel
        for d in self.tDel:
            os.remove(d)
        
        self.tDel = []
    
    def listen(self, a):

        while a.poll() is None:
            time.sleep(0.5)
            self.log.emit('updateGui')

    
    def convertAudio(self):
        self.log.info('Converting audio for job %d.' % (self.id))

        aS = self.aud.split('.')
        aExt = aS[-1].lower()
        aName = '.'.join(aS[:-1])

        if aExt == 'pcm': #Audio needs to be extracted to wav
            self.log.info('\tConverting audio from pcm to wav.')
            if os.path.isfile(aName+'.wav'):
                self.log.warning('\tWav file already exists, skipping.')
            else:
                eacCmd = '"%s" "%s" "%s" %s' % (p.eac3to, aName+'.pcm', aName+'.wav', self.s.pcmProperties)
                #eacExec = call(eacCmd)
                eacExec = Popen(eacCmd, stdout=sys.stdout, stderr=sys.stderr)
                self.listen(eacExec)
                #print(eacExec)
            aExt = 'wav'
            self.aud = aName + '.' + aExt

            self.tDel.append(aName+'.wav')
        
        if aExt == 'wav': #Audio needs to be encoded to aac
            self.log.info('\tConverting audio from wav to aac.')
            if os.path.isfile(aName+'.aac'):
                self.log.warning('\tAac file already exists, skipping.')
            else:
                neroCmd = '"%s" -q %s -if "%s" -of "%s"' % (p.neroAacEnc, self.s.audioQuality, aName+'.wav', aName+'.aac')
                print(neroCmd)
                neroExec = Popen(neroCmd, stdout=sys.stdout, stderr=sys.stderr)
                self.listen(neroExec)
                #neroExec = call(neroCmd, stdout=PIPE)
            aExt = 'aac'
            self.aud = aName + '.' + aExt

            self.tDel.append(aName+'.aac')

    def cutAudio(self):
        self.log.info('Cutting audio for job %d.' % (self.id))

        aS = self.aud.split('.')
        aExt = aS[-1].lower()
        aName = '.'.join(aS[:-1])

        vfrCmd = '"%s" "%s" -i "%s" -o "%s" -f %s -c "%s" -vmr --ofps %s "%s"' % (p.python, p.vfr, aName+'.aac', aName+'.cut.mka', self.s.oFps, self.name+'.xml', self.s.fFps, self.avs)
        vfrExec = call(vfrCmd)
        #vfrExec = call(vfrCmd, stdout=PIPE)

        if vfrExec == 0:
            aExt = 'cut.mka'
            self.aud = aName + '.' + aExt
        else:
            self.log.warning('\tThere was an error cutting the audio. Will mux the uncut aac file.')

    def encode(self):
        self.log.info('Encoding job %d.' % (self.id))

        width, height = self.s.size

        mp4File = "%s %dp %sbit.mp4" % (self.name, height, self.s.bitDepth)

        print(mp4File)

        if os.path.isfile(mp4File):
            self.log.warning('\tMp4 file already exists, skipping.')
        else:
            if self.s.bitDepth == 8:
                x264Cmd = '"%s" "%s" -o - | "%s" --demuxer y4m --preset veryslow --tune animation --crf %d --bframes 8 --ref 9 --thread-input --threads auto --output "%s" -' % (p.avs2yuv, self.avs, p.x264_8, self.s.crf, mp4File)
            else:
                x264Cmd = '"%s" "%s" -raw -o - | "%s" --demuxer raw --input-depth 16 --input-res %dx%d --fps %s --preset veryslow --tune animation --crf %d --bframes 8 --ref 16 --thread-input --threads auto --output "%s" -' % (p.avs2yuv, self.avs, p.x264_10, width, height, self.s.fFps, self.s.crf, mp4File)
            
            #x264Exec = call(x264Cmd, shell=True)
            x264Exec = Popen(x264Cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
            self.listen(x264Exec)
            #x264Exec = call(x264Cmd, shell=True, stdout=PIPE)
    
    def mux(self):
        self.log.info('Muxing job %d.' % (self.id))

        width, height = self.s.size

        mp4File = "%s %dp %sbit.mp4" % (self.name, height, self.s.bitDepth)

        bit = "h264" if self.s.bitDepth == 8 else "Hi10"
        mkvFile = "%s [%dp %s AAC][Raw].mkv" % (self.name, height, bit)
        
        if os.path.isfile(mkvFile):
            self.log.error('\tMp4 file already exists.')
        else:
            chapters = self.name + '.xml'
            chapters = ('--chapters "' + chapters + '"') if os.path.isfile(chapters) else ''
            mkvCmd = '"%s" -v -o "%s" %s --language 1:jpn --default-track 1:yes --compression 1:none -a 1 -D -S -T --no-global-tags --no-chapters "%s"\
            --language 1:jpn --default-track 1:yes --compression 1:none -d 1 -A -S -T --no-global-tags --no-chapters "%s"' % (p.mkvmerge, mkvFile, chapters, self.aud, mp4File)
            #mkvExec = call(mkvCmd, stdout=PIPE) 
            mkvExec = Popen(mkvCmd, stdout=sys.stdout, stderr=sys.stderr)
            self.listen(mkvExec)
            mkvExec = mkvExec.poll()
            if mkvExec == 0:
                self.info('File %s sucessfully muxed' % (mkvFile))

    def __str__(self):
        return "%d %s crf:%d %dbit %dp" % (self.id, self.avs, self.s.crf, self.s.bitDepth, self.s.size[1])

    def info(self):
        return (self.id, self.oAvs, self.aud, self.s.crf, self.s.bitDepth, self.s.pcmProperties, self.s.oFps, self.s.fFps, self.s.size[1])

    #def setId(self, ident):
    #    self.id = ident
    #
    #def getId(self):
    #    return self.id


"""
Model class

Handles all the data, controls Jobs, Paths, Settings, is an eventemitter that the Controller will listen to.

"""
class Model(EventEmitter):
    def __init__(self):
        EventEmitter.__init__(self)
        #self.p = Paths()
        #self.s = Settings()
        self.log = Log()
        self.jobs = []

        self.log.on('info', self.info)
        self.log.on('warning', self.warning)
        self.log.on('error', self.error)
        self.log.on('updateGui', self.updateGui)

        #self.log.on('needAudioSelection', self.selectAudio)
    
    def info(self, msg):
        self.emit('info', msg)
    
    def warning(self, msg):
        self.emit('warning', msg)
    
    def error(self, msg):
        self.emit('error', msg)

    def updateGui(self):
        self.emit('updateGui')

    def addJob(self, avs):
        # i = self.findJob(avs)
        # if i != -1:
        #     self.log.error("Job already exists with avs file '" + avs + "' at job " + str(i))
        #     return
        
        job = Job(avs, self.log, len(self.jobs), Settings())
        self.jobs.append(job)

        self.emit('jobList', self.listJobs())
        #if not job.hasAudioFile():
        #    self.emit('needAudioSelection', job.path, job.id)

    # def findJob(self, avs):
    #     for i,j in enumerate(self.jobs):
    #         if avs == j.avs:
    #             return i
    #     return -1
    
    # def delJob(self, avs):
    #     j = self.findJob(avs)
    #     if j == -1:
    #         self.log.error("Cannot remove job. Job doesn't exists with avs file '" + avs + "'")
    #         return
        
    #     self.delJobAtI(j)
    
    def delJobAtI(self, j):
        temp = self.jobs.pop(j)
        temp.delete()
        
        for i in range(j, len(self.jobs)):
            self.jobs[i].id = i

        self.emit('jobList', self.listJobs())

    def editJob(self, i, avs=None, audio=None, deleteTemp=None, pcmProperties=None, oFps=None, fFps=None, crf=None, bitDepth=None, height=None):
        job = self.jobs[i]

        if avs != None:
            job.oAvs = os.path.normpath(avs)
            job.path = os.path.dirname(job.oAvs)
            job.name = '.'.join(job.oAvs.split('.')[:-1])

        if audio != None:
            job.aud = os.path.normpath(audio)

        if deleteTemp != None:
            job.s.deleteTemp = deleteTemp
        
        if pcmProperties != None:
            job.s.pcmProperties = pcmProperties
        
        if oFps != None:
            job.s.oFps = oFps
        
        if fFps != None:
            job.s.fFps = fFps
        
        if crf != None:
            job.s.crf = int(crf or 0)
        
        if bitDepth != None:
            job.s.bitDepth = int(bitDepth)
        
        if height != None:
            #[(1920, 1080), (1280, 720), (848, 480)]
            if height == 480:
                size = (848, 480)
            elif height == 720:
                size = (1280, 720)
            elif height == 1080:
                size = (1920, 1080)
            else:
                size = job.s.size
            job.s.size = size
        
        self.emit('jobList', self.listJobs())

    def getJobInfo(self, i):
        return self.jobs[i].info()

    def listJobs(self):
        return [j.info() for j in self.jobs]
    
    def runJobs(self):
        for j in self.jobs:
            j.createAvs()
            j.convertAudio()
            j.cutAudio()
            j.encode()
            j.mux()
            j.delete()


"""
View class

A simple commandline gui

"""
class View(EventEmitter):
    def __init__(self):
        EventEmitter.__init__(self)
        self.root = Tk()

        self.root.title("Encode.py")

        self.frame = Frame(self.root)
        self.frame.grid(column=0, row=0, sticky=(N,S,E,W), padx=5, pady=5)

        self.jobs = Treeview(self.frame, columns=('id', 'avs', 'height', 'bit'), show="headings")
        self.jobs.grid(column=0,row=1, sticky=(N,S,E,W), padx=(0,5), rowspan=3)

        self.jobs.column("id", width=5, anchor=W)
        self.jobs.column("height", width=5, anchor=W)
        self.jobs.column("bit", width=5, anchor=W)
        self.jobs.heading('id', text="Id", anchor=W)
        self.jobs.heading('avs', text="Avs File", anchor=W)
        self.jobs.heading('height', text="Height", anchor=W)
        self.jobs.heading('bit', text="Bitdepth", anchor=W)

        Label(self.frame, text="Jobs:").grid(row=0,column=0, sticky=(N,S,W), pady=(0,5))

        addBtn = Button(self.frame, text="New Job")
        addBtn.grid(column=1, row=1, sticky=(N,E,W))

        removeBtn = Button(self.frame, text="Remove Job")
        removeBtn.grid(column=1, row=2, sticky=(N,E,W), pady=5)

        self.jobs.bind('<<TreeviewSelect>>', self.jobSelected)
        addBtn.bind("<Button-1>", self.newJobClick)
        removeBtn.bind("<Button-1>", self.delJobClick)

        ####################
        # Options:
        blackText = Style()
        blackText.configure("BW.TLabelframe", foreground="black")
        blackText.configure("BW.TLabelframe.Label", foreground="black")
        
        self.oFrame = LabelFrame(self.frame, text="Options:", style="BW.TLabelframe")
        #self.oFrame.winfo_class())
        self.oFrame.grid(row=4, column=0, sticky=(N,S,E,W), pady=5, columnspan=2)

        #Avs
        Label(self.oFrame, text="Avs File:").grid(row=0, column=0, padx=5, sticky=(N,S,W))
        self.avsS = StringVar()
        Entry(self.oFrame, textvariable=self.avsS).grid(row=0, column=1, sticky=(N,S,E,W))
        self.avsB = Button(self.oFrame, text="Browse")
        self.avsB.grid(row=0, column=2, sticky=(N,E,W), padx=5)

        #Audio
        Label(self.oFrame, text="Audio File:").grid(row=1, column=0, padx=5, sticky=(N,S,W))
        self.audS = StringVar()
        Entry(self.oFrame, textvariable=self.audS).grid(row=1, column=1, sticky=(N,S,E,W), pady=5)
        self.audB = Button(self.oFrame, text="Browse")
        self.audB.grid(row=1, column=2, sticky=(N,E,W), padx=5, pady=5)

        #innerframe
        self.iFrame = Frame(self.oFrame)
        self.iFrame.grid(row=2, column=0, columnspan=3, sticky=(N,S,E,W), padx=(5,10), pady=10)

        #crf
        Label(self.iFrame, text="Crf:").grid(row=0, column=0, padx=5, sticky=(N,S,W), pady=(0,5))
        self.crfS = StringVar()
        Combobox(self.iFrame, textvariable=self.crfS, values=('14', '16', '18')).grid(row=0, column=1, sticky=(N,S,E,W), pady=(0,5))

        #bitDepth
        Label(self.iFrame, text="Bit depth:").grid(row=0, column=2, padx=5, sticky=(N,S,W), pady=(0,5))
        self.bitS = StringVar()
        self.bitC = Combobox(self.iFrame, textvariable=self.bitS, values=('8', '10'), state="readonly")
        self.bitC.grid(row=0, column=3, sticky=(N,S,E,W), pady=(0,5))

        #pcm
        Label(self.iFrame, text="Pcm properties:").grid(row=1, column=0, padx=5, sticky=(N,S,W), pady=(0,5))
        self.pcmS = StringVar()
        Entry(self.iFrame, textvariable=self.pcmS).grid(row=1, column=1, sticky=(N,S,E,W), pady=(0,5))

        #width
        Label(self.iFrame, text="Size:").grid(row=1, column=2, padx=5, sticky=(N,S,W), pady=(0,5))
        self.sizeS = StringVar()
        self.sizeC = Combobox(self.iFrame, textvariable=self.sizeS, values=('848x480', '1280x720', '1920x1080'), state="readonly")
        self.sizeC.grid(row=1, column=3, sticky=(N,S,E,W), pady=(0,5))

        #oFps
        Label(self.iFrame, text="Original fps:").grid(row=2, column=0, padx=5, sticky=(N,S,W), pady=(0,5))
        self.oFpsS = StringVar()
        self.oFpsC = Combobox(self.iFrame, textvariable=self.oFpsS, values=('30000/1001', '24000/1001'), state="readonly")
        self.oFpsC.grid(row=2, column=1, sticky=(N,S,E,W), pady=(0,5))

        #fFps
        Label(self.iFrame, text="Final fps:").grid(row=2, column=2, padx=5, sticky=(N,S,W), pady=(0,5))
        self.fFpsS = StringVar()
        self.fFpsC = Combobox(self.iFrame, textvariable=self.fFpsS, values=('30000/1001', '24000/1001'), state="readonly")
        self.fFpsC.grid(row=2, column=3, sticky=(N,S,E,W), pady=(0,5))

        self.iFrame.columnconfigure(1, weight=1)
        self.iFrame.columnconfigure(3, weight=1)

        self.oFrame.columnconfigure(1, weight=1)

        ####
        #status box
        Label(self.frame, text="Log:").grid(row=5, column=0, sticky=(N,S,W))
        self.box = Text(self.frame, height=10)
        self.box.grid(row=6, column=0, columnspan=3, sticky=(N,S,E,W), pady=5)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1, minsize=500)
        self.frame.rowconfigure(3, weight=1, minsize=100)


        encB = Button(self.frame, text="Start Encoding")
        encB.grid(row=7, column=0, columnspan=2, pady=5)

        encB.bind('<Button-1>', lambda x: self.emit('encode'))


        #EVENTS MORE OF
        self.avsB.bind('<Button-1>', self.selectAvs)
        self.audB.bind('<Button-1>', self.selectAud)

        self.avsS.trace('w', self.jobEdited)
        self.audS.trace('w', self.jobEdited)
        self.crfS.trace('w', self.jobEdited)
        self.bitS.trace('w', self.jobEdited)
        self.pcmS.trace('w', self.jobEdited)
        self.sizeS.trace('w', self.jobEdited)
        self.oFpsS.trace('w', self.jobEdited)
        self.fFpsS.trace('w', self.jobEdited)

        #Used to tell the updated event handlers that 
        self.justSelected = [False for i in range(0,8)]

        self.writeNum = 0

    def selectAvs(self, e=None):
        avsName = filedialog.askopenfilename(filetypes=[('Avisynth script', '*.avs'), ('Any', '*.*')])
        if avsName != None and len(avsName)>0:
            self.avsS.set(avsName)
    
    def selectAud(self, e=None):
        audName = filedialog.askopenfilename(filetypes=[('Audio Files', '*.pcm *.wav *.aac'), ('Pcm Audio File', '*.pcm'), ('Wav audio file', '*.wav'), ('Aac Audio File', '*.aac')])
        if audName != None and len(audName)>0:
            self.audS.set(audName)

    def jobList(self, list):
        numChilds = len(self.jobs.get_children())
        sel = self.jobs.focus()
        if sel == '':
            id = None
        else:
            id = int(self.jobs.item(sel, "values")[0])

        children = self.jobs.get_children()
        for child in children:
            self.jobs.delete(child)

        for j in list:
            name = os.path.basename(j[1])
            self.jobs.insert("", END, values=(j[0], name, j[8], j[4]))
        
        if len(self.jobs.get_children()) > numChilds: #new has been added
            childs = self.jobs.get_children()
            toS = childs[numChilds]
            self.jobs.selection_set(toS)
            self.jobs.focus(toS)
            self.jobs.see(toS)
            return

        if id != None:
            childs = self.jobs.get_children()
            if id < len(childs):
                toS = childs[id]
                self.jobs.selection_set(toS)
                self.jobs.focus(toS)
                self.jobs.see(toS)
        #print(list)
    
    def info(self, i):
        w = '[ERROR] ' + i
        self.box.insert(END, i+'\n')
        print(i)
    
    def warning(self, w):
        w = '[ERROR] ' + w
        self.box.insert(END, w+'\n')
        print(w)
    
    def error(self, e):
        w = '[ERROR] ' + e
        self.box.insert(END, e+'\n')
        print(e)

    def write(self, w):
        self.box.insert(END, w)

        self.root.update()
        self.box.see(END)

        #old = self.writeNum
        #self.writeNum = (self.writeNum + 1) % 16

        # if self.writeNum < old:
        #     self.root.update()
        #     self.box.see(END)
    
    def updateGui(self):
        self.root.update()

    def jobEdited(self, o, t, mode):
        sel = self.jobs.focus()
        if sel == '':
            return #not possible, but just in case

        varNum = int(o[6:])
        if self.justSelected[varNum]:
            self.justSelected[varNum] = False
            return

        jobNum = int(self.jobs.item(sel, "values")[0])

        size = self.sizeS.get()
        if size == '848x480':
            height = 480
        elif size == '1280x720':
            height = 720
        else:
            height = 1080


        #Todo: add option for deleteTemp
        self.emit('jobInfoEdit', jobNum, self.avsS.get(), self.audS.get(), 
            None, self.pcmS.get(), self.oFpsS.get(), self.fFpsS.get(), self.crfS.get(), self.bitS.get(), height)
        #print('Edit!')
        #print(o)
        #print('Mode: ' + mode)
    
    def jobInfo(self, i):
        self.avsS.set(i[1] or '')
        self.audS.set(i[2] or '')
        self.crfS.set(int(i[3]) or 18)
        self.bitS.set(int(i[4]) or 8)
        self.pcmS.set(i[5] or '')

        if i[8] == 480:
            size = '848x480'
        elif i[8] == 720:
            size = '1280x720'
        else:
            size = '1920x1080'

        self.sizeS.set(size)

        self.oFpsS.set(i[6] or '30000/1001')
        self.fFpsS.set(i[7] or '24000/1001')
        #print(i)

    def newJobClick(self, e=None):
        avsName = filedialog.askopenfilename(filetypes=[('Avisynth script', '.avs'), ('Any', '.*')])

        if avsName != None and len(avsName)>0:
            self.emit('newJob', avsName)
        #else:
        #    print("None")
        return 'break'
    
    def jobSelected(self, e=None):
        sel = self.jobs.focus()
        if sel == '':
            return #not possible, but just in case
        
        id = int(self.jobs.item(sel, "values")[0])
        self.justSelected = [True for i in range(0,8)]
        self.emit('getJobInfo', id)

    def delJobClick(self, e=None):
        sel = self.jobs.focus()
        if sel == '':
            return
        
        id = int(self.jobs.item(sel, "values")[0])
        self.emit('deleteJob', id)
        pass

    def run(self):
        self.root.mainloop()
            


"""
Controlled class

Controls and such

"""
class Controller():
    def __init__(self):
        self._model = Model()
        self._view = View()

        self._view.on('newJob', self._model.addJob)
        self._view.on('deleteJob', self._model.delJobAtI)
        self._view.on('runJobs', self._model.runJobs)
        self._view.on('getJobInfo', self.getJobInfo)
        self._view.on('jobInfoEdit', self._model.editJob)
        self._view.on('encode', self._model.runJobs)

        self._model.on('jobList', self._view.jobList)
        self._model.on('updateGui', self._view.updateGui)
        #self._model.on('needAudioSelection', self._view.selectAudio)

        self._model.on('info', self._view.info)
        self._model.on('warning', self._view.warning)
        self._model.on('error', self._view.error)
        self._model.on('write', self._view.write)

        self._view.run()
    
    def getJobInfo(self, id):
        self._view.jobInfo(self._model.getJobInfo(id))

def main():
    c = Controller()


if __name__ == "__main__":
    #for name in ttk.__all__:
        #print(name)
    main()
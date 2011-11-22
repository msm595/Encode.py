#!/usr/bin/env python3.1

import os, json
from subprocess import call
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

'''
Don't edit below this point unless you know what you are doing.
'''

#Globals
p = Paths()

sizeRe = compile("^([^#]*Resize)\(\s*(\d+),\s*(\d+)\s*\)")
tenRe = compile("^#10bit (.*)$")


"""
Job class

Handles the data for each job, emits to the log

"""
class Job():
    def __init__(self, avs, log, ident, settings):
        self.path = os.path.dirname(avs)
        self.id   = ident
        self.avs  = None
        self.aud  = None
        self.s    = settings
        self.del = []
        #self.toDo = []
        self.log  = log

        self.name = None

        self.createAvs(avs)
        self.findAudio()
    
    def createAvs(self, avs):
        self.log.info('Creaing avs file for job %d.' % (self.id))

        sName = ''.join(avs.split('.')[:-1])
        newAvsName = "%s %dp %sbit.avs" % (sName, height, self.s.bitDepth)

        if os.path.isfile(newAvsName):
            self.log.warning('\tAvs file already exists, skipping.')
            self.avs = newAvsName
            self.name = ''.join(self.avs.split('.')[:-1])
            self.del.append(self.avs)
            return

        avsLines = []
        with open(o['avsFile']) as avs:
            avsLines = [f.strip() for f in avs.readlines()]
        
        width, height = self.s.size

        #TODO: make more effecient
        newAvs = [sizeRe.sub(lambda s: s.group(1)+'('+str(width)+', '+str(height)+')', f) for f in avsLines]
        if depth > 8:
            newAvs = [tenRe.sub(lambda s: s.group(1), f) for f in newAvs]

        with open(newAvsName, 'w', encoding='utf-8') as output:
            [output.write(l+"\n") for l in newAvs]

        self.avs = newAvsName
        self.name = ''.join(self.avs.split('.')[:-1])
        self.del.append(self.avs)

    def findAudio(self):
        files = os.listdir(self.path)
        audio = [f for f in files if f.endswith(('.pcm', '.wav', '.aac'))]
        #if len(audio) == 0:
        #    self.log.warning("Job with '" + self.avs + "' has no audio file")
        if len(audio) == 1:
            self.log.info("Auto selecting audio file '" + audio[0] + "' for job " + str(self.id))
            self.aud = audio[0]
        
        #self.log.emit('needAudioSelection', self.path, self.id)
    
    def hasAudioFile(self):
        return self.aud != None
    
    def delete(self):
        if not self.s.deleteTemp:
            return
        
        #TODO: delete all fines in self.del
        for d in self.del:
            os.remove(d)
        
        self.del = []
    
    def convertAudio(self):
        self.log.info('Converting audio for job %d.' % (self.id))

        aS = self.aud.split('.')
        aExt = aS[-1].lower()
        aName = ''.join(aS[:-1])

        if aExt == 'pcm': #Audio needs to be extracted to wav
            self.log.info('\tConverting audio from pcm to wav.')
            if os.path.isfile(aName+'.wav'):
                self.log.warning('\tWav file already exists, skipping.')
            else:
                eacCmd = '"%s" "%s" "%s" %s' % (p.eac3to, aName+'.pcm', aName+'.wav', self.s.pcmProperties)
                eacExec = call(eacCmd)
                #print(eacExec)
            aExt = 'wav'
            self.aud = aName + '.' + aExt

            self.del.append(aName+'.wav')
        
        if aExt == 'wav': #Audio needs to be encoded to aac
            self.log.info('\tConverting audio from wav to aac.')
            if os.path.isfile(aName+'.aac'):
                self.log.warning('\tAac file already exists, skipping.')
            else:
                neroCmd = '"%s" -q %s -if "%s" -of "%s"' % (p.neroAacEnc, self.s.audioQuality, aName+'.wav', aName+'.aac')
                neroExec = call(neroCmd)
            aExt = 'aac'
            self.aud = aName + '.' + aExt

            self.del.append(aName+'.aac')

    def cutAudio(self):
        self.log.info('Cutting audio for job %d.' % (self.id))

        aS = self.aud.split('.')
        aExt = aS[-1].lower()
        aName = ''.join(aS[:-1])

        vfrCmd = '"%s" "%s" -i "%s" -o "%s" -f %s -c "%s" -vmr --ofps %s "%s"' % (p.python, p.vfr, aName+'.aac', aName+'.cut.mka', self.s.oFps., self.name+'.xml', self.s.fFps, self.avs)
        vfrExec = call(vfrCmd)

        if vfrExec == 0:
            aExt = 'cut.mka'
            self.aud = aName + '.' + aExt
        else:
            self.log.warning('\tThere was an error cutting the audio. Will mux the uncut aac file.')

    def encode(self):
        self.log.info('Encoding job %d.' % (self.id))

        width, height = self.s.size

        mp4File = "%s %dp %sbit.mp4" % (self.name, height, self.s.bitDepth)

        if os.path.isfile(mp4File):
            self.log.warning('\tMp4 file already exists, skipping.')
        else:
            if self.s.bitDepth == 8:
                x264Cmd = '"%s" "%s" -o - | "%s" --demuxer y4m --preset veryslow --tune animation --crf %d --bframes 8 --ref 9 --thread-input --threads auto --output "%s" -' % (p.avs2yuv, self.avs, p.x264_8, self.s.crf, mp4File)
            else:
                x264Cmd = '"%s" "%s" -raw -o - | "%s" --demuxer raw --input-depth 16 --input-res %dx%d --fps %s --preset veryslow --tune animation --crf %d --bframes 8 --ref 16 --thread-input --threads auto --output "%s" -' % (p.avs2yuv, newAvsName, p.x264_10, width, height, self.s.fFps, self.s.crf, mp4File)
            
            x264Exec = call(x264Cmd, shell=True)
    
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
            mkvExec = call(mkvCmd) 
            if mkvExec == 0:
                self.info('File %s sucessfully muxed' % (mkvName))

    def __str__(self):
        width, height = self.s.size
        return "%d %s crf:%d %dbit %dp" % (self.id, self.avs, self.s.crf, self.s.bitDepth, width)

    def info(self):
        return (self.id, self.avs, self.s.crf, self.s.bitDepth, width)

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
    def __init__():
        EventEmitter.__init__(self)
        #self.p = Paths()
        #self.s = Settings()
        self.log = Log()
        self.jobs = []

        self.log.on('info', self.info)
        self.log.on('warning', self.warning)
        self.log.on('error', self.error)

        self.log.on('needAudioSelection', self.selectAudio)
    
    def info(self, msg):
        self.emit('info', msg)
    
    def warning(self, msg):
        self.emit('warning', msg)
    
    def error(self, msg):
        self.emit('error', msg)

    def addJob(self, avs):
        i = self.findJob(avs)
        if i != -1:
            self.log.error("Job already exists with avs file '" + avs + "' at job " + str(i))
            return
        
        job = Job(avs, self.log, len(self.jobs), s.deleteTemp)
        self.jobs.append(job)

        if not job.hasAudioFile():
            self.emit('needAudioSelection', job.path, job.id)

    def findJob(self, avs):
        for i,j in enumerate(self.jobs):
            if avs == self.jobs.avs:
                return i
        return -1
    
    def delJob(self, avs):
        j = self.findJob(avs)
        if j == -1:
            self.log.error("Cannot remove job. Job doesn't exists with avs file '" + avs + "'")
            return
        
        self.delJobAtI(j)
    
    def delJobAtI(self, i):
        temp = self.jobs.pop(j)
        temp.delete()

        for i in range(j, len(self.jobs)):
            self.jobs[i].id = i

    def editJob(self, i, deleteTemp=None, pcmProperties=None, oFps=None, oFps=None, crf=None, bitDepth=None, size=None):
        job = self.jobs[i]

        if deleteTemp != None:
            job.s.deleteTemp = deleteTemp
        
        if pcmProperties != None:
            job.s.pcmProperties = pcmProperties
        
        if oFps != None:
            job.s.oFps = oFps
        
        if oFps != None:
            job.s.oFps = oFps
        
        if crf != None:
            job.s.crf = crf
        
        if bitDepth != None:
            job.s.bitDepth = bitDepth
        
        if size != None:
            job.s.size = size

    def getJobInfo(self, i):
        return self.jobs[i].s

    def listJobs(self):
        return [j.info() for j in self.jobs]
    
    def runJobs(self):
        for j in self.jobs:
            j.covertAudio()
            j.cutAudio()
            j.encode()
            j.delete()


"""
View class

A simple commandline gui

"""
class View(EventEmitter):
    def __init__(self):
        EventEmitter.__init__(self)
    
    def printMenu(self):
        print('The following key do the following commands:')
        print('\tn - create a new job')
        print('\te - edit a job')
        print('\tl - list the current jobs')
        print('\tr - run job(s)')

    def run(self):
        while(True):
            self.printMenu()
            c = input()

            if len(c) == 0:
                continue
            
            c = c[0].lower()

            if c == 'n':
                self.newJob()
            elif c == 'e':
                self.editJob()
            elif c == 'l':
                self.listJobs()
            elif c == 'r':
                self.runJobs()
    
    def newJob(self):
        print("To navigate folders type the beginnings of the folder name or `..` to go up a folder. Type `.` to select the current folder.")

        folder = os.getcwd()
        while(True):
            folders = [f for f in os.listdir(folder) if os.path.isdir(f)]
            print('Current directory is `%s` \n ..' %s)
            [print(f) for f in folders]
            
            i = input("Navigate:")

            if i == '.':
                avs = [f for f in os.listdir(folder) if f.endswith('.avs')]
                if len(avs) == 0:
                    self.error('There is no avs file in this folder')
                    continue
                elif len(avs) == 1:
                    self.emit('newJob', avs[0])
                    print('Make sure you edit this new job or else it will have the default settings.')
                    return
                else:
                    print('The following avs files match:')
                    for n,f in enumerate(avs):
                        print('\t%d\t%s' % (n+1, f))
                    
                    n = input('Which avs file did you mean (-1 or any nonvalid number to exit):')
                    n = n - 1
                    if n >= 0 and n < len(avs):
                        self.emit('newJob', avs[n])
                        print('Make sure you edit this new job or else it will have the default settings.')
                        return
                    continue

            l = len(i)
            poss = [f for f in folders if len(f) >= l and f[l].lower() == i.lower()]

            if len(poss) == 1:
                folder = poss[0]
                continue
            elif len(poss) == 0:
                print('Could not find that folder.')
                continue
            else
                print('The following folders match:')
                for n,f in enumerate(poss):
                    print('\t%d\t%s' % (n+1, f))
                
                n = input('Which folder did you mean (-1 or any nonvalid number to exit):')
                n = n - 1
                if n >= 0 and n < len(poss):
                    folder = poss[n]
                continue

        def editJob(self):
            self.listJobs()
            i = input('Which job (#) do you wish to edit:')
            


"""
Controlled class

Controls and such

"""
class Controller():
    def __init__(self):
        self._model = Model()
        self._view = View()

        self._view.on('newJob', self._model.addJob)
        self._view.on('deleteJob', self.delJob)
        self._view.on('getJobList', self.getJobList)
        self._view.on('runJobs', self._model.runJobs)

        self._model.on('needAudioSelection', self._view.selectAudio)

        self._model.on('info', self._view.info)
        self._model.on('warning', self._view.warning)
        self._model.on('error', self._view.error)

        self._view.run()

    def delJob(self, i):
        self._model.delJobAtI(i-1)
    
    def getJobList(self, l):
        self._view.updateJobList(l)

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
        print "[EventEmitter] " + ss
    
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



def main():
    root = 


if __name__ == "__main__":
    main()
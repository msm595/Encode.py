#!/usr/bin/env python3.1

import os
from subprocess import call
from re import compile

# Change these to the full paths if they are not in your $PATH
path = {
    'x264 8bit': 'x264_8bit.exe',
    'x264 10bit': 'x264_10bit.exe',
    'avs2yuv': 'avs2yuv.exe',
    'vfr': 'D:\\tools\\Encode\\vfr.py',
    #'vfr': 'vfr.py',
    'python': 'python.exe',
    'neroAacEnc': 'neroAacEnc.exe',
    'eac3to': 'eac3to.exe',
    'mkvmerge': 'mkvmerge.exe'
}


def main():
    o = {
        'currentDir': os.getcwd(),
        'tempDir': 'temp\\',
        'audioFile': '',
        'avsFile': '',
        'jobs': [],
        'audioQuality': '0.55', #audio quality to encode with
        'pcmProperties': '-blu-ray -16 -big -2 -override' #values to use when extracting pcm audio
    }

    files = os.listdir(o['currentDir'])
    #print(ascii(files))
    audio = [f for f in files if f.endswith(('.pcm', '.wav', '.aac'))]
    avs = [f for f in files if f.endswith('.avs')]

    #Find the audio file
    if len(audio) == 0:
        print('[WARNING] No audio file found!')
    else:
        for i,a in enumerate(audio):
            o['audioFile'] = a
            if i == len(audio) - 1:
                break
            y = input('Is ' + ascii(a) + ' the correct audio file (Y/n):')
            if len(y) == 0 or y[0].lower() != 'n':
                break
            #print(y)
    

    #Find the avs file
    if len(avs) == 0:
        print('[WARNING] No avs file found!')
    else:
        for i,a in enumerate(avs):
            o['avsFile'] = a
            if i == len(avs) - 1:
                break
            y = input('Is ' + ascii(a) + ' the correct avs file (Y/n):')
            if len(y) == 0 or y[0].lower() != 'n':
                break
    

    #Encode the audio
    aS = o['audioFile'].split('.')
    aExt = aS[-1].lower()
    aName = ''.join(aS[:-1])
    
    if aExt == 'pcm': #Audio needs to be extracted to wav
        if os.path.isfile(aName+'.wav'):
            print('[Warning] Wav file already exists, skipping')
        else:
            eacExec = call('"%s" "%s" "%s" %s' % (path['eac3to'], aName+'.pcm', aName+'.wav', o['pcmProperties']))
            #print(eacExec)
        aExt = 'wav'
    
    if aExt == 'wav': #Audio needs to be encoded to aac
        if os.path.isfile(aName+'.aac'):
            print('[Warning] Aac file already exists, skipping')
        else:
            neroExec = call('"%s" -q %s -if "%s" -of "%s"' % (path['neroAacEnc'], o['audioQuality'], aName+'.wav', aName+'.aac'))
        aExt = 'aac'

    #Audio is now ready to be cut


    #Vfr.py this bitch!
    #vfr.py -i "5 PID 112 DELAY -386ms.aac" -o audio.cut.mka -f 30/1.001 -c chapters.xml -vmr --ofps 24/1.001 5.avs
    sS = o['avsFile'].split('.')
    sName = ''.join(sS[:-1])

    fpsO = input('Original fps of video (30/1.001 / 24/1.001):')
    fpsO = '30/1.001' if len(fpsO) == 0 or fpsO[0] == '3' else '24/1.001'

    fpsA = input('Output fps of video (24/1.001 / 30/1.001):')
    fpsA = '24/1.001' if len(fpsA) == 0 or fpsA[0] == '2' else '30/1.001'

    #print('"%s" "%s" -i "%s" -o "%s" -f %s -c "%s" -vmr --ofps %s "%s"' % (path['python'], path['vfr'], aName+'.aac', aName+'.cut.mka', fpsO, sName+'.xml', fpsA, o['avsFile']))
    vfrCmd = '"%s" "%s" -i "%s" -o "%s" -f %s -c "%s" -vmr --ofps %s "%s"' % (path['python'], path['vfr'], aName+'.aac', aName+'.cut.mka', fpsO, sName+'.xml', fpsA, o['avsFile'])
    #vfrCmd = '%s" -i "%s" -o "%s" -f %s -c "%s" -vmr --ofps %s "%s"' % (path['vfr'], aName+'.aac', aName+'.cut.mka', fpsO, sName+'.xml', fpsA, o['avsFile'])
    #print(vfrCmd)
    vfrExec = call(vfrCmd)
    
    if vfrExec == 0:
        aExt = 'cut.mka'
    else:
        y = input('Would you like to continue and mux "%s" as the audio file (Y/n):' % (aName+'.'+aExt))
        if len(y) == 0 or y[0].lower() == 'y':
            pass
        else:
            return

    
    #Get the jobs
    avalSizes = [(1920, 1080), (1280, 720), (848, 480)]
    while len(avalSizes) > 0:
        size = avalSizes.pop()
        y = input('Encode video in %dp (Y/n):' % (size[1]))
        if len(y) == 0 or y[0].lower() == 'y':
            y = input('\tUse crf (18, #):')
            crf = 18 if len(y) == 0 else int(y)

            y = input('\tUse bitdepth (Both,10,8):')
            y = 'b' if len(y) == 0 else y[0].lower()
            if y in ('b', '1'):
                o['jobs'].append((size, 10, crf))
            if y in ('b', '8'):
                o['jobs'].append((size, 8, crf))

    

    #Run the jobs
    sizeRe = compile("^([^#]*Resize)\(\s*(\d+),\s*(\d+)\s*\)")
    tenRe = compile("^#10bit (.*)$")
    avsLines = []
    with open(o['avsFile']) as avs:
        avsLines = [f.strip() for f in avs.readlines()]
        # for line in lines:
        #     m = sizeRe.match(line)
        #     if m != None:
        #         print(m.groups())

    for size, depth, crf in o['jobs']:
        width, height = size

        mp4File = "%s %dp %sbit.mp4" % (sName, height, depth)
        if os.path.isfile(mp4File):
            print('[ERROR] File with the name "%s" already exists, skipping.' % (mp4File))
        else:
            #TODO: fix, make more efficient
            newAvs = [sizeRe.sub(lambda s: s.group(1)+'('+str(width)+', '+str(height)+')', f) for f in avsLines]
            if depth > 8:
                newAvs = [tenRe.sub(lambda s: s.group(1), f) for f in newAvs]
            newAvsName = "%s %dp %sbit.avs" % (sName, height, depth)
            with open(newAvsName, 'w', encoding='utf-8') as output:
                [output.write(l+"\n") for l in newAvs]
            
            if depth == 8:
                x264Cmd = '"%s" "%s" -o - | "%s" --demuxer y4m --preset veryslow --colormatrix bt709 --transfer bt709 --colorprim bt709 --tune animation --crf %d --bframes 8 --ref 9 --thread-input --threads auto --output "%s" -' % (path['avs2yuv'], newAvsName, path['x264 8bit'], crf, mp4File)
            else:
                if fpsA[0] == '2':
                    rate = "24000/1001"
                else:
                    rate = "30000/1001"
                x264Cmd = '"%s" "%s" -raw -o - | "%s" --demuxer raw --input-depth 16 --input-res %dx%d --fps %s --preset veryslow --colormatrix bt709 --transfer bt709 --colorprim bt709 --tune animation --crf %d --bframes 8 --ref 16 --thread-input --threads auto --output "%s" -' % (path['avs2yuv'], newAvsName, path['x264 10bit'], width, height, rate, crf, mp4File)
            
            #print(x264Cmd)
            x264Exec = call(x264Cmd, shell=True)
        
        #Mux
        bit = "h264" if depth == 8 else "Hi10"
        mkvFile = "%s [%dp %s AAC][Raw].mkv" % (sName, height, bit)

        if os.path.isfile(mkvFile):
            print("[ERROR] Mkv file exists.")
        else:
            chapters = sName + '.xml'
            chapters = ('--chapters "' + chapters + '"') if os.path.isfile(chapters) else ''
            mkvCmd = '"%s" -v -o "%s" %s --language 1:jpn --default-track 1:yes --compression 1:none -a 1 -D -S -T --no-global-tags --no-chapters "%s"\
            --language 1:jpn --default-track 1:yes --compression 1:none -d 1 -A -S -T --no-global-tags --no-chapters "%s"' % (path['mkvmerge'], mkvFile, chapters, aName + '.' + aExt, mp4File)
            mkvExec = call(mkvCmd)

    print("\n")
    print(o)
    #print(o)

if __name__ == "__main__":
    main()
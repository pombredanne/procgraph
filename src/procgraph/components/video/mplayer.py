# OS X: install from http://ffmpegx.com/download.html
import subprocess 
from procgraph.core.block import Generator
from procgraph.core.registrar import default_library  
from procgraph.core.exceptions import ModelExecutionError
import numpy
import os
 
class MPlayer(Generator):
    ''' Plays a video stream.
    
    Config: 
        - file 

    ''' 
     
    def init(self):
        self.define_input_signals([])
        self.define_output_signals(["video"])
        self.file = self.get_config('file')
        
        # first we identify the video resolution
        args = 'mplayer -identify -vo null -ao null -frames 0'.split() + [self.file]
        output = check_output(args)
        
        info = {}
        for line in output.split('\n'):
            if line.startswith('ID_'):
                key,value=line.split('=',1)
                try: # interpret numbers if possible
                    value = eval(value)
                except: 
                    pass
                info[key]=value
            
        print "Video configuration: %s" % info

        keys = ["ID_VIDEO_WIDTH", "ID_VIDEO_HEIGHT",  "ID_VIDEO_FPS"]
        id_width, id_height, id_fps = keys
        for k in keys:
            if not k in info:
                raise ModelExecutionError('Could not find key %s in properties %s' %
                                          (k, sorted(info.keys())), self)
        
        self.width = info[id_width]
        self.height = info[id_height]
        self.fps = info[id_fps]

        self.shape = (self.height, self.width, 3)
        self.dtype = 'uint8'
         
        # format = {2: 'y8', 3: 'rgb24'}[len(image.shape)]
#        format = "+rawrgb24"
#        args = ['mplayer', self.file,
#                '-demuxer', 'rawvideo', '-vc', format,
#                '-rawvideo', 
#                'w=%d:h=%d:format=%s' % (self.width,self.height,format),
#                #'w=%d:h=%d' % (self.width,self.height)
#                ]

        format = "rgb24"
        fifo_name = 'mencoder_fifo'
        if os.path.exists(fifo_name):
            os.unlink(fifo_name)
        os.mkfifo(fifo_name)
        args = ['mencoder', self.file,'-ovc', 'raw', 
                '-rawvideo', 'w=%d:h=%d:format=%s' % (self.width,self.height,format),
                '-of', 'rawvideo',
                '-vf', 'format=rgb24',
                # '-oac', 'copy',
                '-nosound', 
                '-o',
                fifo_name
                # '/dev/stdout'
                ]
        
        print "command line: %s" % " ".join(args)
        
        #self.process = subprocess.Popen(args,stdout=subprocess.PIPE)
        self.process = subprocess.Popen(args)

        self.delta = 1.0 / self.fps
        self.set_state('timestamp', self.delta)
        
        self.stream = open(fifo_name,'r')
        
    def update(self):
#        bytes = self.height * self.width * 3
#        buffer = self.process.stdout.read(bytes)
#        print bytes, len(buffer)
#        frame = numpy.ndarray(shape=self.shape,dtype=self.dtype,
#                              buffer=buffer)
        dtype = numpy.dtype(('uint8', self.shape))
        rgb = numpy.fromfile(self.stream, dtype=dtype, count=1)
        rgb = rgb.squeeze()
#        print "dtype: ", rgb.dtype, rgb.shape
        
        t = self.get_state('timestamp')

        self.set_output(0, rgb, t)

        self.set_state('timestamp', t + self.delta)        
    
    def next_data_status(self):
        return (True, self.get_state('timestamp'))

default_library.register('mplayer',  MPlayer)



# backported from 2.7
def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output
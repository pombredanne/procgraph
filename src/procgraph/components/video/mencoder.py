# OS X: install from http://ffmpegx.com/download.html
import subprocess 

from procgraph.core.block import Block
from procgraph.core.registrar import default_library 
from procgraph.components  import check_rgb_or_grayscale
 
 
class MEncoder(Block):
    ''' Encodes a video stream.
    
    Input: H x W x 3  uint8  numpy array representing RGB image.
    Config: 
        - file 
        - vcodec   mpeg4
        - vbitrate 1000000
    
    Note that allowed codec and bitrate depend on your version of mencoder.
    ''' 
     
    def init(self):
        #self.set_config_default()
        self.process = None
        self.define_input_signals(["image"])
        self.define_output_signals([])
        self.file = self.config.file
        self.config.fps = 10 
        self.config.vcodec = 'mpeg4'
        self.config.vbitrate = 1000000
        
    def update(self):
        check_rgb_or_grayscale(self, 0)
        
        image = self.input.image        
        h, w = image.shape[0:2]
        fps = self.config.fps
        
        if self.process is None:
            vcodec = self.config.vcodec
            vbitrate = self.config.vbitrate
            
            format = {2: 'y8', 3: 'rgb24'}[len(image.shape)]
            
            args = ['mencoder', '/dev/stdin', '-demuxer', 'rawvideo',
                    '-rawvideo', 'w=%d:h=%d:fps=%d:format=%s' % (w, h, fps, format),
                    '-ovc', 'lavc', '-lavcopts',
                     'vcodec=%s:vbitrate=%d' % (vcodec, vbitrate),
                     '-o', self.file]
            print 'command line: %s' % " ".join(args)
            self.process = subprocess.Popen(args=args, stdin=subprocess.PIPE,
                                            #stderr=subprocess.PIPE,
                                            #stdout=subprocess.PIPE
                                            )
            
        self.process.stdin.write(image.data)
        self.process.stdin.flush()

default_library.register('mencoder', MEncoder)

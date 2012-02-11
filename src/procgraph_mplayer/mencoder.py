from . import convert_to_mp4
from procgraph import Block
from procgraph.block_utils import (expand, make_sure_dir_exists,
    check_rgb_or_grayscale)
from procgraph.utils import indent
import numpy
import os
import subprocess
from procgraph_mplayer.scripts.crop_video import video_crop


#"""
#sudo apt-get install libavcodec-extra-52 libavdevice-extra-52 
#libavfilter-extra-0 libavformat-extra-52 libavutil-extra-49 
#libpostproc-extra-51 libswscale-extra-0
#
#"""


class MEncoder(Block):
    ''' Encodes a video stream using ``mencoder``.
    
    Note that allowed codec and bitrate depend on your version of mencoder.
    '''
    Block.alias('mencoder')

    Block.input('image', 'Either a HxWx3 uint8 numpy array representing '
                         'an RGB image, or a HxW representing grayscale. ')

    Block.config('file', 'Output file (AVI/MP4 format)')
    Block.config('fps', 'Framerate of resulting movie. If not specified, '
                        'it will be guessed from data.', default=None)
    Block.config('fps_safe', 'If the frame autodetect gives strange results, '
                             'we use this safe value instead.', default=10)

    Block.config('vcodec', 'Codec to use.', default='mpeg4')
    Block.config('vbitrate', 'Bitrate -- default is reasonable.',
                             default=2000000)
    Block.config('quiet', "If True, suppress mencoder's messages",
                 default=True)
    Block.config('timestamps', "If True, also writes <file>.timestamps that"
        " includes a line with the timestamp for each frame", default=True)

    Block.config('crop', "If true, the video will be "
                 "post-processed and cropped", default=False)

    def init(self):
        self.process = None
        self.buffer = []
        self.image_shape = None # Shape of image being encoded

    def update(self):
        check_rgb_or_grayscale(self, 0)

        # Put image in a buffer -- we don't use it right away
        image = self.get_input(0)
        timestamp = self.get_input_timestamp(0)
        self.buffer.append((timestamp, image))

        if self.process is None:
            self.try_initialization()

        if self.process is not None:
            # initialization was succesful
            while self.buffer:
                timestamp, image = self.buffer.pop(0)
                self.write_value(timestamp, image)

    def try_initialization(self):
        # If we don't have at least two frames, continue
        if len(self.buffer) < 2:
            return

        # Get height and width from first image
        first_image = self.buffer[0][1]

        self.shape = first_image.shape
        self.height = self.shape[0]
        self.width = self.shape[1]
        self.ndim = len(self.shape)

        # Format for mencoder's rawvideo "format" option
        if self.ndim == 2:
            format = 'y8' #@ReservedAssignment
        else:
            if self.shape[2] == 3:
                format = 'rgb24' #@ReservedAssignment
            elif self.shape[2] == 4:
                # Note: did not try this yet
                format = 'rgba' #@ReservedAssignment
                msg = 'I detected that you are trying to write a transparent'
                msg += 'video. This does not work well yet (and besides,'
                msg += 'it is not supported in many applications, like '
                msg += 'Keynote. Anyway, the plan is to use mencoder '
                msg += 'to write a .AVI with codec "png".'
                self.error(msg)

        # guess the fps if we are not given the config
        if self.config.fps is None:
            delta = self.buffer[-1][0] - self.buffer[0][0]

            if delta == 0:
                timestamps = [x[0] for x in self.buffer]
                self.debug('Got 0 delta: timestamps: %s' % timestamps)
                fps = 0
            else:
                fps = (len(self.buffer) - 1) / delta

            # Check for very wrong results
            if not (3 < fps < 60):
                self.error('Detected fps is %.2f; this seems strange to me,'
                           ' so I will use the safe choice fps = %.2f.' %
                           (fps, self.config.fps_safe))
                fps = self.config.fps_safe
        else:
            fps = self.config.fps

        vcodec = self.config.vcodec
        vbitrate = self.config.vbitrate

        self.filename = expand(self.config.file)
        if os.path.exists(self.filename):
            self.info('Removing previous version of %s.' % self.filename)
            os.unlink(self.filename)

        _, ext = os.path.splitext(self.filename)

        self.tmp_filename = '%s-active.avi' % self.filename
        self.convert_to_mp4 = ext in ['.mp4', '.MP4']

        make_sure_dir_exists(self.filename)

        self.info('Writing %dx%d %s video stream at %.1f fps to %r.' %
                  (self.width, self.height, format, fps, self.filename))

        if format == 'rgba':
            ovc = ['-ovc', 'lavc', '-lavcopts',
                  'vcodec=png']
        else:
            ovc = ['-ovc', 'lavc', '-lavcopts',
                  'vcodec=%s:vbitrate=%d' % (vcodec, vbitrate)]

        out = ['-o', self.tmp_filename]
        args = ['mencoder', '/dev/stdin', '-demuxer', 'rawvideo',
                '-rawvideo', 'w=%d:h=%d:fps=%f:format=%s' %
                (self.width, self.height, fps, format)] + ovc + out

                #'-v', "0", # verbosity level (1 prints stats \r)

        self.debug('$ %s' % " ".join(args))
        # Note: mp4 encoding is currently broken in mencoder :-(
        #       so we have to use ffmpeg as a second step.
        # These would be the options to add:
        #'-of', 'lavf', '-lavfopts', 'format=mp4'

        if self.config.quiet:
            # XXX /dev/null not portable
            self.process = subprocess.Popen(args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        else:
            self.process = subprocess.Popen(args=args,
                                            stdin=subprocess.PIPE)

        if self.config.timestamps:
            self.timestamps_filename = self.filename + '.timestamps'
            self.timestamps_file = open(self.timestamps_filename, 'w')

    def finish(self):
        if self.convert_to_mp4:
            self.debug('Converting %s to %s' %
                        (self.tmp_filename, self.filename))
            convert_to_mp4(self.tmp_filename, self.filename)

            if os.path.exists(self.tmp_filename):
                os.unlink(self.tmp_filename)
        else:
            os.rename(self.tmp_filename, self.filename)

        self.info('Finished %s' % (self.filename))

        # TODO: skip mp4
        if self.config.crop:
            base, ext = os.path.splitext(self.filename)
            cropped = '%s-crop%s' % (base, ext)
            video_crop(self.filename, cropped)
            os.unlink(self.filename)
            os.rename(cropped, self.filename)

    def cleanup(self):
        # TODO: remove timestamps
        if 'tmp_filename' in self.__dict__:
            if os.path.exists(self.tmp_filename):
                os.unlink(self.tmp_filename)

        self.cleanup_mencoder()

    def cleanup_mencoder(self):
        # Try to cleanup as well as possible
        if (not 'process' in self.__dict__) or self.process is None:
            return

        self.process.stdin.close()
        try:
            self.process.terminate()
            self.process.wait()
        except (OSError, AttributeError):
            # Exception AttributeError: AttributeError("'NoneType' object 
            # has no attribute 'SIGTERM'",) 
            # in <bound method RangefinderUniform.__del__ 
            # of RangefinderUniform> ignored
            # http://stackoverflow.com/questions/2572172/
            pass

    def write_value(self, timestamp, image):
        if self.image_shape is None:
            self.image_shape = image.shape

        if self.image_shape != image.shape:
            msg = ('The image has changed shape, from %s to %s.' %
                   (self.image_shape, image.shape))
            raise Exception(msg) # TODO: badinput
        # very important! make sure we are using a reasonable array
        if not image.flags['C_CONTIGUOUS']:
            image = numpy.ascontiguousarray(image)

        try:
            self.process.stdin.write(image.data)
            self.process.stdin.flush()
        except IOError as e: # broken pipe
            msg = 'Could not write data to mencoder: %s.' % e
            self.error(msg)
            msg += '\n' + indent(self.process.stdout.read(), 'stdout> ')
            msg += '\n' + indent(self.process.stderr.read(), 'stderr> ')
            raise Exception(msg)

        if self.config.timestamps:
            self.timestamps_file.write('%s\n' % timestamp)
            self.timestamps_file.flush()



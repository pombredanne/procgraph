import numpy as np
from procgraph import simple_block


@simple_block
def ros2python(msg):
    ''' Converts a ROS message to a Python object. '''
    # FIXME: this is a hack
#    print msg.__class__
#    if isinstance(msg, String):
#        return msg.data
#    else:
#        print('Unknown type: %s' % msg.__class__)
#        return msg

    return msg.data


@simple_block
def ros_scan2python(scan):
    #    print scan.__dict__.keys()
    return np.array(scan.ranges)
    
def rgb_from_imgmsg(image):
    im, _, _ = imgmsg_to_pil(image)
    pix = np.asarray(im).astype(np.uint8)
    return pix

# @PydevCodeAnalysisIgnore
# #Code from:
# http://nullege.com/codes/show/src%40c%40m%40cmu-ros-pkg-HEAD%40trunk%40posedetectiondb%40src%40ParseMessages.py/75/sensor_msgs.msg.Image/python
# 
 
import PIL.Image  # @UnresolvedImport
import numpy
import roslib  # @UnresolvedImport @UnusedImport
import rospy  # @UnresolvedImport @UnusedImport
import sensor_msgs.msg  # @UnresolvedImport
from sensor_msgs.msg import CompressedImage  # @UnusedImport @UnresolvedImport
import struct

@simple_block
def ros2rgb(msg):
    # print msg.__class__.__name__ # _sensor_msgs__CompressedImage
    if 'CompressedImage' in msg.__class__.__name__:
        # print 'format: %s' % msg.format
        # if msg.format == 'jpeg':
        #     data = msg.data
        #      
        #     from PIL import ImageFile  # @UnresolvedImport
        #     parser = ImageFile.Parser()
        #     parser.feed(data)
        #     res = parser.close()
        #     print res
        return rgb_from_pil(pil_from_CompressedImage(msg))
    else:
        return rgb_from_imgmsg(msg)

def pil_from_CompressedImage(msg):
    from PIL import ImageFile  # @UnresolvedImport
    parser = ImageFile.Parser()
    parser.feed(msg.data)
    res = parser.close()            
    return res 

def rgb_from_pil(im):
    return np.asarray(im).astype(np.uint8)


# Number of channels used by a PIL image mode
def imgmsg_to_pil(rosimage, encoding_to_mode={
        'mono8':     'L',
        '8UC1':      'L',
        '8UC3':      'RGB',
        'rgb8':       'RGB',
        'bgr8':       'RGB',
        'rgba8':      'RGBA',
        'bgra8':      'RGBA',
        'bayer_rggb': 'L',
        'bayer_gbrg': 'L',
        'bayer_grbg': 'L',
        'bayer_bggr': 'L',
        'yuv422':     'YCbCr',
        'yuv411':     'YCbCr'},
        PILmode_channels={ 'L' : 1, 'RGB' : 3, 'RGBA' : 4, 'YCbCr' : 3 }):
    conversion = 'B'
    channels = 1
    if rosimage.encoding.find('32FC') >= 0:
        conversion = 'f'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('64FC') >= 0:
        conversion = 'd'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('8SC') >= 0:
        conversion = 'b'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('8UC') >= 0:
        conversion = 'B'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('16UC') >= 0:
        conversion = 'H'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('16SC') >= 0:
        conversion = 'h'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('32UC') >= 0:
        conversion = 'I'
        channels = int(rosimage.encoding[-1])
    elif rosimage.encoding.find('32SC') >= 0:
        conversion = 'i'
        channels = int(rosimage.encoding[-1])
    else:
        if rosimage.encoding.find('rgb') >= 0 or rosimage.encoding.find('bgr') >= 0:
            channels = 3
  
    data = struct.unpack(('>' if rosimage.is_bigendian else '<') + '%d' % (rosimage.width * rosimage.height * channels) + conversion, rosimage.data)
  
    if conversion == 'f' or conversion == 'd':
        dimsizes = [rosimage.height, rosimage.width, channels]
        imagearr = numpy.array(255 * I, dtype=numpy.uint8)  # @UndefinedVariable
        im = PIL.Image.frombuffer('RGB' if channels == 3 else 'L', dimsizes[1::-1], imagearr.tostring(), 'raw', 'RGB', 0, 1)
        if channels == 3:
            im = PIL.Image.merge('RGB', im.split()[-1::-1])
        return im, data, dimsizes
    else:
        mode = encoding_to_mode[rosimage.encoding]
        step_size = PILmode_channels[mode]
        dimsizes = [rosimage.height, rosimage.width, step_size]
        im = PIL.Image.frombuffer(mode, dimsizes[1::-1], rosimage.data, 'raw', mode, 0, 1)
        if mode == 'RGB':
            im = PIL.Image.merge('RGB', im.split()[-1::-1])
        return im, data, dimsizes
  
def pil_to_imgmsg(image, encodingmap={'L': 'mono8', 'RGB': 'rgb8', 'RGBA': 'rgba8', 'YCbCr': 'yuv422'},
                        PILmode_channels={'L': 1, 'RGB': 3, 'RGBA': 4, 'YCbCr': 3}):
    rosimage = sensor_msgs.msg.Image()
    # adam print 'Channels image.mode: ',PILmode_channels[image.mode]
    rosimage.encoding = encodingmap[image.mode]
    (rosimage.width, rosimage.height) = image.size
    rosimage.step = PILmode_channels[image.mode] * rosimage.width
    rosimage.data = image.tostring()
    return rosimage
  
def numpy_to_imgmsg(image, stamp=None):
    rosimage = sensor_msgs.msg.Image()
    rosimage.height = image.shape[0]
    rosimage.width = image.shape[1]
    if image.dtype == numpy.uint8:
        rosimage.encoding = '8UC%d' % image.shape[2]
        rosimage.step = image.shape[2] * rosimage.width
        rosimage.data = image.ravel().tolist()
    else:
        rosimage.encoding = '32FC%d' % image.shape[2]
        rosimage.step = image.shape[2] * rosimage.width * 4
        rosimage.data = numpy.array(image.flat, dtype=numpy.float32).tostring()
    if stamp is not None:
        rosimage.header.stamp = stamp
    return rosimage

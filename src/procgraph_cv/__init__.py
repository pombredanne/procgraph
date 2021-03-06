''' 
    Blocks using the OpenCV library. 
'''


procgraph_info = {
    # List of python packages 
    'requires': [('cv2', ('cv2',))]
}


from procgraph import import_magic, import_succesful
cv = import_magic(__name__, 'cv2', 'cv')

from .opencv_utils import *
from .cv_capture import *
from .cv_display import *


if not import_succesful(cv):
    from procgraph import logger
    logger.warn('Could not import CV')


from procgraph import pg_add_this_package_models
pg_add_this_package_models(__file__, __package__)



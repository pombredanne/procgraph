''' Blocks for basic operations on images.

This package contains blocks that perform basic operations
on images. The library has no software dependency. 

For more complex operations see also :ref:`module:procgraph_cv` and 
:ref:`module:procgraph_pil`

**Example**

Convert a RGB image to grayscale, and back to a RGB image:::


    |input| -> |rgb2gray| -> |gray2rgb| -> |output| 

'''
 
import filters 
import compose 
import imggrid
import border
from blend import blend
from copied_from_reprep import posneg, scale


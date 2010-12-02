try:

    from PIL import Image, ImageDraw, ImageFont #@UnusedImport

except ImportError as e:
    # We believe only nose will import this
    import sys
    sys.stderr.write('procgraph_pil: Could not find the PIL module \n'
                     '  I will let you continue, but probably you will have \n'
                     '  other errors later on.\n')
    def warn():
        raise Exception('The PIL module was not found.')
    
    class warn_and_throw:
        def __getattr__(self, method_name):
            warn()            

    Image = warn_and_throw() 
    ImageDraw = warn_and_throw()
    ImageFont = warn_and_throw()
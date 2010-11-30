import sys, os, traceback 
from optparse import OptionParser

from procgraph.core.model_loader import model_from_string, pg_look_for_models
from procgraph.core.registrar import default_library, Library
from procgraph.core.exceptions import SemanticError, PGSyntaxError 
from procgraph.core.visualization import error, info


usage_short = \
"""Usage:    
        
    pg [options]  <model>.pg   [param=value  param=value ... ]
    
Type "pg --help" for all the options and a few examples.

"""
usage_long = \
"""Usage:    
        
    pg [options]  <model>.pg   [param=value  param=value ... ]
    
Examples:

1) Execute a model that does not need parameters:
    
    $ pg  my_model.pg

2) Execute a model, reading the a directory for additional models:

    $ pg -d my_models/  my_model.pg

   (Note that the current directory is not ready by default).    
   There is also an environment variable that has the same effect:

    $ export PROCGRAPH_PATH=my_models

3) Execute a model, but first load a module that might contain additional block
   definitions.

    $ pg -m my_blocks  my_model.pg 
"""
    
    

def main(): 
    parser = OptionParser(usage=usage_long)

    def load_module(option, opt_str, value, parser):
        info('Importing module %s' % value)
        __import__(value)
    
    additional_directories = []
    def add_directory(option,  opt_str, value, parser):
        additional_directories.append(value)
    
    parser.add_option("-m", dest="module",
                  action="callback", callback=load_module,
                  type="string", help='Loads the specified module')

    parser.add_option("-d",  dest='directory', type="string",
                      action="callback", callback=add_directory, 
                      help='Additional directory to search for models.')

    parser.add_option("--debug", action="store_true",
                      default=False, dest="debug",
                      help="Displays debug information on the model.")
    
    parser.add_option("--stats", action="store_true",
                      default=False, dest="stats",
                      help="Displays execution statistics, including CPU usage.")
    
    parser.add_option("--nocache", action="store_true",
                      default=False, dest="nocache",
                      help="Ignores the parsing cache.")
    
    
    (options, args) = parser.parse_args()
    
    
    if not args:
        print usage_short
        
        #print "Known models: %s" % \
        #    ", ".join(sorted(default_library.get_known_blocks()))
        sys.exit(-1) 
    
    
    filename = args.pop(0)
        
    config = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=')
            try:
                value = float(value)
            except:
                try: 
                    value = int(value)
                except:
                    pass
            config[key] = value            
        else:
            raise Exception('What should I do with "%s"?' % arg)
    
    if options.debug:
        print "Configuration: %s" % config

    pg(filename, config,
       nocache=options.nocache, debug=options.debug, stats=options.stats,
       additional_directories=additional_directories)
            

def pg(filename, config, 
       debug=False, nocache=False, stats=False,
       additional_directories=[]):
    ''' Instantiate and run a model. 
    
    Instantiate a model (filename can be either a file or a known model. '''
    
    try:
        library = Library(default_library)
        pg_look_for_models(library, ignore_cache=nocache,
                           additional_paths=additional_directories)
        
        # load standard components
        import procgraph.components #@UnusedImport

        if library.exists(block_type=filename):
#            w = Where('command line', filename, 0)
            model = library.instance(filename, name=None,
                                             config=config)
        else:
            if not os.path.exists(filename):
                raise Exception('Unknown model or file "%s".' % filename)

            model_spec = open(filename).read()
            model = model_from_string(model_spec, config=config,
                                      filename=filename, library=library)
        
        if debug:
            model.summary()
            return

        count = 0
        model.reset_execution()
        while model.has_more():       
            model.update()
            
            if stats:
                count += 1
                if count % 500 == 0:
                    model.stats.print_info()
        
        # XXX: it should know by itself
        model.finish()
                
    #except ModelExecutionError as e:
    #    print e
    #    traceback.print_exc()    
        
    except SemanticError as e:    
        error(e)
        if e.element is not None:
            where = e.element.where
            if where is None:
                raise Exception("%s does not have where?" % e.element)
            
            s = str(where)
            error(s)
            
        raise Exception('Semantic error')
    except PGSyntaxError as e:    
        error(e)
        error(str(e.where))
        raise Exception('Syntax error')
            
    #return model

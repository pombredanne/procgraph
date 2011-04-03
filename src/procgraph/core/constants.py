''' 
    All the arbitrary constants used by ProcGraph.


    Note that some of these come from prototypes, and I should get rid of them.

    Also some are configuration parameters which should be settable in some way.
    
'''


# If true, consider an error if a model's input is not defined formally.
STRICT_CHECK_OF_DEFINED_IO = False


STRICT = True

### For the procgraph_info  dictionary:

# Variable that should be defined 
PROCGRAPH_INFO_VARIABLE = 'procgraph_info'  
# Which variable holds the dependencies
REQUIRES = 'requires'
# Key for the "parsed" version of REQUIRES (used internally)
REQUIRES_PARSED = 'requires_parsed'
    

### Types of inputs and outputs

# Normal input/output
FIXED = 'fixed-signal'
# Variable number of inputs/outputs.
VARIABLE = 'variable-signal'
# The block will define the signals *after* it has seen the configuration. 
DEFINED_AT_RUNTIME = 'defined-at-runtime'

### When defining simple blocks
# TODO: write documentation on how these work
COMPULSORY = 'compulsory-param'
TIMESTAMP = 'timestamp-param'


# not sure this is used anywhere now
ETERNITY = 0

### Environment

# Environment variable containing colon-separated additional paths to look
# for modules.
PATH_ENV_VAR = 'PROCGRAPH_PATH'



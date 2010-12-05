from procgraph import Block, COMPULSORY, register_simple_block


# Make it generic?
class Extract(Block):
    ''' 
    This block extracts some of the components of a vector.
    
    '''
    Block.alias('extract')
    Block.input('vector')
    Block.output('part')
    Block.config('index') 

    def update(self):
        index = self.config.index
        vector = self.input.vector
        
        part = vector[index]
        
        self.output.part = part
         
         
def slice(signal, start, end):
    ''' Slices a signal by extracting from index ``start`` to index ``end`` (INCLUSIVE).'''
    return signal[start:(end + 1)]

    
register_simple_block(slice, 'slice', params={'start':COMPULSORY, 'end':COMPULSORY})

    
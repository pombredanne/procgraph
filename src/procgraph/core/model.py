import time

from .exceptions import SemanticError, ModelExecutionError, ModelWriterError
from .block import Block, Generator
from .model_io import ModelInput, ModelOutput
from .model_stats import ExecutionStats
from .visualization import debug as debug_main, info, warning
from .constants import STRICT_CHECK_OF_DEFINED_IO


class BlockConnection:
    def __init__(self, block1, block1_signal, block2, block2_signal,
                       public_name=None):
        assert isinstance(block1, Block)
        assert block1_signal is not None
        assert block2 is None or isinstance(block2, Block)
        
        self.block1 = block1
        self.block1_signal = block1_signal
        self.block2 = block2
        self.block2_signal = block2_signal
        self.public_name = public_name
        
    def __repr__(self):
        s = 'Connection(' 
        s += self.block1.name
        s += '.%s' % self.block1_signal 
        
        s += ' --> '
        if self.block2:
            s += self.block2.name
            s += '.%s' % self.block2_signal 
        else:
            s += '?.?'
        s += ')'
            
        return s
    

class Model(Generator):
    ''' A Model is a block and a generator. '''
    
    def __init__(self, name, model_name):
        ''' Name is the personal name of this instance.
            model_name is this model's name.
            
            model_name is used for visualization and serialization
            config is usef only for serialization.
             '''
        if name is None:
            name = 'unnamed-block'
        assert isinstance(name, str)
        
        if model_name is None:
            model_name = 'unnamed-model'
        assert isinstance(model_name, str)        

        self.model_name = model_name
    
        # As a block
        Block.__init__(self, name=name, config={}, library=None)
        
        self.name2block = {}
        self.name2block_connection = {}
        # block -> block unresolved 
        self.unresolved = {}
        
        # list of blocks that act as generators (instance of Generator)
        self.generators = []
        
        self.reset_execution()
        
        # hash signal name -> Block for blocks of type ModelInput
        self.model_input_ports = {} 
        
        
        self.stats = ExecutionStats()
    
        self._already_inited = False 
        
        self.level = 0
         
    def add_block(self, name, block):
        '''  Add a block to the model.
            Returns the block instance. '''
        assert not name in self.name2block, 'Name %r already taken' % name
        
        self.name2block[name] = block
        
        if isinstance(block, Generator):
            self.generators.append(block)
            
        if isinstance(block, ModelInput):
            block.init() # get the name from config
            if not self.is_valid_input_name(block.signal_name):
                msg = 'Input %r was not defined formally.' % block.signal_name
                if STRICT_CHECK_OF_DEFINED_IO:
                    raise SemanticError(msg, block)
                else:
                    warning("Warning: %s" % msg)
                    
                if self.are_input_signals_defined():
                    all_inputs = self.get_input_signals_names()
                else: 
                    all_inputs = [] 
                            
                self.define_input_signals_new(all_inputs + [block.signal_name])
                
                
            self.model_input_ports[block.signal_name] = block
        
        if isinstance(block, ModelOutput):
            block.init() # get the name from config
            
            if not self.is_valid_output_name(block.signal_name):
                msg = 'Output %r was not defined formally.' % block.signal_name
                if STRICT_CHECK_OF_DEFINED_IO:
                    raise SemanticError(msg, block)
                else:
                    warning("Warning: %s" % msg)
            
                if self.are_output_signals_defined():
                    all_outputs = self.get_output_signals_names()
                else: 
                    all_outputs = [] 
                    
                # XXX bug: output_signals -> output_signals
                self.define_output_signals_new(all_outputs + [block.signal_name])
        
        return block
    
    def from_outside_set_input(self, num_or_id, value, timestamp):
        assert self._already_inited, 'The block must first be init()ed.' 
        Block.from_outside_set_input(self, num_or_id, value, timestamp)
        
        signal_name = self.canonicalize_input(num_or_id)
        input_block = self.model_input_ports[signal_name]
        input_block.set_output(signal_name, value, timestamp)
        self.blocks_to_update.append(input_block)
    
    def connect(self,
                block1, block1_signal,
                block2, block2_signal,
                public_name):
        ''' Caller should check that the public name is not taken. '''
        assert public_name is not None
        assert not public_name in self.public_signal_names(), \
            "%r is already taken" % public_name
        
        BC = BlockConnection(block1, block1_signal, block2, block2_signal,
                             public_name)
    
        self.name2block_connection[public_name] = BC

    def public_signal_names(self):
        ''' Returns the set of public signal names. '''
        return set(self.name2block_connection.keys())

    def next_data_status(self):
        ''' XXX OK, I'm writing this late and probably it's more 
            complicated than this. '''  
        generator_timestamps = []
        at_least_one = False
        for generator in self.generators:
            status = generator.next_data_status() 
            (has_next, timestamp) = status #@UnusedVariable
            if has_next:
                at_least_one = True
                if timestamp is not None:
                    generator_timestamps.append(timestamp)
        
        if not at_least_one:
            return (False, None)
        elif not generator_timestamps:
            return (True, None)
        else:
            return (True, min(generator_timestamps))
            

    def has_more(self):
        """ Returns true if there are blocks with pending updates,
            or there is at least one generator that has not ended. """
        if self.blocks_to_update:
            return True
        
        for generator in self.generators:
            status = generator.next_data_status() #@UnusedVariable
            
            if not isinstance(status, tuple) or len(status) != 2:
                msg = ('next_data_status() should return a tuple of len 2, '
                       ' not %r.' % status)
                raise ModelWriterError(msg, generator)
            (has_next, timestamp) = status #@UnusedVariable
            if has_next:
                return True
            
        return False
    
    def reset_execution(self):
        self.blocks_to_update = []
        # FIXME XXX it's late
        # add all the blocks without input to the update list
        for block in self.name2block.values():
#            self.debug('Considering %s' % block)
            if isinstance(block, Model):
                if block.blocks_to_update:
                    self.blocks_to_update.append(block)
                pass
            elif (not isinstance(block, ModelInput) and
                not isinstance(block, Generator) and
                block.num_input_signals() == 0):
                self.blocks_to_update.append(block)
#                self.debug(' --> adding %s' % block)
                # XXX: no, without input they should be generators??? maybe
            else:
                pass
#                self.debug(' --> NOT adding %s' % block)

#        self.debug('I need update: %s' % self.blocks_to_update)

    
    def init(self):
        assert not self._already_inited, 'The block has already been init()ed.'
        self._already_inited = True
        for block in self.name2block.values():
            block.level = self.level + 1
            block.init()
        self.reset_execution()
                        
    def finish(self):
        for block in self.name2block.values():
            block.finish() 

    def update(self):
        def debug(s):
            if False:
                debug_main('Model %s | %s' % (self.model_name, s))
        
        # We keep a list of blocks to be updated.
        # If the list is not empty, then pop one and update it.
        if self.blocks_to_update:
            # get one block
            block = self.blocks_to_update.pop(0)
            
            debug('Got block to update %s' % block)
            
        else:
            debug('No blocks to update')
            
            # look if we have any generators
            # list of (generator, timestamp) 
            generators_with_timestamps = [] 
            for generator in self.generators:
                (has_next, timestamp) = generator.next_data_status()
                if has_next:
                    generators_with_timestamps.append((generator, timestamp))
        
            if not generators_with_timestamps:
                msg = "You asked me to update but nothing's left."
                raise ModelExecutionError(msg, self)
               
            # now look for the smallest available timestamp
            # (timestamp can be none)
            def cmp(timestamp1, timestamp2):
                if timestamp1 is None:
                    return 1
                elif timestamp2 is None:
                    return - 1
                elif timestamp1 < timestamp2:
                    return - 1
                elif timestamp2 < timestamp1:
                    return 1
                else:
                    return 0
                
            generators_with_timestamps.sort(key=lambda x:x[1], cmp=cmp)
            
            block = generators_with_timestamps[0][0]
        
        if block is None:
            # We finished everything
            msg = "You asked me to update but nothing's left."
            raise ModelExecutionError(msg, self)
            
        # now we have a block (could be a generator)
        debug('Updating %s (input ts: %s)' % 
              (block, block.get_input_signals_timestamps()))
        
        # We also time the execution
        start_cpu = time.clock()
        start_wall = time.time()
        
        result = block.update()
        
        cpu = time.clock() - start_cpu
        wall = time.time() - start_wall

        if block.get_input_signals_timestamps():
            timestamp = max(block.get_input_signals_timestamps())
        elif block.get_output_signals_timestamps():
            timestamp = max(block.get_output_signals_timestamps())
        else: # for those that don't have input signals
            timestamp = 0.001
            
        self.stats.add(block=block, cpu=cpu, wall=wall,
                       timestamp=timestamp)
        
        # if the update is not finished, we put it back in the queue
        if result == block.UPDATE_NOT_FINISHED:
            self.blocks_to_update.insert(0, block)
        else:
            # the block updated, propagate
            debug("  processed %s, ts: %s" % 
                  (block, block.get_output_signals_timestamps()))
            debug("  its successors: %s" % 
                  list(self.__get_output_connections(block)))
            # check if the output signals were updated
            for connection in self.__get_output_connections(block):
                other = connection.block2
                if other is None:
                    # XXX don't include dummy connection
                    debug(" ignoring connection %s" % connection)
                    continue
                other_signal = connection.block2_signal
                old_timestamp = other.get_input_timestamp(other_signal)
                this_signal = connection.block1_signal
                this_timestamp = block.get_output_timestamp(this_signal)
                                
                value = block.get_output(this_signal)

                # FIXME: make another condition
                if value is not None and this_timestamp is None:
                    msg = ('Strange, value is not None but the timestamp is 0' 
                          ' for output signal %r of block %s.' % 
                            (block.canonicalize_output(this_signal), block)) 
                    raise ModelExecutionError(msg, block)
                
                # Two cases:
                # - timestamp is updated
                # NOOOOOOO - this is the first time
                #  WRONG think of the |wait| block
                if this_timestamp > old_timestamp: 
                # or other.get_input(other_signal) is None:
                    #print "updating input %s of %s with timestamp %s" % \
                    #    (other_signal, other, this_timestamp)
                    
                    debug('  then waking up %s' % other) 
                    
                    other.from_outside_set_input(other_signal, value,
                                                 this_timestamp)
                    
                    if not other in self.blocks_to_update:
                        self.blocks_to_update.append(other)
                    
                    # If this is an output port, update the model
                    if isinstance(other, ModelOutput):
                        #print "Updating output %s" %  other.signal_name
                        self.set_output(other.signal_name,
                                        value, this_timestamp)
                else:
                    debug("  Not updated %s because not %s > %s." % 
                           (other, this_timestamp, old_timestamp))
        
        # now let's see if we have still work to do
        # this step is important when the model is inside another one
        if self.blocks_to_update:
            # XXX should I count the generators here?
            return Block.UPDATE_NOT_FINISHED
        else:
            return True
            
    def __get_output_connections(self, block):
        for block_connection in self.name2block_connection.values():
            if block_connection.block1 == block:
                yield block_connection
                
    def __get_successors(self, block):
        ''' Returns an iterable of all the blocks connected
            to one of the outputs of the given block. '''
        successors = set()
        for block_connection in self.name2block_connection.values():
            if block_connection.block1 == block:
                successors.add(block_connection.block2)
        return successors
    
    
    def __repr__(self):
        s = 'M:%s:%s(' % (self.model_name, self.name)
        s += self.get_io_repr()
        s += ')'
        return s
    
    def summary(self):
        info("--- Model: %d blocks, %d connections" % 
            (len(self.name2block), len(self.name2block_connection)))
        for name, block in self.name2block.items():
            info("- %s: %s" % (name, block))
            
        for name, conn in self.name2block_connection.items():
            info("- %s: %s" % (name, conn)) 



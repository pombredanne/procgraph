from procgraph.testing.utils import PGTestCase
from tempfile import NamedTemporaryFile
from procgraph.core.block import Block
from procgraph.core.model_loader import model_from_string
import pickle
from procgraph.core.registrar import default_library

class HasState(Block):
    ''' A simple block for debugging purposes 
       that puts the config "x" in the state "x". '''
    def init(self):
        # default value
        self.config.x = 42
        
        self.state.x = self.config.x
        
        self.define_input_signals([])
        self.define_output_signals(['x'])

    def update(self):
        self.set_output(0, self.state.x + 1, timestamp=1)

default_library.register('has_state', HasState)




class TestSaving(PGTestCase):
    
    def test_saving(self):
        
        # generate temporary file
        file1 = NamedTemporaryFile(suffix='file1.pickle')
        file2 = NamedTemporaryFile(suffix='file2.pickle')
        file3 = NamedTemporaryFile(suffix='file3.pickle')
        
        model_spec = '''
        --- model testing_saving
        
        |has_state x=1| --> Y
        
        on init:   load has_state.x from $file1 as pickle 
        on finish: save has_state.x  to  $file2 as pickle
        on finish: save Y  to  $file3 as pickle
        
        '''
        value = 43
        pickle.dump(value, file1)
        file1.flush()
        
        config = {'file1': file1.name, 'file2': file2.name, 'file3': file3.name}
        model = model_from_string(model_spec, config=config)
        
        
        model.reset_execution()
        while model.has_more():       
            model.update()
        model.finish()
        
        value2 = pickle.load(open(file2.name))
        self.assertEqual(value, value2)

        value3 = pickle.load(open(file3.name))
        self.assertEqual(value + 1, value3)
        
        
        # should be like this
        if False:
            model.init()
            while model.update() == model.UPDATE_NOT_FINISHED:       
                pass
            model.finish()
            
        
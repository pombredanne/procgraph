from procgraph import Block
import os
from procgraph.utils import safe_pickle_load, safe_pickle_dump
import warnings

warnings.warn('remove below dipendence on boot_agents')

__all__ = ['CovarianceRemember']


class CovarianceRemember(Block):
    """ Quick hack to remember covariance across executions """
    Block.alias('covariance_rem')
    
    Block.config('filename', default='cov_remember.pickle') 
    Block.input('x')
    Block.output('cov_x')
    
    def init(self):
        filename = self.config.filename
        if os.path.exists(filename):
            self.info('Loading state from filename %r' % filename)
            self.state = safe_pickle_load(filename)
        else:
            from boot_agents.utils.mean_covariance import MeanCovariance
            self.state = MeanCovariance()
    
    def update(self):
        x = self.input.x.astype('float32')
        self.state.update(x)
        
        self.output.cov_x = self.state.get_covariance()
        safe_pickle_dump(self.state, self.config.filename)  # @UndefinedVariable

from procgraph import Generator, Block


class Clock(Generator):
    Block.alias('clock')
    Block.config('interval', 'Delta between ticks.', default=1)
    Block.output('clock', 'Clock signal.')

    def init(self):
        self.state.clock = 0

    def update(self):
        self.set_output('clock', self.state.clock, timestamp=self.state.clock)
        self.state.clock += self.config.interval

    def next_data_status(self):
        return (True, self.state.clock + self.config.interval)



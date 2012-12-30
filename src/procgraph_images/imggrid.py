from numpy import ceil, sqrt, zeros

from procgraph import Block, BadConfig
from procgraph.block_utils import check_rgb_or_grayscale

from .compose import place_at  # XXX:
from procgraph_images.border import image_border


class ImageGrid(Block):
    ''' A block that creates a larger image by arranging them in a grid. '''

    Block.alias('grid')

    Block.config('cols', 'Columns in the grid.', default=None)
    Block.config('bgcolor', 'Background color.', default=[0, 0, 0])

    Block.config('pad', 'Padding for each cell', default=0)
    Block.input_is_variable('Images to arrange in a grid.', min=1)
    Block.output('grid', 'Images arranged in a grid.')

    def update(self):
        n = self.num_input_signals()
        for i in range(n):
            if self.get_input(i) is None:
                # we only go if everything is ready
                return
            check_rgb_or_grayscale(self, i)

        cols = self.config.cols

        if cols is None:
            cols = int(ceil(sqrt(n)))

        if not isinstance(cols, int):
            raise BadConfig('Expected an integer.', self, 'cols')

        rows = int(ceil(n * 1.0 / cols))

        assert cols > 0 and rows > 0
        assert n <= cols * rows

        # find width and height for the grid 
        col_width = zeros(cols, dtype='int32')
        row_height = zeros(rows, dtype='int32')
        for i in range(n):
            col = i % cols
            row = (i - i % cols) / cols
            assert 0 <= col < cols
            assert 0 <= row < rows

            image = self.get_input(i)
            p = self.config.pad 
            if p is not None:
                image = image_border(image,
                           left=p,
                           right=p,
                           top=p,
                           bottom=p,
                           color=self.config.bgcolor)
            width = image.shape[1]
            height = image.shape[0]

            col_width[col] = max(width, col_width[col])
            row_height[row] = max(height, row_height[row])

        canvas_width = sum(col_width)
        canvas_height = sum(row_height)

        # find position for each col and row
        col_x = zeros(cols, dtype='int32')
        for col in range(1, cols):
            col_x[col] = col_x[col - 1] + col_width[col - 1]

        assert(canvas_width == col_x[-1] + col_width[-1])

        row_y = zeros(rows, dtype='int32')
        for row in range(1, rows):
            row_y[row] = row_y[row - 1] + row_height[row - 1]
        assert(canvas_height == row_y[-1] + row_height[-1])

        canvas = zeros((canvas_height, canvas_width, 3), dtype='uint8')
        for k in range(3):
            canvas[:, :, k] = self.config.bgcolor[k] * 255

        for i in range(n):
            col = i % cols
            row = (i - i % cols) / cols
            assert 0 <= col < cols
            assert 0 <= row < rows
            image = self.get_input(i)
            x = col_x[col]
            y = row_y[row]
            
            # Pad if not right shape
            extra_hor = col_width[col] - image.shape[1]
            extra_ver = row_height[row] - image.shape[0]
            eleft = extra_hor / 2
            eright = extra_hor - eleft
            etop = extra_ver / 2
            ebottom = extra_ver - etop
            image = image_border(image, left=eleft, right=eright, top=etop,
                                 bottom=ebottom, color=self.config.bgcolor)
            
            # TODO: align here
            place_at(canvas, image, x, y)

        self.set_output(0, canvas)




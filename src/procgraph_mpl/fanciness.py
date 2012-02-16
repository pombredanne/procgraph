
# str -> function f(pyplot)
fancy_styles = {}


def style(f):
    fancy_styles[f.__name__] = f


@style
def dickinsonA(pylab):
    set_spines_look_A(pylab)


def remove_spine(pylab, which):
    ax = pylab.gca()
    ax.spines[which].set_color('none')


@style
def notopaxis(pylab):
    remove_spine(pylab, 'top')


@style
def nobottomaxis(pylab):
    remove_spine(pylab, 'bottom')


@style
def noxticks(pylab):
    pylab.xticks([], [])


@style
def noyticks(pylab):
    pylab.yticks([], [])


def set_spines_look_A(pylab, outward_offset=10,
                      linewidth=2, markersize=3, markeredgewidth=1):
    ''' 
        Taken from 
        http://matplotlib.sourceforge.net/examples/pylab_examples
        /spine_placement_demo.html
    '''

    ax = pylab.gca()
    for loc, spine in ax.spines.iteritems():
        if loc in ['left', 'bottom']:
            spine.set_position(('outward', outward_offset))
        elif loc in ['right', 'top']:
            spine.set_color('none') # don't draw spine
        else:
            raise ValueError('unknown spine location: %s' % loc)

    # turn off ticks where there is no spine
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')

    for l in ax.get_xticklines() + ax.get_yticklines():
        l.set_markersize(markersize)
        l.set_markeredgewidth(markeredgewidth)

    ax.get_frame().set_linewidth(linewidth)




from pyparsing import Regex, Word, delimitedList, alphas, Optional, OneOrMore, \
    stringEnd, alphanums, ZeroOrMore, Group, Suppress, lineEnd, \
    ParserElement, Combine, nums, Literal, CaselessLiteral, \
    restOfLine, QuotedString, ParseException, Forward 

from .parsing_elements import VariableReference, ParsedBlock, \
    ParsedAssignment, ImportStatement, ParsedModel, ParsedSignal, \
    ParsedSignalList, Connection, Where, \
 output_from_tokens, input_from_tokens, config_from_tokens
from .exceptions import PGSyntaxError


def eval_dictionary(s, loc, tokens): #@UnusedVariable
    #print "Dict Tokens: %s" % tokens
    if not 'content' in tokens:
        return {}
    d = {}
    for a in tokens:
        #print "A: %s" % a
        if 'value' in a:
            d[a['key']] = a['value']
            #print 'Dict got %s = %s (%r)' % (a['key'],
            #                                 a['value'].__class__.__name__, a['value'])
    
    return d 

def eval_value(s, loc, tokens): #@UnusedVariable
    # print 'value got tokens %s = %r' % (tokens.__class__.__name__, tokens)

    #res = tokens.asList()
    
    res = tokens
    
    # print ' -> value returns %s = %r ' % (res.__class__.__name__, res)
    return res

def eval_array(s, loc, tokens): #@UnusedVariable
    #print 'array got tokens %s = %r' % (tokens.__class__.__name__, tokens)

    elements = tokens.asList()
    # print 'array got elements %s = %r' % (elements.__class__.__name__, elements)
    res = []
    for i in range(len(elements)):
        t = elements[i]
        #print '  #%d is %s = %r' % (i, t.__class__.__name__, t)
        res.append(t)
        
    #print '-> Array is returning %s = %r' % (res.__class__.__name__, res)
    return res

def python_interpretation(s, loc, tokens): #@UnusedVariable
    val = eval(tokens[0]) # XXX why 0?
    return val

# Shortcuts
S = Suppress
O = Optional


# Important: should be at the beginning
# make end of lines count
ParserElement.setDefaultWhitespaceChars(" \t") 
    
# These are just values
# Definition of numbers
number = Word(nums) 
point = Literal('.')
e = CaselessLiteral('E')
plusorminus = Literal('+') | Literal('-')
integer = Combine(Optional(plusorminus) + number)
floatnumber = Combine(integer + 
                   Optional(point + Optional(number)) + 
                   Optional(e + integer)
                 )
integer.setParseAction(python_interpretation)
floatnumber.setParseAction(python_interpretation)
# comments
comment = Suppress(Literal('#') + restOfLine)
good_name = Combine(Word(alphas) + Optional(Word(alphanums + '_')))

# All kinds of python strings

single_quoted = QuotedString('"', '\\', unquoteResults=True) | \
                 QuotedString("'", '\\', unquoteResults=True) 
multi_quoted = QuotedString(quoteChar='"""', escChar='\\',
                              multiline=True, unquoteResults=True) | \
                 QuotedString(quoteChar="'''", escChar='\\',
                              multiline=True, unquoteResults=True)
quoted = multi_quoted | single_quoted 

reference = Combine(Suppress('$') + good_name('variable'))

reference.setParseAction(VariableReference.from_tokens)

dictionary = Forward()
array = Forward()
value = Forward()
value << (quoted ^ 
          array ^ 
          dictionary ^ 
          reference ^ 
          good_name ^ 
          integer ^ 
          floatnumber
         )('val')
#value << (
#          quoted | 
#          array | 
#          dictionary | 
#          reference | 
#          good_name | 
#          integer | 
#          floatnumber
#         )('val')
#value.setParseAction(eval_value)

# dictionaries
    
    
dict_key = good_name | quoted
dictionary << (Suppress("{") + \
    Optional(\
             delimitedList(\
                           Group(\
                                 dict_key('key') + Suppress(':') + value('value')\
                                 ) \
                           ) \
             )('content') + \
    Suppress("}"))
    
    
dictionary.setParseAction(eval_dictionary)
     
array << Group(Suppress("[") + O(delimitedList(value)('elements')) + Suppress("]"))

array.setParseAction(eval_array)

def parse_value(string):
    ''' This is useful for debugging '''
    # XXX this is a mess that needs cleaning
    # perhaps now it works without ceremonies
    try:
        #print '-- parse_value string: %r ' % string
        ret_value = value.parseString(string)
        #print '-- parse_value ret_value: %s = %r ' % (ret_value.__class__, ret_value)
        if isinstance(ret_value['val'], dict) or\
           isinstance(ret_value['val'], int) or\
           isinstance(ret_value['val'], list) or\
           isinstance(ret_value['val'], float):
            ret = ret_value['val']
        else:
            ret = ret_value['val'].asList()
        
        return ret
#        print "Parsed '%s' into %s (%d), ret: %s" % (string, tokens, len(tokens),
#                                                     ret)
#        return ret


    except ParseException as e:
        raise SyntaxError('Error in parsing string: %s' % e)
        

def create_model_grammar():
    # TODO: right now we have to recreate the grammar every time
    # We pass a "where" object to the constructors
    def wrap(constructor):
        def from_tokens(string, location, tokens):
            element = constructor(tokens)
            element.where = Where(ParsedModel.static_filename, string, location)
            return element 
        return from_tokens
        
      
    arrow = S(Regex(r'-+>'))
    
    # (don't put '.' at the beginning)
    # good_name =  Combine(Word(alphas) + Word(alphanums +'_' ))
    
    qualified_name = Combine(good_name + '.' + (integer | good_name))
    
    block_name = good_name 
    block_type = good_name | Word('_+-/*') | quoted | reference
     
    signal = O(S('[') + (integer | good_name)('local_input') + S(']')) \
            + O(block_name('block_name') + S(".")) + (integer | good_name)('name') + \
            O(S('[') + (integer | good_name)('local_output') + S(']'))
    signal.setParseAction(wrap(ParsedSignal.from_tokens))
    
    signals = delimitedList(signal)
    signals.setParseAction(wrap(ParsedSignalList.from_tokens))
    
    # Note that here the order matters (as qualified = good + something)
    key = qualified_name | good_name 
    
    key_value_pair = Group(key("key") + S('=') + value("value"))
    # old syntax
    # parameter_list = delimitedList(key_value_pair) ^ OneOrMore(key_value_pair) 
    parameter_list = OneOrMore(key_value_pair)
    parameter_list.setParseAction(
        lambda s, l, t: dict([(a[0], a[1]) for a in t ])) #@UnusedVariable
    
    block = S("|") + O(block_name("name") + S(":")) + block_type("blocktype") + \
         O(parameter_list("config")) + S("|")
    
    block.setParseAction(wrap(ParsedBlock.from_tokens)) 
    
    between = arrow + O(signals + arrow)
    
    # Different patterns
    arrow_arrow = signals + arrow + \
                  O(block + ZeroOrMore(between + block)) \
                  + arrow + signals
    source = block + ZeroOrMore(between + block) + arrow + signals
    sink = signals + arrow + block + ZeroOrMore(between + block)  
    source_sink = block + ZeroOrMore(between + block)
    
    # all of those are colled a connection
    # connection = arrow_arrow | sink | (source_sink ^ source)
    connection = arrow_arrow | sink | source | source_sink
      
    connection.setParseAction(wrap(Connection.from_tokens))
    
    # allow breaking lines with backslash
    continuation = '\\' + lineEnd
    # continuation = Regex('\\\w*\n')
    connection.ignore(continuation)
    
    assignment = (key("key") + S('=') + value("value"))
    assignment.setParseAction(wrap(ParsedAssignment.from_tokens)) 
    
    package_name = good_name + ZeroOrMore('.' + good_name)
    import_statement = S('import') + package_name('package')
    import_statement.setParseAction(wrap(ImportStatement.from_tokens))
     
    config = S('config') + good_name('variable') + O(S('=') + value('default')) + \
        O(quoted('docstring'))
    config.setParseAction(wrap(config_from_tokens))
    
    input = S('input') + good_name('name') + O(quoted('docstring'))
    input.setParseAction(wrap(input_from_tokens))

    output = S('output') + good_name('name') + O(quoted('docstring'))
    output.setParseAction(wrap(output_from_tokens))
    
    newline = S(lineEnd)
     
    docs = S(ZeroOrMore(multi_quoted + OneOrMore(newline)))
    
    action = \
        comment | \
        config | \
        input | \
        output | \
        (docs + connection) | \
        (docs + assignment) | \
        (docs + import_statement)
              
    
    model_content = ZeroOrMore(newline) + action + \
                    ZeroOrMore(OneOrMore(newline) + action) + \
                    ZeroOrMore(newline) 
    
    named_model = \
        Suppress(Combine('---' + Optional(Word('-')))) + Suppress('model') + \
        good_name('model_name') + OneOrMore(newline) + \
        O(quoted('docstring')) + \
        model_content('content')
        
    named_model.setParseAction(wrap(ParsedModel.from_named_model))
    
    anonymous_model = model_content.copy()
    anonymous_model.setParseAction(wrap(ParsedModel.from_anonymous_model))
    
    comments = ZeroOrMore((comment + newline) | newline)
    pg_file = comments + (OneOrMore(named_model) | anonymous_model) + \
        stringEnd 

    return pg_file

pg_file = create_model_grammar()
    
def parse_model(string, filename=None):
    ''' Returns a list of ParsedModel ''' 
    # make this check a special case, otherwise it's hard to debug
    if not string.strip():
        raise PGSyntaxError('Passed empty string.', Where(filename, string, 0))
    
    #  this is not threadsafe (but we don't have threads, so it's all good) 
    ParsedModel.static_filename = filename
    
    try:
        parsed = pg_file.parseString(string)

        return list(parsed)
    except ParseException as e:
        where = Where(filename, string, line=e.lineno, column=e.col)
        raise PGSyntaxError('Error in parsing string: %s' % e, where=where)
    
        

# no dragging CONSTS here for now

'''
currently for validating user input
'''

def positive_int(value: int|float|str, above: int=0, below: int=None):
    '''clamps a value to an int, above is minimum, below is maximum, both inclusive'''
    value = max(abs(int(value)), above)
    if below is not None:
        value = min(value, below)
    return value
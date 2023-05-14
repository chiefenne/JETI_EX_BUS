
def cycler(list):
    '''Cylce through a list inifinitely.
    Create a generator object which can be used to cycle through a list
    Usage:
        cycle_generator = cycler(list)
        next(cycle_generator)
    Args:
        list: Any list which should be cycled
    Yields:
        Next element in the list
    '''
    while list:
        for element in list:
            yield element

class lazy_attribute(object):
    def __init__(self, func):
        self._func = func
        self._value_name = "_" + func.__name__

    def __get__(self, obj, objtype=None):
        try:
            value = getattr(obj, self._value_name) 
        except AttributeError:
            value = self._func(obj)
            setattr(obj, self._value_name, value)
        return value

    def __set__(self, obj, new_value):
        assert(new_value == None)
        setattr(obj, self._value_name, None)





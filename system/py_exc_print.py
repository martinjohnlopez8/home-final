# Note that when we're loaded into gdb via `source py_exc_print.py`, we
# seem to be loaded into the same namespace as the Python debugging
# extension, which is some version of the following file by David Malcolm:
#
# https://hg.python.org/cpython/file/2.7/Tools/gdb/libpython.py

def pm_sys_exc_info():
    '''Just like sys.exc_info(), but post-mortem!'''

    # The _PyThreadState_Current global is defined in:
    # https://hg.python.org/cpython/file/tip/Python/pystate.c
    val = gdb.lookup_symbol('_PyThreadState_Current')[0].value()

    # The PyThreadState type is defined in:
    # https://hg.python.org/cpython/file/tip/Include/pystate.h
    return [PyTracebackObjectPtr.from_pyobject_ptr(val[name])
            for name in ['exc_type', 'exc_value', 'exc_traceback']]

def pm_traceback_print_exc():
    '''Kinda like traceback.print_exc(), but post-mortem, and no args!'''

    exc_type, exc_value, exc_traceback = pm_sys_exc_info()

    sys.stdout.write('Traceback (most recent call last):\n')

    while not exc_traceback.is_null():
        frame = exc_traceback.get_frame()
        sys.stdout.write('  %s\n' % frame.get_truncated_repr(MAX_OUTPUT_LEN))
        exc_traceback = exc_traceback.get_next()

    exc_value.write_repr(sys.stdout, set())
    sys.stdout.write('\n')

class PyTracebackObjectPtr(PyObjectPtr):
    '''
    Class wrapping a gdb.Value that's a (PyTracebackObject*) within the
    inferior process.
    '''

    # PyTracebackObject is defined in:
    # https://hg.python.org/cpython/file/tip/Include/traceback.h
    _typename = 'PyTracebackObject'

    def __init__(self, gdbval, cast_to=None):
        PyObjectPtr.__init__(self, gdbval, cast_to)
        self._py_tb_obj = gdbval.cast(self.get_gdb_type()).dereference()

    def _get_struct_elem(self, name):
        return self.__class__.from_pyobject_ptr(self._py_tb_obj[name])

    def get_frame(self):
        return self._get_struct_elem('tb_frame')

    def get_next(self):
        return self._get_struct_elem('tb_next')

    @classmethod
    def subclass_from_type(cls, t):
        '''
        This is called from the from_pyobject_ptr class method we've
        inherited. We override its default implementation to be
        aware of traceback objects.
        '''

        try:
            tp_name = t.field('tp_name').string()
            if tp_name == 'traceback':
                return PyTracebackObjectPtr
        except RuntimeError:
            pass

        return PyObjectPtr.subclass_from_type(t)

class PyExcPrint(gdb.Command):
    '''
    Display a (sort of) Python-style traceback of the exception currently
    being handled.
    '''

    def __init__(self):
        gdb.Command.__init__(self, 'py-exc-print', gdb.COMMAND_STACK,
                             gdb.COMPLETE_NONE)

    def invoke(self, args, from_tty):
        pm_traceback_print_exc()

PyExcPrint()
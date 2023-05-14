'''Module to lock a resource for a core and 
   prevent other cores from accessing it.
'''

import _thread

lock = _thread.allocate_lock()

import uos, machine, os, gc

gc.collect()

def df():
    s = os.statvfs('//')
    return ('{0} MB'.format((s[0]*s[3])/1048576))
class Struct(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__dict__[k] = v
            
    def __repr__(self):
        kk=list(self.__dict__.keys())
        kk.sort()
        bits = [k + '=' + repr(self.__dict__[k]) for k in kk]
        return 'Struct(' + ', '.join(bits) + ')'
    
    def __str__(self):
        kk=list(self.__dict__.keys())
        kk.sort()
        bits = [k + '=' + repr(self.__dict__[k]) for k in kk]
        return 'Struct( ' + ',\n  '.join(bits) + ' )'

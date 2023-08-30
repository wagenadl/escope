class Struct(object):
    def __repr__(self):
        s0 = super(Struct,self).__repr__()
        s1 = ' {'
        kk=self.__dict__.keys()
        kk.sort()
        for k in kk:
            s1 += k + '=' + repr(self.__dict__[k]) + ', '
        return s0[:-1] + s1[:-2] + '}>'
    
    def __str__(self):
        s1='{'
        kk=self.__dict__.keys()
        kk.sort()
        for k in kk:
            s1 += k + '=' + str(self.__dict__[k]) + ', '
        return s1[:-2] + '}'
    


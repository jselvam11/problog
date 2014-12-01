import unittest

from problog import root_path

import shutil
shutil.rmtree( root_path('problog', 'logic')  )


from problog.setup import install
from problog.program import PrologFile
from problog.sdd_formula import SDD

import glob, os

class TestSystem(unittest.TestCase) :
    
    def setUp(self) :
        
        install()
        
        try :
            self.assertSequenceEqual = self.assertItemsEqual
        except AttributeError :
            self.assertSequenceEqual = self.assertCountEqual
        
        
    
    def testDummy(self) :
        pass


def read_result(filename) :
    results = {}
    with open( filename ) as f :
        reading = False
        for l in f :
            if l.strip().startswith('%Expected outcome:') :
                reading = True
            elif reading :
                if l.strip().startswith('% ') :
                    query, prob = l[2:].rsplit(None,1)
                    results[query.strip()] = float(prob.strip())
                else :
                    break
    return results

def createSystemTestSDD(filename) :
    
    correct = read_result(filename)
    
    def test(self) : 
    
        sdd = SDD.createFrom(PrologFile(filename))
        computed = sdd.evaluate()

        self.assertSequenceEqual(correct, computed)
        
        for query in correct :
            self.assertAlmostEqual(correct[query], computed[query])
    
    return test
        

for testfile in glob.glob( root_path('test', '*.pl' ) ) :
    testname = 'test_' + os.path.basename(testfile) + '_SDD'
    setattr( TestSystem, testname, createSystemTestSDD(testfile) )    
        
        
# 
# TestSystem.testB = createSystemTestSDD(root_path('test', '2_tossing_coin.pl' ) )
import itertools
import math
from pathlib import Path
import sys
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import cumulus_study as cloud


def points(productions):
    result=[]
    for _,c in productions:
        if c[0]=='M':result.append(tuple(c[1:]))
        elif c[0]=='L':result.append(tuple(c[1:]))
        elif c[0]=='C':
            p0=result[-1];p1=c[1:3];p2=c[3:5];p3=c[5:7]
            for i in range(1,17):
                t=i/16
                result.append(tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*d+t**3*e
                                    for a,b,d,e in zip(p0,p1,p2,p3)))
    return result


def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


class CumulusGrammarTest(unittest.TestCase):
    def test_domain_produces_connected_nonintersecting_cuts(self):
        for traits in itertools.product((0,.25,.5,.75,1),(-1,-.5,0,.5,1),(0,.5,1)):
            _,form,grammar=cloud.derive(*traits)
            self.assertGreater(form['height'],.28)
            p=points(grammar)
            segments=list(zip(p,p[1:]+p[:1]))
            for i,(a,b) in enumerate(segments):
                for c,d in segments[i+2:]:
                    self.assertFalse(cross(a,b,c)*cross(a,b,d)<-1e-12 and cross(c,d,a)*cross(c,d,b)<-1e-12,traits)

    def test_growth_is_relational_and_backing_matches_face(self):
        _,low,_=cloud.derive(0,0,.5);_,high,_=cloud.derive(1,0,.5)
        self.assertGreater(high['height'],low['height'])
        self.assertEqual(high['base'],low['base'])
        self.assertGreater(len(high['lobes']),len(low['lobes']))
        for old in low['lobes']:
            self.assertEqual(old,next(l for l in high['lobes'] if l['id']==old['id']))
        self.assertEqual([l['id'] for l in high['lobes'] if 'parent' in l],
                         ['primary','right-flank','left-flank','summit'])
        low_doc,_=cloud.document(0);high_doc,_=cloud.document(1)
        # Constant bottom datum in actual output coordinates catches scale-to-fit.
        self.assertEqual(max(c[-1] for c in low_doc['nodes'][-1]['path'] if c[0]=='L'),
                         max(c[-1] for c in high_doc['nodes'][-1]['path'] if c[0]=='L'))
        doc,_=cloud.document()
        back,face=doc['nodes'][1:]
        for b,f in zip(back['path'],face['path']):
            self.assertEqual(b[0],f[0])
            for i,(bv,fv) in enumerate(zip(b[1:],f[1:])):
                self.assertAlmostEqual(bv-fv,3 if i%2==0 else 6)

    def test_invalid_traits_rejected_and_derivation_replays(self):
        for bad in (float('nan'),float('inf'),True,-.1,1.1):
            with self.assertRaises(ValueError):cloud.derive(growth=bad)
        self.assertEqual(cloud.document(.37,-.4,.8),cloud.document(.37,-.4,.8))

    def test_growth_is_continuous_at_birth_and_maturity(self):
        grammar=cloud.definition()
        for rule in grammar['lobes']:
            if 'activation' not in rule:continue
            for threshold in rule['activation']:
                for value in (max(0,threshold-1e-5),threshold,min(1,threshold+1e-5)):
                    _,form,path=cloud.derive(value)
                    self.assertTrue(math.isfinite(form['height']))
                    p=points(path)
                    area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2
                    if value==max(0,threshold-1e-5):before=area
                    self.assertLess(abs(area-before),1e-4)
        # Child attachment is not an independent floating cloud.
        for growth in (.1,.3,.5,.7,.9,1):
            _,form,_=cloud.derive(growth)
            for child in form['lobes']:
                if 'parent' not in child:continue
                parent=next(l for l in form['lobes'] if l['id']==child['parent'])
                self.assertLess(math.dist((child['x'],child['y']),(parent['x'],parent['y'])),child['radius']+parent['radius'])

if __name__=='__main__':unittest.main()

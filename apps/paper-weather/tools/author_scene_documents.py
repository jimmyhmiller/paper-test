"""Author the three explicit proof documents. Not used by the runtime.

The player consumes JSON paths directly; these small construction helpers only
avoid hand-repeating path syntax. Place composition and skyline contours below
are explicit, not inferred or randomized from density/terrain sliders.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]/'scenes'
ROOT.mkdir(exist_ok=True)
def poly(points): return [['M',*points[0]], *[['L',*p] for p in points[1:]], ['Z']]
def box(x,y,w,h): return poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)])
def ellipse(x,y,rx,ry):
 k=.55228475
 return [['M',x+rx,y],['C',x+rx,y+k*ry,x+k*rx,y+ry,x,y+ry],['C',x-k*rx,y+ry,x-rx,y+k*ry,x-rx,y],['C',x-rx,y-k*ry,x-k*rx,y-ry,x,y-ry],['C',x+k*rx,y-ry,x+rx,y-k*ry,x+rx,y],['Z']]
def piece(id,path,material,z,**kw): return dict(id=id,path=path,material=material,z=z,**kw)
def group(id,children,**kw):return dict(id=id,children=children,**kw)
def gate(channel,lo=0,hi=1): return dict(channel=channel,min=lo,max=hi)
def mat(day,night,winter=None):
 d=dict(day=int(day,16),night=int(night,16))
 if winter:d['winter']=int(winter,16)
 return d
M={
 'sky':mat('c4dce2','1e354c','c7dce1'), 'cloud':mat('f4eddd','697b8e'),
 'cloud-back':mat('dfddcf','52677c'), 'far':mat('9eafb4','33495f'),
 'stone':mat('e8dfca','647583'), 'stone-shade':mat('b3bcb5','40596d'),
 'roof':mat('7898a2','2d455c'), 'glass':mat('668997','d5b584'),
 'land':mat('ddd5bf','53636b','e7e6db'), 'shore':mat('f1e7d3','73828b','f4eee0'),
 'water':mat('7daab8','2e5269','a1bec7'), 'ripple':mat('b0ccd0','688597','dce3db'),
 'leaf':mat('c3a06c','667166','bfc3b6'), 'leaf-fold':mat('a88d65','4c605e','9eafa7'),
 'trunk':mat('8d7960','485365'), 'pine':mat('7e9077','3b555a'),
 'pine-fold':mat('607c6c','2f4954'), 'snow':mat('f5efdf','a8bac6'),
 'rain':mat('9bb9c5','89a8bb'), 'mountain':mat('9e9f9f','3d5065','879faa'),
 'mountain-fold':mat('657f90','2b435b','5e7c91'),
 'crag-light':mat('b5aa9d','687386','9caeb6'), 'crag-shade':mat('89959c','354c63','718e9e'),
}
def cloud(id,x,y,s):
 p=[['M',0,35],['C',-16,35,-13,9,6,10],['C',4,-10,29,-19,40,0],['C',47,-22,76,-17,79,7],['C',103,4,111,34,91,36],['L',0,36],['Z']]
 def scaled(path,dx=0,dy=0): return [[c[0],*[round(v*s+(dx if j%2==0 else dy),3) for j,v in enumerate(c[1:])]] for c in path]
 return group(id,[piece(id+'-back',scaled(p,2,4),'cloud-back',6),piece(id+'-face',scaled(p),'cloud',7)],transform=[x,y,0,0,0],motion=dict(kind='drift',amplitude=9,period=47,phase=x%6))
def leaf_tree(id,x,y,size=1):
 # A single broad canopy silhouette with one deliberate fold, not five circles.
 stem=box(-2,-59,4,59)+poly([(-1,-35),(-23,-60),(-20,-62),(2,-39)])+poly([(0,-44),(18,-70),(21,-68),(2,-39)])
 canopy=[['M',0,-110],['C',-24,-116,-37,-94,-34,-80],['C',-55,-64,-35,-36,-20,-41],['C',-14,-24,13,-26,20,-42],['C',43,-37,49,-67,30,-77],['C',38,-98,15,-114,0,-110],['Z']]
 def scale(path):return [[c[0],*[round(v*size,3) for v in c[1:]]]for c in path]
 fold=[['M',0,-110],['C',15,-114,38,-98,30,-77],['C',49,-67,43,-37,20,-42],['C',13,-26,1,-30,0,-32],['Z']]
 children=[piece(id+'-wood',scale(stem),'trunk',35),piece(id+'-canopy',scale(canopy),'leaf',36,show=gate('winter',0,.65)),piece(id+'-fold',scale(fold),'leaf-fold',36.5,show=gate('winter',0,.65))]
 return group(id,children,transform=[x,y,0,0,0],motion=dict(kind='sway',amplitude=1.1,period=6.5,phase=x%6))
def pine(id,x,y,s=1):
 children=[piece(id+'-trunk',box(-3*s,-35*s,6*s,35*s),'trunk',34)]
 for j,(top,base,w) in enumerate([(-88,-32,50),(-109,-51,39),(-127,-72,29)]):
  children += [piece(id+f'-tier{j}',poly([(-w*s/2,base*s),(0,top*s),(w*s/2,base*s)]),'pine',35+j*.4),piece(id+f'-fold{j}',poly([(0,top*s),(w*s/2,base*s),(0,base*s)]),'pine-fold',35.2+j*.4),piece(id+f'-cap{j}',poly([(-w*s*.32,(base-16)*s),(0,top*s),(w*s*.32,(base-16)*s),(0,(top+14)*s)]),'snow',37+j*.4,show=gate('snow',.4,1))]
 return group(id,children,transform=[x,y,0,0,0],motion=dict(kind='sway',amplitude=.45,period=8,phase=x%6))
def building(id,contour,windows=(),side=None):
 path=poly(contour)
 for x,y,w,h in windows:path+=box(x,y,w,h)
 xs=[p[0] for p in contour];ys=[p[1] for p in contour]
 nodes=[piece(id+'-back',poly(contour),'glass',15),piece(id+'-face',path,'stone',16)]
 if side:nodes.append(piece(id+'-fold',poly(side),'stone-shade',16.4))
 top=contour[:2]
 return group(id,nodes)
def precip():
 # Each scene declares depth bands: distant flakes sit close to sky stock,
 # foreground flakes close to water/ground. This avoids floating black shadows
 # from putting every particle high above every background surface.
 return [
  dict(id='rain',material='rain',z=7.5,emitter=dict(kind='rain',bounds=[0,0,1000,400],count=48,seed=18)),
  dict(id='foreground-rain',material='rain',z=24.8,emitter=dict(kind='rain',bounds=[0,400,1000,200],count=16,seed=31)),
  dict(id='snowfall',material='snow',z=7.5,emitter=dict(kind='snow',bounds=[0,0,1000,400],count=28,seed=27),show=gate('snowfall',.1,1)),
  dict(id='foreground-snowfall',material='snow',z=24.8,emitter=dict(kind='snow',bounds=[0,400,1000,200],count=17,seed=41),show=gate('snowfall',.1,1))]

def doc(title,nodes,conditions=None):return dict(version=1,title=title,viewBox=[1000,600],materials=M,conditions=conditions or dict(night=0,winter=0,snow=0,rain=0,wind=.35),nodes=nodes)
def write(name,data): (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
# INDIANAPOLIS — an explicit illustrated Canal composition, not a survey panorama.
n=[piece('sky',box(0,0,1000,600),'sky',2),cloud('west-cloud',240,114,1),cloud('east-cloud',790,155,.78)]
n += [piece('distant-city',poly([(180,410),(180,343),(222,343),(222,321),(261,321),(261,365),(307,365),(307,313),(351,313),(351,353),(407,353),(407,316),(458,316),(458,354),(695,354),(695,327),(744,327),(744,344),(805,344),(805,410)]),'far',12)]
n += [building('oneamerica',[(371,400),(371,250),(381,250),(381,222),(401,222),(401,250),(411,250),(411,400)],[(379,y,4,11)for y in range(266,378,24)]+[(393,y,4,11)for y in range(266,378,24)],[(411,250),(420,244),(420,396),(411,400)]),building('salesforce',[(526,400),(526,223),(534,223),(534,192),(544,192),(551,166),(562,166),(569,192),(580,192),(580,223),(588,223),(588,400)],[(537,y,5,15)for y in range(236,383,29)]+[(557,y,5,15)for y in range(236,383,29)],[(573,200),(588,223),(588,400),(573,400)])]
n += [piece('salesforce-spires',box(547,143,1.8,27)+box(564,143,1.8,27),'stone',17),building('regional-tower',[(448,400),(448,289),(458,289),(458,275),(480,275),(480,289),(489,289),(489,400)],[(458,y,4,8)for y in range(301,383,20)]),building('east-modern',[(638,400),(638,280),(686,280),(686,400)],[(647,y,3,65)for y in range(295,296)] +[(658,295,3,65),(669,295,3,65)],[(686,280),(695,275),(695,400),(686,400)])]
n += [piece('park-ground',box(0,392,1000,208),'land',23),piece('canal',poly([(427,395),(575,395),(828,600),(161,600)]),'water',24),piece('west-promenade',poly([(0,415),(416,397),(161,600),(0,600)]),'shore',25),piece('east-promenade',poly([(584,397),(1000,415),(1000,600),(828,600)]),'shore',25)]
# restrained planar paper ripple cuts; rhythm is animated as an attached group
n += [group('canal-ripples',[piece('ripple-near',poly([(325,553),(612,553),(650,555),(303,555)]),'ripple',24.4),piece('ripple-middle',poly([(407,485),(565,485),(576,486.6),(395,486.6)]),'ripple',24.4)],motion=dict(kind='drift',amplitude=3,period=11,phase=1))]
bridge=[['M',340,432],['C',422,398,575,398,662,432],['L',662,444],['C',570,416,427,416,340,444],['Z']]
n += [piece('canal-bridge',bridge,'roof',28),piece('bridge-rail',poly([(342,417),(660,417),(660,420),(342,420)])+box(355,417,2,15)+box(403,410,2,15)+box(451,405,2,14)+box(500,404,2,13)+box(549,405,2,14)+box(597,410,2,15)+box(647,417,2,15),'roof',29)]
n += [leaf_tree('west-front-tree',62,545,1.6),leaf_tree('west-middle-tree',216,466,.85),leaf_tree('east-front-tree',935,555,1.55),leaf_tree('east-middle-tree',790,470,.8),leaf_tree('west-small-tree',295,435,.52),leaf_tree('east-small-tree',717,437,.55)]
n += [piece('bank-snow',poly([(0,415),(416,397),(405,401),(0,422)])+poly([(584,397),(1000,415),(1000,422),(595,402)]),'snow',26,show=gate('snow',.4,1))]+precip()
write('indianapolis',doc('Indianapolis · Canal paper study',n))
# NEW YORK — explicit Lower Manhattan contour plus a coherent bridge assembly.
n=[piece('sky',box(0,0,1000,600),'sky',2),cloud('harbor-cloud',215,106,.85),cloud('bridge-cloud',690,83,.7),piece('river',box(0,390,1000,210),'water',23)]
back=[(79,404),(79,335),(110,335),(110,309),(145,309),(145,350),(178,350),(178,317),(204,317),(204,333),(239,333),(239,295),(278,295),(278,344),(320,344),(320,283),(353,283),(353,337),(388,337),(388,316),(430,316),(430,343),(475,343),(475,275),(504,275),(504,343),(548,343),(548,320),(586,320),(586,404)]
n += [piece('downtown-distant-blocks',poly(back),'far',12)]
skyline=[('one-world',[(213,405),(219,223),(226,211),(226,188),(240,188),(240,211),(248,223),(256,405)],[(229,y,5,25)for y in range(239,370,42)],[(240,211),(248,223),(256,405),(239,405)]),('woolworth',[(406,405),(406,299),(412,299),(412,272),(420,253),(428,272),(428,299),(435,299),(435,405)],[(415,y,4,11)for y in range(311,380,23)],None),('seaport-block',[(105,405),(105,353),(173,353),(173,405)],[(x,366,4,16)for x in [115,130,145,160]],None),('financial-tower',[(296,405),(296,283),(321,283),(321,405)],[(306,y,4,13)for y in range(299,382,24)],[(321,283),(331,278),(331,405),(321,405)]),('east-bank',[(480,405),(480,324),(534,324),(534,405)],[(x,339,4,31)for x in [490,505,520]],None),('stepped-financial',[(353,405),(353,337),(362,337),(362,318),(386,318),(386,337),(396,337),(396,405)],[(366,350,4,28),(379,350,4,28)],None)]
for name,points,windows,side in skyline:n += [building(name,points,windows,side)]
# Interlocking stepped blocks make this a continuous downtown silhouette.
for name, contour, apertures in [
 ('world-financial-west',[(172,405),(172,331),(181,331),(181,313),(199,301),(215,313),(215,331),(220,331),(220,405)],[(181,345,3,15),(193,345,3,15),(205,345,3,15),(181,373,3,13),(193,373,3,13),(205,373,3,13)]),
 ('world-trade-neighbor',[(265,405),(265,270),(280,259),(289,270),(289,405)],[(274,287,3,52)]),
 ('battery-low-block',[(66,405),(66,373),(107,373),(107,405)],[(75,383,3,9),(88,383,3,9)]),
 ('downtown-front-left',[(247,405),(247,354),(284,354),(284,405)],[(256,365,3,11),(270,365,3,11),(256,386,3,10),(270,386,3,10)]),
 ('downtown-front-center',[(330,405),(330,369),(366,369),(366,405)],[(339,380,3,13),(353,380,3,13)]),
 ('downtown-slate-step',[(442,405),(442,343),(451,343),(451,329),(467,329),(467,343),(476,343),(476,405)],[(452,355,4,12),(452,378,4,12)]),
 ('seaport-eastern-block',[(539,405),(539,359),(585,359),(585,405)],[(548,371,4,12),(563,371,4,12),(577,371,3,12)])
]:
 n += [building(name,contour,apertures)]
n += [piece('one-world-spire',box(232,143,1.7,47),'roof',17)]
# Bridge tower Gothic apertures use real even-odd subpaths.
tower=box(800,196,61,252)+poly([(807,196),(807,184),(855,184),(855,196)])
for x in [811,838]:tower += [['M',x,414],['L',x,266],['C',x,253,x+5,241,x+9,235],['C',x+14,241,x+18,253,x+18,266],['L',x+18,414],['Z']]
cables=[]
for shift in [0,5]:
 cables += [['M',478,366+shift],['C',608,356+shift,740,307+shift,815,207+shift],['L',815,210+shift],['C',740,310+shift,608,359+shift,478,369+shift],['Z']]
 cables += [['M',846,207+shift],['C',900,260+shift,952,278+shift,1000,286+shift],['L',1000,289+shift],['C',952,281+shift,900,263+shift,846,210+shift],['Z']]
for x,top,bottom in [(558,355,357),(612,338,347),(666,313,337),(720,280,327),(768,242,317),(892,247,304),(940,273,294),(979,283,287)]:cables+=box(x,top,1.2,max(bottom-top,2))
bridge_children=[piece('bridge-deck',poly([(478,366),(1000,280),(1000,294),(478,380)]),'stone-shade',27),piece('bridge-cables',cables,'roof',28),piece('brooklyn-tower',tower,'stone',29),piece('brooklyn-tower-fold',poly([(861,196),(872,188),(872,448),(861,448)]),'stone-shade',29.5),piece('tower-snow-cap',box(800,193,61,3),'snow',30,show=gate('snow',.4,1))]
n += [group('brooklyn-bridge',bridge_children)]
for i,(x,y,w) in enumerate([(45,456,168),(285,490,202),(538,449,174),(722,528,220),(126,553,150)]):n += [group(f'river-wave-{i}',[piece(f'wave-{i}',poly([(x,y),(x+w,y),(x+w-30,y+2),(x+20,y+2)]),'ripple',24)],motion=dict(kind='drift',amplitude=2,period=12+i,phase=i))]
n += [piece('waterfront',poly([(0,516),(262,558),(412,600),(0,600)]),'shore',32),piece('ledge-fold',poly([(0,516),(262,558),(262,568),(0,526)]),'stone-shade',33),piece('ledge-snow',poly([(0,513),(262,555),(275,560),(0,520)]),'snow',34,show=gate('snow',.4,1))]
n += [group('winter-branches',[piece('bare-branch',poly([(47,550),(52,550),(57,482),(96,441),(94,437),(59,473),(64,403),(60,401),(52,478),(23,440),(20,442),(51,487)]),'trunk',35)],motion=dict(kind='sway',amplitude=.55,period=7,phase=1),transform=[0,0,0,48,550])]+precip()
write('new-york',doc('New York · Brooklyn waterfront paper study',n,dict(night=.55,winter=1,snow=0,rain=0,wind=.3)))
# MAROON BELLS — authored twin-peak ridge, not randomly generated triangles.
n=[piece('sky',box(0,0,1000,600),'sky',2),cloud('valley-cloud',175,102,.85),cloud('east-cloud',760,127,.55)]
n += [piece('rear-ridge',poly([(0,426),(0,301),(115,248),(203,302),(325,211),(425,283),(571,221),(687,292),(819,241),(1000,303),(1000,463)]),'far',12)]
left=[(172,452),(263,303),(314,256),(336,223),(369,233),(388,182),(411,171),(434,124),(464,150),(490,193),(523,208),(553,268),(594,322),(636,452)]
right=[(479,452),(548,317),(583,281),(609,228),(633,238),(661,186),(684,163),(709,187),(731,230),(761,243),(790,316),(859,452)]
n += [piece('maroon-peak',poly(left),'mountain',16),piece('maroon-peak-fold',poly([(434,124),(464,150),(490,193),(523,208),(553,268),(594,322),(636,452),(452,452),(464,267),(428,213)]),'mountain-fold',17),piece('north-maroon',poly(right),'mountain',18),piece('north-maroon-fold',poly([(684,163),(709,187),(731,230),(761,243),(790,316),(859,452),(693,452),(707,305),(677,241)]),'mountain-fold',19)]
# Limited residual snow vs added settled winter snow: masks are authored contours.
n += [piece('maroon-west-ridges',poly([(434,124),(411,171),(388,182),(369,233),(336,223),(314,256),(263,303),(237,360),(308,317),(337,278),(359,288),(389,240),(407,219),(428,213)]),'crag-light',19.2),
      piece('maroon-chiseled-fold',poly([(411,171),(428,213),(407,219),(389,240),(382,280),(359,320),(336,378),(383,330),(406,296),(420,258),(444,263),(426,228)]),'crag-shade',19.3),
      piece('north-maroon-west-ridge',poly([(684,163),(661,186),(633,238),(609,228),(583,281),(548,317),(537,338),(592,302),(611,267),(639,278),(655,237),(673,221)]),'crag-light',19.4),
      piece('north-maroon-chiseled-fold',poly([(684,163),(673,221),(655,237),(672,270),(660,314),(625,368),(685,325),(705,295),(682,247)]),'crag-shade',19.5)]
n += [piece('high-crag-snow',poly([(434,124),(464,150),(480,179),(458,168),(447,149),(425,166),(411,171)])+poly([(684,163),(709,187),(723,214),(701,204),(687,184),(672,204),(661,210)]),'snow',20)]
n += [piece('winter-mountain-snow',poly([(388,182),(411,171),(434,124),(425,179),(445,197),(464,202),(472,232),(451,215),(432,212),(420,188),(399,201),(382,224)])+poly([(307,270),(336,223),(369,233),(388,182),(380,235),(357,258),(337,244),(321,275)])+poly([(609,228),(633,238),(661,186),(652,242),(629,259),(615,247),(596,276)])+poly([(709,187),(731,230),(761,243),(773,275),(748,256),(728,251),(720,227)]),'snow',21,show=gate('snow',.4,1))]
n += [piece('valley-floor',poly([(0,389),(181,398),(379,455),(540,460),(820,386),(1000,361),(1000,600),(0,600)]),'land',23),piece('maroon-lake',poly([(213,458),(749,458),(1000,600),(0,600)]),'water',24),piece('left-bank',poly([(0,416),(184,436),(297,492),(144,559),(0,600)]),'shore',25),piece('right-bank',poly([(770,435),(1000,408),(1000,600),(879,551),(729,493)]),'shore',25)]
for i,(x,y,w) in enumerate([(322,485,308),(203,532,191),(526,566,277)]):n += [group(f'lake-wave-{i}',[piece(f'lake-ripple-{i}',poly([(x,y),(x+w,y),(x+w-40,y+2),(x+20,y+2)]),'ripple',24.4)],motion=dict(kind='drift',amplitude=2,period=15+i,phase=i))]
n += [pine('left-evergreen',114,496,1.18),pine('right-evergreen',909,505,1.25),pine('far-left-evergreen',244,462,.5),pine('far-right-evergreen',790,460,.55),leaf_tree('left-aspen',40,533,1.65),leaf_tree('left-small-aspen',181,480,.85),leaf_tree('right-aspen',979,551,1.7),leaf_tree('right-small-aspen',844,474,.8)]
n += [piece('shore-snow',poly([(0,416),(184,436),(297,492),(284,498),(174,444),(0,425)])+poly([(770,435),(1000,408),(1000,418),(780,443),(738,497),(729,493)]),'snow',26,show=gate('snow',.4,1)),piece('winter-ice',poly([(130,568),(249,547),(405,549),(356,558),(518,560),(489,571),(278,574),(377,586),(295,600),(0,600)]),'snow',25,show=gate('winter',.75,1))]+precip()
write('maroon-bells',doc('Maroon Bells · Lake paper study',n))
for f in [ROOT/(name+'.json') for name in ['indianapolis','new-york','maroon-bells']]:
 data=json.loads(f.read_text())
 def walk(nodes):
  return sum(1+walk(n.get('children',[])) for n in nodes)
 print(f.name,walk(data['nodes']),'nodes')

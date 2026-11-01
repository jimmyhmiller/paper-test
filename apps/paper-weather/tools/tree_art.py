#!/usr/bin/env python3
"""One procedural paper-tree family: form, variation, placement, aesthetic rules.

Uses only Python's standard library. Output is native Paper scene data, not a
raster illustration. No image generator, generic-city system or runtime eval.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import random
import tempfile

APP = Path(__file__).resolve().parents[1]
DEFAULT_DEFINITION = APP/'art/trees/folded-conifer.json'


def load_definition(path):
    def nonfinite(value):
        raise ValueError(f'Non-finite value in tree definition: {value}')
    definition=json.loads(path.read_text(),parse_constant=nonfinite)
    if definition.get('construction')!='folded-conifer-v1' or definition.get('version')!=1:
        raise ValueError('Unsupported tree construction/version')
    traits=definition['variation']
    if set(traits)!={'age','vigour','exposure','gesture'}:
        raise ValueError('This family requires age, vigour, exposure and gesture traits')
    for name,rule in traits.items():
        lo,hi=rule['range']
        if not lo<hi or not lo<=rule['mean']<=hi or not 0<rule['deviation']<=2:
            raise ValueError(f'Invalid sampling rule: {name}')
    domains={'height':(50,600),'width_ratio':(.1,1.0),'trunk_ratio':(.005,.1),
             'clearance':(.05,.4),'lean':(-.2,.2),'tier_count':(3,10),
             'taper_power':(.2,2),'branch_sag':(.01,.5),'asymmetry':(-.3,.3)}
    if set(definition['form'])!=set(domains):
        raise ValueError('Unexpected/missing form relationship')
    for name,equation in definition['form'].items():
        low=high=equation.get('base',0)
        for trait,coefficient in equation.items():
            if trait=='base':continue
            if trait not in traits:raise ValueError(f'Unknown trait in {name}: {trait}')
            a,b=traits[trait]['range']
            low+=min(a*coefficient,b*coefficient);high+=max(a*coefficient,b*coefficient)
        if not domains[name][0]<=low<=high<=domains[name][1]:
            raise ValueError(f'{name} relationship exceeds construction domain')
    for rule in definition['preferences'].values():
        if rule['weight']<0 or rule['tolerance']<=0:
            raise ValueError('Aesthetic preference requires nonnegative weight and positive tolerance')
    if sum(r['weight'] for r in definition['preferences'].values())<=0:
        raise ValueError('At least one aesthetic preference needs weight')
    stocks=definition['paper']['stocks']
    if not 1<=len(stocks)<=12:raise ValueError('Paper palette exceeds native material budget')
    for stock in stocks:
        for key in ['face','fold']:
            if len(stock[key])!=6 or not 0<=int(stock[key],16)<=0xffffff:
                raise ValueError('Stocks must be six-digit RGB colors')
    rules=definition['construction_rules'];placement=definition['placement']
    if not 0<=rules['tier_overlap']<=1 or not 0<=rules['local_width_variation']<=.1 or not 0<=rules['tier_step_variation']<=.2:
        raise ValueError('Invalid crown construction variation')
    if not 1<=placement['count']<=24 or not placement['count']<=placement['candidate_pool']<=10000:
        raise ValueError('Placement work exceeds study budget')
    if not 1<=placement['alternatives_per_tree']<=128:
        raise ValueError('Invalid placement alternatives count')
    for kernel in placement['density_field']:
        if min(kernel['radius'])<=0 or kernel['weight']<=0:
            raise ValueError('Invalid density-field kernel')
    return definition


def stream(seed, channel):
    digest = hashlib.blake2b(f'{seed}:{channel}'.encode(), digest_size=16).digest()
    return random.Random(int.from_bytes(digest, 'big'))


def relation(rule, traits):
    return rule.get('base', 0) + sum(traits[k]*v for k, v in rule.items() if k != 'base')


def sample_traits(definition, seed):
    result = {}
    for name, rule in definition['variation'].items():
        rng = stream(seed, name)
        lo, hi = rule['range']
        for _ in range(1000):
            value = rng.gauss(rule['mean'], rule['deviation'])
            if lo <= value <= hi:
                result[name] = value
                break
        else:
            raise ValueError(f'Could not sample {name}; inspect its distribution')
    return result


@dataclass(frozen=True)
class Tier:
    top: float
    bottom: float
    radius: float
    left: float
    right: float


@dataclass(frozen=True)
class Tree:
    seed: int
    traits: dict
    height: float
    width_ratio: float
    trunk_ratio: float
    clearance: float
    lean: float
    taper_power: float
    branch_sag: float
    asymmetry: float
    tiers: tuple[Tier, ...]
    metrics: dict
    losses: dict
    score: float
    violations: tuple[str, ...]

    @property
    def width(self):
        return self.height*self.width_ratio


def construct(definition, seed, traits=None):
    traits = dict(sample_traits(definition, seed) if traits is None else traits)
    form = {name: relation(rule, traits) for name, rule in definition['form'].items()}
    count = round(form.pop('tier_count'))
    rules = definition['construction_rules']
    height = form['height']
    crown = height*(1-form['clearance'])
    width = height*form['width_ratio']
    rng = stream(seed, 'tier-rhythm')
    # Generate top-to-bottom branch tiers along one shared growth axis.
    # Perturb spacings, then normalize; adding a material rule cannot move them.
    steps = [1+rng.uniform(-rules['tier_step_variation'], rules['tier_step_variation']) for _ in range(count)]
    total = sum(steps)
    position = 0
    tiers = []
    for i, step in enumerate(steps):
        top_fraction = position/total
        position += step
        bottom_fraction = position/total
        radius = width*.5*bottom_fraction**form['taper_power']
        radius *= 1+stream(seed, f'tier-width-{i}').uniform(-rules['local_width_variation'], rules['local_width_variation'])
        overlap = rules['tier_overlap']*(bottom_fraction-top_fraction)
        top = -height + crown*max(0, top_fraction-overlap)
        bottom = -height + crown*bottom_fraction
        # A shared asymmetry gives a coherent gesture; local variation is small.
        left = radius*(1-form['asymmetry'])
        right = radius*(1+form['asymmetry'])
        tiers.append(Tier(top, bottom, radius, left, right))
    metrics = {
        'proportion': form['width_ratio'],
        'branch_rhythm': coefficient_of_variation(steps),
        'trunk_exposure': form['clearance'],
        'gesture': abs(form['lean']),
    }
    losses = {name: ((metrics[name]-rule['target'])/rule['tolerance'])**2 for name, rule in definition['preferences'].items()}
    weighted = sum(losses[k]*rule['weight'] for k, rule in definition['preferences'].items())
    weights = sum(rule['weight'] for rule in definition['preferences'].values())
    violations = []
    values = dict(form, absolute_lean=abs(form['lean']), tier_count=count)
    for name, limits in definition['constraints'].items():
        if name == 'minimum_tier_overlap':
            continue
        if not limits[0] <= values[name] <= limits[1]:
            violations.append(name)
    for above, below in zip(tiers, tiers[1:]):
        overlap = (above.bottom-below.top)/(below.bottom-below.top)
        if overlap < definition['constraints']['minimum_tier_overlap']:
            violations.append('tier_overlap')
    if any(b.radius <= a.radius for a,b in zip(tiers,tiers[1:])):
        violations.append('crown_taper')
    return Tree(seed, traits, **form, tiers=tuple(tiers), metrics=metrics,
                losses=losses, score=math.exp(-weighted/weights), violations=tuple(violations))


def coefficient_of_variation(values):
    mean = sum(values)/len(values)
    return math.sqrt(sum((v-mean)**2 for v in values)/len(values))/mean


def feature(tree):
    return [tree.traits[k] for k in ['age','vigour','exposure','gesture']]


def difference(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(feature(a),feature(b))))


def select_variations(definition, count=6, start=100, candidates=256):
    pool = [construct(definition, seed) for seed in range(start,start+candidates)]
    pool = [tree for tree in pool if not tree.violations and tree.score >= .35]
    if len(pool) < count:
        raise ValueError('Insufficient admissible variants; inspect constraints and preferences')
    selected = [max(pool,key=lambda tree:tree.score)]
    pool.remove(selected[0])
    while len(selected) < count:
        winner = max(pool,key=lambda t:min(difference(t,s) for s in selected)*(.65+.35*t.score))
        selected.append(winner)
        pool.remove(winner)
    return selected


def material(rgb):
    return {'day':int(rgb,16),'night':int(rgb,16)}


def palette(definition):
    result = {'paper':material('f3ead9'),'ground':material('e7e2d1'),'ground-fold':material('dbddcb'),
              'trunk':material(definition['paper']['trunk']),'trunk-fold':material(definition['paper']['trunk_fold'])}
    for i,stock in enumerate(definition['paper']['stocks']):
        result[f'face-{i}']=material(stock['face'])
        result[f'fold-{i}']=material(stock['fold'])
    return result


def path_node(identity, commands, stock, z):
    return {'id':identity,'path':commands,'material':stock,'z':round(z,4)}


def poly(points):
    return [['M',*points[0]],*[['L',*p]for p in points[1:]],['Z']]


def box(x,y,w,h):
    return poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)])


def tree_geometry(definition, tree, identity, x, y, scale=1, depth=32, sheet_step=None):
    """Two faces per tier meet at the exact same curved seam.

    Construct lower tiers first; upper tiers overlap them as cardstock. Tier tips,
    width and fold all derive from the same branch coordinates.
    """
    h = tree.height
    def axis(v):
        t=-v/h
        return h*tree.lean*(.35*t+.65*t*t)
    def P(vx,vy):return [round(vx*scale,4),round(vy*scale,4)]
    def M(vx,vy):return ['M',*P(vx,vy)]
    def L(vx,vy):return ['L',*P(vx,vy)]
    def C(a,b,c,d,e,f):return ['C',*P(a,b),*P(c,d),*P(e,f)]
    width = h*tree.trunk_ratio
    tip_y = -h*.88
    wood=[M(-width*.5,0),C(-width*.35,-h*.35,axis(tip_y)-width*.15,tip_y*.8,axis(tip_y),tip_y),
          C(axis(tip_y)+width*.15,tip_y*.8,width*.35,-h*.35,width*.5,0),['Z']]
    wood_fold=[M(0,0),L(axis(tip_y),tip_y),C(axis(tip_y)+width*.15,tip_y*.8,width*.35,-h*.35,width*.5,0),['Z']]
    nodes=[path_node(identity+'-trunk',wood,'trunk',depth),path_node(identity+'-trunk-fold',wood_fold,'trunk-fold',depth+.1)]
    stock = min(len(definition['paper']['stocks'])-1, int(tree.traits['exposure']*len(definition['paper']['stocks'])))
    rules=definition['construction_rules']
    for order,tier in enumerate(reversed(tree.tiers)):
        peak_x=axis(tier.top); bottom_x=axis(tier.bottom)
        span=tier.bottom-tier.top
        sag=span*tree.branch_sag
        seam_x=bottom_x+tier.radius*rules['fold_offset']
        seam_y=tier.bottom-sag*.65
        left_x=bottom_x-tier.left;right_x=bottom_x+tier.right
        # Control points deliberately keep the upper branch edges taut, while
        # lower edges lift toward the shared fold. No circles or stacked symbols.
        left=[M(peak_x,tier.top),C(peak_x-tier.left*.18,tier.top+span*.44,left_x+tier.left*.17,tier.bottom-span*.16,left_x,tier.bottom),
              C(left_x+tier.left*.18,tier.bottom-sag,left_x+tier.left*.58,seam_y-span*.025,seam_x,seam_y),
              C(seam_x,tier.top+span*.62,peak_x,tier.top+span*.21,peak_x,tier.top),['Z']]
        right=[M(peak_x,tier.top),C(peak_x,tier.top+span*.21,seam_x,tier.top+span*.62,seam_x,seam_y),
               C(right_x-tier.right*.58,seam_y-span*.025,right_x-tier.right*.18,tier.bottom-sag,right_x,tier.bottom),
               C(right_x-tier.right*.17,tier.bottom-span*.16,peak_x+tier.right*.18,tier.top+span*.44,peak_x,tier.top),['Z']]
        z=depth+.35+order*(rules['sheet_step'] if sheet_step is None else sheet_step)
        nodes += [path_node(f'{identity}-tier-{order}-face',left,f'face-{stock}',z),path_node(f'{identity}-tier-{order}-fold',right,f'fold-{stock}',z+.015)]
    return {'id':identity,'children':nodes,'transform':[round(x,4),round(y,4),0,0,0]}


def document(definition,title,nodes):
    return {'version':1,'title':title,'viewBox':[1200,720],'materials':palette(definition),
            'conditions':dict(night=0,winter=0,snow=0,rain=0,wind=0),
            'nodes':[path_node('paper-ground',box(0,0,1200,720),'paper',30),*nodes]}


def contact_sheet(definition, variants):
    nodes=[]
    for i,tree in enumerate(variants):
        col=i%3;row=i//3
        x=200+col*400;y=340+row*350
        nodes.append(tree_geometry(definition,tree,f'variant-{i+1:02}',x,y,scale=1,depth=32))
    return document(definition,'Folded conifer · six individuals from one definition',nodes)


@dataclass(frozen=True)
class PlacedTree:
    tree: Tree
    x: float
    y: float
    scale: float
    density: float

    @property
    def bounds(self):
        lean=abs(self.tree.lean)*self.tree.height*self.scale
        half=self.tree.width*self.scale*.56
        return (self.x-half-lean,self.y-self.tree.height*self.scale,self.x+half+lean,self.y)


def density_at(rule,x,y):
    return sum(kernel['weight']*math.exp(-.5*((x-kernel['center'][0])/kernel['radius'][0])**2-.5*((y-kernel['center'][1])/kernel['radius'][1])**2)for kernel in rule['density_field'])


def intersects(a,b):
    return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]


def placement_violations(rule,candidate,placed):
    errors=[]
    x0,y0,x1,y1=rule['region']
    if not x0<=candidate.x<=x1 or not y0<=candidate.y<=y1: errors.append('outside_ground')
    if intersects(candidate.bounds,rule['protected_opening']):errors.append('protected_opening')
    bounds=candidate.bounds
    if bounds[0]<28 or bounds[2]>1172 or bounds[1]<38:errors.append('frame_clearance')
    for other in placed:
        required=rule['minimum_root_spacing']*(candidate.scale+other.scale)*.5
        if math.hypot(candidate.x-other.x,candidate.y-other.y)<required:
            errors.append('root_spacing');break
    return errors


def placement_losses(rule,candidate,placed):
    crowd=tangent=repetition=0.0
    for other in placed:
        a,b=candidate.bounds,other.bounds
        if min(a[3],b[3])<=max(a[1],b[1]):continue
        signed_overlap=min(a[2],b[2])-max(a[0],b[0])
        smaller=min(a[2]-a[0],b[2]-b[0])
        overlap=signed_overlap/smaller
        target=rule['crown_clearance']
        # Signed envelope overlap catches near-touching from either side.
        # Exact touching is worst; both a clear gap and a decisive overlap relax it.
        tangent += math.exp(-(overlap/target)**2)
        crowd += max(0,overlap-.62)**2
        repetition += math.exp(-difference(candidate.tree,other.tree)**2/.12)*max(0,overlap)
    return {'density':-math.log(max(candidate.density,.0001)), 'crowding':crowd,
            'near_tangency':tangent,'neighbor_repetition':repetition,
            'individual_quality':1-candidate.tree.score}


def place_grove(definition):
    rule=definition['placement'];rng=stream(rule['seed'],'ground-candidates')
    x0,y0,x1,y1=rule['region'];s0,s1=rule['perspective_scale']
    pool=[];rejected={}
    for i in range(rule['candidate_pool']):
        x=rng.uniform(x0,x1);y=rng.uniform(y0,y1)
        tree=construct(definition,rule['seed']*10000+i)
        scale=s0+(s1-s0)*(y-y0)/(y1-y0)
        candidate=PlacedTree(tree,x,y,scale,density_at(rule,x,y))
        reasons=list(tree.violations)+placement_violations(rule,candidate,[])
        if reasons:
            for reason in set(reasons):rejected[reason]=rejected.get(reason,0)+1
        else:pool.append(candidate)
    selected=[];records=[]
    for _ in range(rule['count']):
        eligible=[c for c in pool if not placement_violations(rule,c,selected)]
        if not eligible:raise ValueError('Placement exhausted; inspect rejection report and constraints')
        # Density-based proposal, aesthetic preference selection. A stochastic
        # proposal avoids always taking the central maximum of a density field.
        proposals=rng.choices(eligible,weights=[c.density for c in eligible],k=min(rule['alternatives_per_tree'],len(eligible)))
        def cost(c):
            losses=placement_losses(rule,c,selected)
            return sum(rule['preferences'][k]*v for k,v in losses.items())
        winner=min(proposals,key=cost)
        records.append({'seed':winner.tree.seed,'x':winner.x,'y':winner.y,'scale':winner.scale,
                        'losses':placement_losses(rule,winner,selected),'weighted_cost':cost(winner)})
        selected.append(winner);pool.remove(winner)
    return sorted(selected,key=lambda c:c.y),{'rejected':rejected,'placements':records}


def grove_scene(definition,placements):
    back=[['M',0,424],['C',290,354,395,462,627,415],['C',844,363,1040,388,1200,401],['L',1200,760],['L',0,760],['Z']]
    front=[['M',0,604],['C',240,556,421,692,692,618],['C',864,566,1031,631,1200,598],['L',1200,760],['L',0,760],['Z']]
    nodes=[path_node('distant-ground-fold',back,'ground-fold',30.2),path_node('near-ground-fold',front,'ground',30.4)]
    for i,placed in enumerate(placements):
        stack=definition['placement']['paper_stack']
        depth=stack['base']+i*stack['tree_band']
        occupied=.35+(len(placed.tree.tiers)-1)*stack['tier_step']+.015
        if occupied >= stack['tree_band'] or depth+occupied>48:
            raise ValueError('Paper depth budget cannot preserve whole-tree occlusion')
        nodes.append(tree_geometry(definition,placed.tree,f'grove-tree-{i+1:02}',placed.x,placed.y,placed.scale,depth,sheet_step=stack['tier_step']))
    return document(definition,'Folded conifer · clustered placement with a protected opening',nodes)


def save(path,data,indent=2):
    # A running native viewer should see a complete revision, never a half-write.
    candidate=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix='.'+path.name,suffix='.candidate',delete=False) as file:
            candidate=Path(file.name)
            file.write(json.dumps(data,indent=indent,allow_nan=False,separators=(',', ':') if indent is None else None)+'\n')
            file.flush()
            os.fsync(file.fileno())
        os.replace(candidate,path)
    finally:
        if candidate is not None:candidate.unlink(missing_ok=True)


def generate(definition_path,output):
    definition=load_definition(definition_path)
    output.mkdir(parents=True,exist_ok=True)
    variants=select_variations(definition)
    placements,placement_report=place_grove(definition)
    save(output/'tree-variations.json',contact_sheet(definition,variants))
    save(output/'tree-grove.json',grove_scene(definition,placements))
    report={'definition':str(definition_path),'definition_sha256':hashlib.sha256(definition_path.read_bytes()).hexdigest(),
            'individuals':[asdict(t) for t in variants], 'grove':placement_report,
            'scope':'Designer-defined measurable constraints/preferences. Scores are not proof of aesthetic quality.'}
    save(output/'tree-report.json',report)
    print(f'Generated {len(variants)} individual variants and {len(placements)} placements in {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definition',type=Path,default=DEFAULT_DEFINITION)
    parser.add_argument('--output',type=Path,default=APP.parents[1]/'output/tree-art')
    args=parser.parse_args()
    generate(args.definition,args.output)

#!/usr/bin/env python3
"""Procedural paper elements, coupled land/water geometry and habitat recipes.

Family definitions own form/variation/preferences; scene recipes own attributes,
placement fields and composition constraints. Existing conifers stay unchanged.
The output is native Paper paths, with no raster art or runtime code evaluation.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import tree_art as tree

APP = Path(__file__).resolve().parents[1]
ART = APP / 'art'
FAMILIES = ('broadleaf', 'grasses', 'rock', 'ridge', 'cloud', 'water')


def load_json(path):
    def reject(value):
        raise ValueError(f'Non-finite value in {path}: {value}')
    data = json.loads(path.read_text(), parse_constant=reject)
    if data.get('version') != 1:
        raise ValueError(f'Unsupported definition version: {path}')
    return data


def library():
    result = {name: load_json(ART / 'elements' / f'{name}.json') for name in FAMILIES}
    for name, definition in result.items():
        if definition['construction'] != name + '-v1':
            raise ValueError(f'Unknown construction algorithm for {name}')
        for rule in definition['variation'].values():
            lo, hi = rule['range']
            if not lo < hi or not lo <= rule['mean'] <= hi or not 0 < rule['deviation'] <= 2:
                raise ValueError(f'Invalid trait distribution for {name}')
        for equation in definition['form'].values():
            if not set(equation) <= {'base', *definition['variation']}:
                raise ValueError(f'Unknown trait in {name} relationship')
        for rule in definition['preferences'].values():
            if rule['weight'] < 0 or rule['tolerance'] <= 0:
                raise ValueError(f'Invalid aesthetic preference for {name}')
    result['conifer'] = tree.load_definition(tree.DEFAULT_DEFINITION)
    result['conifer']['placement'].update(load_json(ART / 'elements' / 'conifer-host.json')['placement'])
    return result


@dataclass(frozen=True)
class Context:
    season: str = 'summer'
    daylight: float = 1
    moisture: float = .5
    wind: float = .25
    snow: float = 0
    cloud: float = .2

    def __post_init__(self):
        if self.season not in ('summer', 'autumn', 'winter'):
            raise ValueError('Season must be summer, autumn or winter')
        for key in ('daylight', 'moisture', 'wind', 'snow', 'cloud'):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'Invalid context attribute: {key}')


@dataclass(frozen=True)
class Element:
    family: str
    seed: int
    traits: dict
    form: dict
    width: float
    height: float
    metrics: dict
    losses: dict
    score: float
    violations: tuple


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))) / 2


def stone_faces(form):
    w, h = form['width'], form['width']/form['aspect']
    outline = [(-w*.5, 0), (-w*.43, -h*.52), (-w*.12, -h),
               (w*form['shoulder'], -h*.85), (w*.5, -h*.31), (w*.46, 0)]
    joint = (w*(form['facet_balance']-.5), -h*.45)
    return outline, [[outline[0], outline[1], outline[2], joint],
                     [outline[2], outline[3], outline[4], joint],
                     [outline[4], outline[5], outline[0], joint]]


def individual(definitions, family, seed):
    if family == 'conifer':
        model = tree.construct(definitions[family], seed)
        return Element(family, seed, model.traits, {}, model.width, model.height,
                       model.metrics, model.losses, model.score, model.violations)
    definition = definitions[family]
    traits = tree.sample_traits(definition, seed)
    form = {k: tree.relation(v, traits) for k, v in definition['form'].items()}
    for key in ('branch_count', 'blades', 'lobes'):
        if key in form:
            form[key] = round(form[key])
    metrics = dict(form)
    violations = [name for name, (lo, hi) in definition['constraints'].items()
                  if not lo <= form[name] <= hi]
    if family == 'broadleaf':
        width, height = form['height']*form['crown_ratio'], form['height']
    elif family == 'grasses':
        height = form['height']; width = height*form['spread']*1.8
    elif family == 'rock':
        width = form['width']; height = width/form['aspect']
        outline, faces = stone_faces(form)
        metrics['smallest_face'] = min(map(area, faces))/area(outline)
        if metrics['smallest_face'] < definition['construction_rules']['minimum_face_area']:
            violations.append('facet_sliver')
    elif family == 'cloud':
        width = form['width']; height = width*form['aspect']
    elif family == 'ridge':
        width, height = form['width'], form['height']
    else:
        width, height = form['near_width'], 180
        metrics['width_ratio'] = form['near_width']/form['far_width']
    losses = {name: ((metrics[name]-rule['target'])/rule['tolerance'])**2
              for name, rule in definition['preferences'].items()}
    total = sum(losses[name]*rule['weight'] for name, rule in definition['preferences'].items())
    weights = sum(rule['weight'] for rule in definition['preferences'].values())
    return Element(family, seed, traits, form, width, height, metrics, losses,
                   math.exp(-total/weights), tuple(violations))


def choose_individual(definitions, family, seed):
    candidates = [individual(definitions, family, seed+i) for i in range(12)]
    eligible = [item for item in candidates if not item.violations]
    if not eligible:
        raise ValueError(f'No admissible {family} near seed {seed}')
    return max(eligible, key=lambda item: item.score)


def color_mix(a, b, amount):
    a, b = int(a, 16) if isinstance(a, str) else a, int(b, 16) if isinstance(b, str) else b
    return sum(round(((a >> shift) & 255)*(1-amount)+((b >> shift) & 255)*amount) << shift
               for shift in (16, 8, 0))


def palette(definitions, context):
    result = tree.palette(definitions['conifer'])
    autumn = context.season == 'autumn'
    wet = context.moisture*.08
    colors = {
        'paper': ('f3ead9', '9baebb', 'f3eee1'),
        'ground': ('d9dfc9' if not autumn else 'dfd1b6', '61777b', 'dce5de'),
        'ground-fold': ('bbcbb6' if not autumn else 'c9b99a', '4e696f', 'b6c9cd'),
        'sky': ('c8dfe2', '244557', 'cadfe4'),
        'water': ('88b6c2', '3b667b', 'a6c6cf'),
        'ripple': ('c1d9d9', '7997a3', 'e4e9df'),
        'ridge-face': ('a0b5b7', '536e80', 'a6bdc6'),
        'ridge-fold': ('7396a5', '3b596f', '7e9fab'),
        'rock-face': ('b7b9aa', '72818a', 'b6c6ca'),
        'rock-fold': ('8e9f9b', '536d7b', '90aab7'),
        'broad-face': ('9faf87' if not autumn else 'd3b17a', '667d70' if not autumn else '95856d', 'b2c1b6'),
        'broad-fold': ('7d976e' if not autumn else 'b89464', '4c6c64' if not autumn else '786d61', '8da7a6'),
        'grass-face': ('a9b791' if not autumn else 'c8b481', '718876', 'b5c4bc'),
        'grass-fold': ('819b78' if not autumn else 'a79265', '526e64', '8ca9a6'),
        'cloud-face': ('f5efdf', '91a5b0', 'f1eee2'),
        'cloud-back': ('dbe1d5', '718c9e', 'd5e0de'),
        'snow': ('f4eee1', 'b0c6d0', 'f4eee1'),
    }
    for key, (day, night, winter) in colors.items():
        if key in ('ground', 'rock-face', 'rock-fold'):
            day = color_mix(day, '849996', wet)
        if key == 'sky':
            day = color_mix(day, 'b4c7cb', context.cloud*.5)
        if key in ('cloud-face', 'cloud-back'):
            day = color_mix(day, 'aebfc6', context.cloud*.48)
        result[key] = {'day': int(day, 16) if isinstance(day, str) else day,
                       'night': int(night, 16), 'winter': int(winter, 16)}
    for i in range(len(definitions['conifer']['paper']['stocks'])):
        for prefix in ('face', 'fold'):
            mat = result[f'{prefix}-{i}']; day = mat['day']
            mat['night'] = color_mix(day, '2d5263', .55)
            mat['winter'] = day
    for key in ('trunk', 'trunk-fold'):
        result[key]['night'] = color_mix(result[key]['day'], '37566b', .45)
        result[key]['winter'] = result[key]['day']
    if len(result) > 32:
        raise ValueError('Shared stock palette exceeds native material budget')
    return result


def node(identity, commands, stock, z):
    return tree.path_node(identity, commands, stock, z)


def group(identity, children):
    return {'id': identity, 'children': children}


def smooth_path(points, closed=True):
    """Catmull–Rom contour as cubic paper cuts; no bitmap textures."""
    result = [['M', *points[0]]]
    n = len(points)
    for i in range(n if closed else n-1):
        p0 = points[(i-1) % n] if closed or i else points[0]
        p1 = points[i]; p2 = points[(i+1) % n]
        p3 = points[(i+2) % n] if closed or i+2 < n else points[-1]
        result.append(['C', p1[0]+(p2[0]-p0[0])/6, p1[1]+(p2[1]-p0[1])/6,
                       p2[0]-(p3[0]-p1[0])/6, p2[1]-(p3[1]-p1[1])/6, *p2])
    if closed:
        result.append(['Z'])
    return result


def leaf_faces(element, definition):
    f = element.form; h, w = element.height, element.width
    cy = -h*.65; ry = h*f['crown_height']*.5
    cx = h*f['lean']*.75; n = definition['construction_rules']['crown_points']
    phase = tree.stream(element.seed, 'crown-contour').uniform(-math.pi, math.pi)
    points = []
    for i in range(n):
        angle = -math.pi/2+2*math.pi*i/n
        radius = 1+f['irregularity']*(.6*math.cos(3*angle+phase)+.4*math.sin(5*angle-phase))
        points.append((cx+math.cos(angle)*w*.5*radius, cy+math.sin(angle)*ry*radius))
    top, bottom = points[0], points[n//2]
    bow = w*definition['construction_rules']['fold_bow']
    seam = ['C', top[0]+bow, top[1]+ry*.7, bottom[0]+bow, bottom[1]-ry*.7, *bottom]
    reverse = ['C', seam[3], seam[4], seam[1], seam[2], *top]
    left = smooth_path([top, *reversed(points[n//2:])], False)+[reverse, ['Z']]
    right = [['M', *top], seam]+smooth_path([bottom, *reversed(points[1:n//2]) , top], False)[1:]+[['Z']]
    return left, right


def broadleaf_geometry(definition, item, context, identity):
    h = item.height; lean = item.form['lean']*h
    width = h*(.022+.012*item.traits['age'])
    # Tapered trunk and branches are present in all states; winter reveals them.
    trunk = [['M', -width*.5, 0], ['C', -width*.4, -h*.35, lean-width*.2, -h*.7, lean, -h*.91],
             ['C', lean+width*.2, -h*.7, width*.4, -h*.35, width*.5, 0], ['Z']]
    children = [node(identity+'-trunk', trunk, 'paper', .08)]
    trunk_fold = [['M', 0, 0], ['L', lean, -h*.91], ['C', lean+width*.2, -h*.7, width*.4, -h*.35, width*.5, 0], ['Z']]
    children.append(node(identity+'-trunk-fold', trunk_fold, 'trunk', .09))
    branches = []
    count = item.form['branch_count']
    for i in range(count):
        t = .34+i*.43/max(1, count-1); side = -1 if i % 2 else 1
        x = lean*t; y = -h*t
        endx = lean*.8+side*item.width*(.22-.085*t)
        endy = -h*(t+.16)
        branches += [['M', x-1.3, y], ['C', x+side*9, y-h*.06, endx-side*6, endy+h*.035, endx, endy],
                     ['C', endx-side*3, endy+h*.04, x+side*7, y-h*.025, x+1.3, y], ['Z']]
    children.append(node(identity+'-branches', branches, 'trunk', .12))
    marks = []
    for i in range(definition['construction_rules']['bark_marks']):
        y = -h*(.12+i*.13); x = lean*(-y/h)*.5
        marks += tree.box(x-width*.35, y, width*.58, max(.8, h*.004))
    children.append(node(identity+'-bark-marks', marks, 'trunk-fold', .14))
    left, right = leaf_faces(item, definition)
    for side, path, stock, z in [('face', left, 'broad-face', .35), ('fold', right, 'broad-fold', .37)]:
        face = node(identity+'-crown-'+side, path, stock, z)
        face['show'] = {'channel': 'winter', 'min': 0, 'max': .65}
        children.append(face)
    return group(identity, children)


def grasses_geometry(definition, item, context, identity):
    f = item.form; moisture = context.moisture
    reed = moisture >= definition['construction_rules']['reed_moisture']
    h = item.height*(1.35 if reed else 1)*( .75 if context.season == 'winter' else 1)
    children = []
    for i in range(f['blades']):
        rng = tree.stream(item.seed, f'blade-{i}')
        fan = (i/max(1, f['blades']-1)-.5)*2
        length = h*(1+rng.uniform(-.22, .16))
        tipx = fan*h*f['spread']*(.55 if reed else 1)+h*f['bend']
        tipy = -length*(1-abs(fan)*(.09 if reed else .22))
        rootx = fan*h*.04; blade_width = h*f['blade_width']
        path = [['M', rootx-blade_width*.5, 0],
                ['C', rootx, -length*.4, tipx-h*.09, tipy+length*.16, tipx, tipy],
                ['C', tipx-h*.03, tipy+length*.2, rootx+blade_width*.7, -length*.3, rootx+blade_width*.5, 0], ['Z']]
        children.append(node(f'{identity}-blade-{i}', path, 'grass-face' if i % 2 else 'grass-fold', .12+i*.018))
        if reed and i in (1, f['blades']-2):
            x, y = tipx*.82, tipy*.9
            children.append(node(f'{identity}-head-{i}', tree.poly([(x-1.6, y), (x-1.9, y-9), (x+.5, y-12), (x+2, y-8), (x+1.6, y)]), 'trunk', .31+i*.01))
    return group(identity, children)


def rock_geometry(definition, item, context, identity):
    outline, faces = stone_faces(item.form)
    children = [node(f'{identity}-face-{i}', tree.poly(face), stock, .15+i*.03)
                for i, (face, stock) in enumerate(zip(faces, ['rock-face', 'paper', 'rock-fold']))]
    depth = item.height*definition['construction_rules']['snow_depth']*max(.12, context.snow)
    top = outline[1:4]
    cap = tree.poly([*top, (top[-1][0], top[-1][1]+depth), (top[0][0], top[0][1]+depth)])
    snow = node(identity+'-snow', cap, 'snow', .27)
    snow['show'] = {'channel': 'snow', 'min': .01, 'max': 1}
    children.append(snow)
    return group(identity, children)


def ridge_geometry(definition, item, context, identity):
    w, h = item.width, item.height; f = item.form
    xs = [0, .13, .25, .34, f['summit'], .58, .68, .83, 1]
    ys = [.98, .73, .63, .43, 0, .38, f['shoulder'], .76, .98]
    rng = tree.stream(item.seed, 'ridge-contour')
    top = [(w*(x-.5), -h*(1-y+(rng.uniform(-.025, .025) if i != 4 else 0))) for i, (x, y) in enumerate(zip(xs, ys))]
    foot = (w*(definition['construction_rules']['fold_foot']-.5), 0)
    left = [(-w*.5, 0), *top[:5], foot]
    right = [top[4], *top[5:], (w*.5, 0), foot]
    children = [node(identity+'-face', tree.poly(left), 'ridge-face', .1),
                node(identity+'-fold', tree.poly(right), 'ridge-fold', .12)]
    depth = h*definition['construction_rules']['snow_depth']*max(.12, context.snow)
    peak = top[4]
    reach = .35+.65*context.snow
    left = tuple(a+(b-a)*reach for a, b in zip(peak, top[3]))
    right = tuple(a+(b-a)*reach for a, b in zip(peak, top[5]))
    cap = [left, peak, right, (peak[0]+w*.035, peak[1]+depth*1.05),
           (peak[0]-w*.025, peak[1]+depth*.7)]
    snow = node(identity+'-snow', tree.poly(cap), 'snow', .2)
    snow['show'] = {'channel': 'snow', 'min': .01, 'max': 1}
    children.append(snow)
    return group(identity, children)


def cloud_geometry(definition, item, context, identity):
    f = item.form; w = item.width*(.9+context.cloud*.25); h = item.height
    n = f['lobes']
    # The upper envelope of overlapping elliptical lobes gives rounded shoulders
    # and continuous masses. Sampling the union avoids even-odd overlap holes.
    ellipses = []
    for i in range(n):
        t = i/max(1, n-1)
        center = (t-.5)*w*.61
        rx = w*(.235+.025*math.sin(math.pi*t))
        ry = h*(.58+.4*math.sin(math.pi*(t*.85+.06)))
        ry *= 1+f['asymmetry']*(t-.5)
        ellipses.append((center, rx, ry))
    points = [(-w*.5, 0)]
    for i in range(33):
        x = -w*.5+w*i/32
        upper = max((ry*math.sqrt(max(0, 1-((x-cx)/rx)**2))
                     for cx, rx, ry in ellipses), default=0)
        points.append((x, -upper))
    points += [(w*.5, 0), (w*.22, h*.025), (-w*.22, h*.025)]
    path = smooth_path(points)
    dx, dy = definition['construction_rules']['back_offset']
    back = copy.deepcopy(path)
    for command in back:
        for j in range(1, len(command), 2):
            command[j] += dx; command[j+1] += dy
    return group(identity, [node(identity+'-back', back, 'cloud-back', .1), node(identity+'-face', path, 'cloud-face', .23)])


def cubic_at(p0, p1, p2, p3, t):
    return tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for a, b, c, d in zip(p0, p1, p2, p3))


def subcubic(p0, p1, p2, p3, t):
    def lerp(a, b): return tuple(x+(y-x)*t for x, y in zip(a, b))
    a, b, c = lerp(p0, p1), lerp(p1, p2), lerp(p2, p3)
    d, e = lerp(a, b), lerp(b, c)
    return p0, a, d, lerp(d, e)


def conifer_geometry(definition, item, context, identity):
    model = tree.construct(definition, item.seed)
    result = tree.tree_geometry(definition, model, identity, 0, 0, depth=0, sheet_step=.035)
    children = result['children']
    caps = []
    for i in range(len(model.tiers)):
        left, right = children[2+i*2:4+i*2]
        peak = tuple(left['path'][0][1:]); edge = left['path'][1]; last = right['path'][-2]
        t = .22+.22*context.snow
        lc = subcubic(peak, tuple(edge[1:3]), tuple(edge[3:5]), tuple(edge[5:7]), t)
        rc = subcubic(peak, tuple(last[3:5]), tuple(last[1:3]), tuple(right['path'][-3][5:7]), t)
        inner = ((lc[3][0]+rc[3][0])/2, max(lc[3][1], rc[3][1])-.8)
        path = [['M', *lc[3]], ['C', *lc[2], *lc[1], *peak],
                ['C', *rc[1], *rc[2], *rc[3]], ['L', *inner], ['Z']]
        snow = node(f'{identity}-snow-{i}', path, 'snow', left['z']+.06)
        snow['show'] = {'channel': 'snow', 'min': .01, 'max': 1}
        caps.append(snow)
    children.extend(caps)
    result.pop('transform', None)
    return result


BUILDERS = {'broadleaf': broadleaf_geometry, 'grasses': grasses_geometry, 'rock': rock_geometry,
            'ridge': ridge_geometry, 'cloud': cloud_geometry, 'conifer': conifer_geometry}


def paths(node_):
    if 'path' in node_:
        yield node_
    for child in node_.get('children', []):
        yield from paths(child)


def rebase(node_, low, high):
    pieces = list(paths(node_))
    before = [piece['z'] for piece in pieces]
    minimum, maximum = min(before), max(before)
    for piece in pieces:
        fraction = (piece['z']-minimum)/(maximum-minimum) if maximum > minimum else .5
        piece['z'] = low+(high-low)*fraction
    return node_


def attach(node_, x, y, scale=1, motion=None):
    # Scale native path coordinates rather than relying on viewer-specific code.
    for piece in paths(node_):
        for command in piece['path']:
            for i in range(1, len(command)):
                command[i] = round(command[i]*scale, 5)
    node_['transform'] = [round(x, 5), round(y, 5), 0, 0, 0]
    if motion:
        node_['motion'] = motion
    return node_


def motion_for(family, seed):
    phase = tree.stream(seed, 'motion-phase').uniform(0, 6.2)
    if family == 'cloud':
        return dict(kind='drift', amplitude=12, period=55, phase=phase)
    if family in ('broadleaf', 'conifer', 'grasses'):
        return dict(kind='sway', amplitude={'broadleaf': .5, 'conifer': .3, 'grasses': 1.7}[family],
                    period=6+tree.stream(seed, 'motion-period').random()*3, phase=phase)
    return None


@dataclass(frozen=True)
class Habitat:
    kind: str
    horizon: float
    water_top: float
    water_bottom: float
    water_center: float
    water_half_width: float
    shore_sweep: float
    seed: int
    water_ratio: float = .16

    def edges(self, y):
        t = min(1, max(0, (y-self.water_top)/(self.water_bottom-self.water_top)))
        if self.kind == 'river':
            center = self.water_center+self.shore_sweep*math.sin(t*math.pi*2-.5)
            far = self.water_half_width*self.water_ratio
            width = far+(self.water_half_width-far)*t**1.2
            return center-width, center+width
        if self.kind == 'lake':
            width = self.water_half_width*(.7+.75*t)
            center = self.water_center+self.shore_sweep*math.sin(t*math.pi)
            return center-width, center+width
        # A single curved coastline; water occupies the right half-plane.
        edge = 245+140*t+self.shore_sweep*math.sin(t*math.pi*1.3)
        return edge, 1500

    def ground_y(self, x):
        return self.horizon+12*math.sin(x/220+self.seed%6)+6*math.sin(x/110)

    def signed_shore_distance(self, x, y):
        if y < self.water_top:
            return math.hypot(y-self.water_top, max(0, abs(x-self.water_center)-80))
        left, right = self.edges(y)
        return max(left-x, x-right)

    def on_soil(self, x, y):
        return y >= self.ground_y(x) and (y < self.water_top or self.signed_shore_distance(x, y) >= 0)


def habitat_for(definitions, recipe):
    # Scene recipes choose the domain; the water family supplies the form.
    # Placement and drawing both use this exact derived boundary model.
    item = choose_individual(definitions, 'water', recipe['seed']+910)
    terrain = dict(recipe['terrain'])
    terrain['water_center'] += item.form['offset']*.35
    terrain['water_half_width'] *= item.form['near_width']/210
    terrain['shore_sweep'] *= item.form['bend']/60
    return Habitat(**terrain, seed=recipe['seed'],
                   water_ratio=item.form['far_width']/item.form['near_width'])


def band_path(left, right):
    return tree.poly([*left, *reversed(right)])


def terrain_nodes(definition, habitat, context):
    ground = [(x, habitat.ground_y(x)) for x in range(0, 1201, 40)]
    nodes = [node('terrain-ground', tree.poly([*ground, (1200, 720), (0, 720)]), 'ground', 29.5)]
    samples = definition['construction_rules']['samples']
    ys = [habitat.water_top+(720-habitat.water_top)*i/samples for i in range(samples+1)]
    left = [(habitat.edges(y)[0], y) for y in ys]
    right = [(min(1200, habitat.edges(y)[1]), y) for y in ys]
    nodes.append(node('terrain-water', band_path(left, right), 'water', 29.6))
    shore = definition['construction_rules']['bank_width']*(.75 if habitat.kind == 'river' else 1.2)
    nodes.append(node('terrain-left-bank', band_path([(x-shore, y) for x, y in left], left), 'paper', 29.72))
    if habitat.kind != 'coast':
        nodes.append(node('terrain-right-bank', band_path(right, [(x+shore, y) for x, y in right]), 'paper', 29.72))
    count = definition['construction_rules']['ripple_count']
    for i in range(count):
        fraction = (i+1)/(count+1)
        y = habitat.water_top+(720-habitat.water_top)*fraction
        lo, hi = habitat.edges(y)
        if habitat.kind == 'coast':
            lo += 45; hi = 1190
        margin = (hi-lo)*.18
        x1, x2 = lo+margin, min(1170, hi-margin)
        path = [['M', x1, y], ['C', x1+(x2-x1)*.25, y-2, x1+(x2-x1)*.65, y+3, x2, y],
                ['L', x2-16, y+1.6], ['C', x1+(x2-x1)*.65, y+4, x1+(x2-x1)*.25, y, x1+12, y+1.6], ['Z']]
        ripple = group(f'water-ripple-{i}', [node(f'water-ripple-{i}-face', path, 'ripple', 29.66)])
        ripple['motion'] = dict(kind='drift', amplitude=2.5, period=10+i, phase=i)
        nodes.append(ripple)
    if habitat.kind == 'coast':
        # Separate landward cliff face, fitted to the same shoreline, not pasted in water.
        cliff = band_path([(x-23, y-2) for x, y in left], [(x-3, y+7) for x, y in left])
        nodes.append(node('coast-cut-bank', cliff, 'rock-fold', 29.77))
    return nodes


@dataclass(frozen=True)
class Placement:
    identity: str
    family: str
    element: Element
    x: float
    y: float
    scale: float
    density: float

    @property
    def bounds(self):
        half = self.element.width*self.scale*.57
        return self.x-half, self.y-self.element.height*self.scale, self.x+half, self.y


def placement_reasons(definitions, recipe, habitat, layer, candidate, placed):
    rules = recipe['placement']; family = definitions[candidate.family]['placement']
    x, y = candidate.x, candidate.y
    reasons = list(candidate.element.violations)
    if not family['moisture'][0] <= recipe['ecology']['moisture'] <= family['moisture'][1]:
        reasons.append('habitat_moisture')
    if not habitat.on_soil(x, y):
        reasons.append('unsupported_root')
    # Rocks need two of three footprint contacts on land; plants have narrow roots.
    radius = candidate.element.width*candidate.scale*family.get('root_radius', .02)
    support = sum(habitat.on_soil(x+offset, y) for offset in (-radius, 0, radius))
    if support < (2 if candidate.family == 'rock' else 3):
        reasons.append('unsupported_footprint')
    if layer.get('water_distance'):
        distance = habitat.signed_shore_distance(x, y)
        if not layer['water_distance'][0] <= distance <= layer['water_distance'][1]:
            reasons.append('shore_distance')
    bounds = candidate.bounds
    margin = rules['frame_margin']
    if bounds[0] < margin or bounds[2] > 1200-margin or bounds[1] < 45:
        reasons.append('frame_clearance')
    if tree.intersects(bounds, recipe['protected_opening']):
        reasons.append('protected_opening')
    if candidate.element.height*candidate.scale < rules['minimum_visible_height']:
        reasons.append('subpixel_detail')
    for other in placed:
        spacing = (candidate.element.width*candidate.scale+other.element.width*other.scale)*.5
        if candidate.family == other.family:
            required = spacing*family['spacing']
        else:
            # Small tufts can nest between trees, but cannot sit on rock footprints.
            required = spacing*(.38 if 'rock' in (candidate.family, other.family) else .13)
        if math.hypot(x-other.x, y-other.y) < required:
            reasons.append('root_spacing'); break
    return reasons


def trait_distance(a, b):
    if a.family != b.family:
        return 1
    return math.sqrt(sum((a.traits[k]-b.traits[k])**2 for k in a.traits)/len(a.traits))


def placement_losses(candidate, placed):
    tangent = crowd = similar = 0
    for other in placed:
        a, b = candidate.bounds, other.bounds
        if min(a[3], b[3]) <= max(a[1], b[1]):
            continue
        width = min(a[2]-a[0], b[2]-b[0])
        overlap = (min(a[2], b[2])-max(a[0], b[0]))/width
        tangent += math.exp(-(overlap/.1)**2)
        crowd += max(0, overlap-.68)**2
        if candidate.family == other.family:
            similar += math.exp(-trait_distance(candidate.element, other.element)**2/.06)*max(0, overlap)
    return dict(density=-math.log(max(.0001, candidate.density)), near_tangency=tangent,
                crowding=crowd, neighbor_similarity=similar, individual_quality=1-candidate.element.score)


def place_layers(definitions, recipe, habitat):
    selected = []; report = []; rejected = {}
    rules = recipe['placement']
    for layer_index, layer in enumerate(recipe['layers']):
        family = layer['family']; rng = tree.stream(recipe['seed'], f'placement-{layer_index}')
        pool = []; x0, y0, x1, y1 = layer['bounds']
        for i in range(rules['candidate_pool']):
            element = individual(definitions, family, recipe['seed']*100000+layer_index*10000+i)
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            t = (y-y0)/(y1-y0)
            scale = layer['scale'][0]+(layer['scale'][1]-layer['scale'][0])*t
            candidate = Placement('', family, element, x, y, scale, tree.density_at(layer, x, y))
            reasons = placement_reasons(definitions, recipe, habitat, layer, candidate, [])
            if reasons:
                for reason in set(reasons):
                    rejected[reason] = rejected.get(reason, 0)+1
            else:
                pool.append(candidate)
        for index in range(layer['count']):
            eligible = [item for item in pool if not placement_reasons(definitions, recipe, habitat, layer, item, selected)]
            if not eligible:
                raise ValueError(f'{recipe["name"]}: {family} placement exhausted; inspect fields/constraints')
            proposals = rng.choices(eligible, weights=[item.density for item in eligible], k=min(len(eligible), rules['alternatives']))
            def cost(item):
                losses = placement_losses(item, selected)
                return sum(losses[name]*weight for name, weight in rules['preferences'].items())
            best = min(proposals, key=cost)
            placed = Placement(f'{family}-{layer_index}-{index}', best.family, best.element, best.x, best.y, best.scale, best.density)
            report.append(dict(id=placed.identity, family=family, seed=placed.element.seed, x=placed.x, y=placed.y,
                               scale=placed.scale, support=habitat.signed_shore_distance(placed.x, placed.y),
                               losses=placement_losses(placed, selected), cost=cost(placed)))
            selected.append(placed); pool.remove(best)
    return sorted(selected, key=lambda item: (item.y, item.identity)), dict(placements=report, rejections=rejected)


def scene_document(definitions, recipe, context, placements):
    habitat = habitat_for(definitions, recipe)
    nodes = [node('scene-sky', tree.box(0, 0, 1200, 720), 'sky', 27)]
    backdrop = recipe['backdrop']
    for i in range(backdrop['cloud_count']):
        item = choose_individual(definitions, 'cloud', recipe['seed']+i*80)
        rng = tree.stream(recipe['seed'], f'cloud-anchor-{i}')
        x = 180+i*(820/max(1, backdrop['cloud_count']-1))+rng.uniform(-35, 35)
        y = rng.uniform(*backdrop['cloud_height'])
        cloud = cloud_geometry(definitions['cloud'], item, context, f'cloud-{i}')
        nodes.append(attach(rebase(cloud, 27.22+i*.04, 27.37+i*.04), x, y, motion=motion_for('cloud', item.seed)))
    for i in range(backdrop['ridge_count']):
        item = choose_individual(definitions, 'ridge', recipe['seed']+300+i*100)
        ridge = ridge_geometry(definitions['ridge'], item, context, f'ridge-{i}')
        relief = backdrop.get('relief', 1)
        for face in paths(ridge):
            for command in face['path']:
                for coordinate in range(2, len(command), 2):
                    command[coordinate] *= relief
        scale = backdrop['ridge_scale']*(1 if i else 1.3)
        x = backdrop['ridge_center']+(-90 if not i else 120)
        y = habitat.horizon+25+i*8
        nodes.append(attach(rebase(ridge, 28+i*.25, 28.2+i*.25), x, y, scale))
    nodes.extend(terrain_nodes(definitions['water'], habitat, context))
    low, high = recipe['placement']['paper_stack']
    band = (high-low)/max(1, len(placements))
    for i, placed in enumerate(placements):
        model = BUILDERS[placed.family](definitions[placed.family], placed.element, context, placed.identity)
        model = rebase(model, low+i*band, low+(i+.85)*band)
        nodes.append(attach(model, placed.x, placed.y, placed.scale, motion_for(placed.family, placed.element.seed)))
    return dict(version=1, title=recipe['name']+' · '+context.season, viewBox=[1200, 720],
                materials=palette(definitions, context),
                conditions=dict(night=1-context.daylight, winter=int(context.season == 'winter'),
                                snow=context.snow, rain=0, wind=context.wind, snowfall=0), nodes=nodes)


def water_card(definitions, element, context, identity):
    f = element.form; height = 165; samples = definitions['water']['construction_rules']['samples']
    left = []; right = []
    for i in range(samples+1):
        t = i/samples; y = -height+height*t
        center = f['offset']*.15+math.sin(t*math.pi*2-.5)*f['bend']*.18
        half = (f['far_width']+(f['near_width']-f['far_width'])*t)*.2
        left.append((center-half, y)); right.append((center+half, y))
    return group(identity, [node(identity+'-water', band_path(left, right), 'water', .1),
                            node(identity+'-bank-left', band_path([(x-4, y) for x, y in left], left), 'ground-fold', .2),
                            node(identity+'-bank-right', band_path(right, [(x+4, y) for x, y in right]), 'ground-fold', .2)])


def catalog(definitions):
    context = Context(moisture=.8)
    nodes = [node('catalog-paper', tree.box(0, 0, 1200, 720), 'paper', 27)]
    records = []
    for cell, family in enumerate(FAMILIES):
        col, row = cell % 3, cell // 3
        pool = [individual(definitions, family, 500+cell*1000+i) for i in range(150)]
        pool = [item for item in pool if not item.violations and item.score > .15]
        chosen = [max(pool, key=lambda item: item.score)]
        while len(chosen) < 3:
            chosen.append(max((item for item in pool if item not in chosen),
                              key=lambda item: min(trait_distance(item, other) for other in chosen)*(.7+.3*item.score)))
        for index, item in enumerate(chosen):
            x = col*400+80+index*120
            y = row*360+(310 if family == 'broadleaf' else 285)
            # One scale per family preserves visible size variation between individuals.
            scale = {'broadleaf': .65, 'grasses': 1.4, 'rock': 1.2,
                     'ridge': .16, 'cloud': .56, 'water': .9}[family]
            builder = water_card if family == 'water' else BUILDERS[family]
            model = builder(definitions if family == 'water' else definitions[family], item, context, f'catalog-{family}-{index}')
            nodes.append(attach(rebase(model, 28.3, 28.9), x, y, scale))
            records.append(dict(family=family, variant=index+1, seed=item.seed, form=item.form, traits=item.traits, losses=item.losses))
    return dict(version=1, title='Paper element families · three variations each', viewBox=[1200, 720],
                materials=palette(definitions, context), conditions=dict(night=0, winter=0, snow=0, rain=0, wind=0, snowfall=0), nodes=nodes), records


def check_budget(document):
    ids = set(); commands = 0; count = 0
    def walk(item, depth):
        nonlocal commands, count
        count += 1
        if item['id'] in ids or depth > 8:
            raise ValueError('Duplicate ID or excessive hierarchy')
        ids.add(item['id'])
        if 'path' in item:
            if not 0 <= item['z'] <= 48:
                raise ValueError('Paper depth outside budget')
            commands += len(item['path'])
            for command in item['path']:
                if any(not math.isfinite(v) or abs(v) > 4000 for v in command[1:]):
                    raise ValueError('Non-finite or unbounded path')
        for child in item.get('children', []):
            walk(child, depth+1)
    for item in document['nodes']:
        walk(item, 0)
    if count > 512 or commands > 20000 or len(document['materials']) > 32:
        raise ValueError('Native document work budget exceeded')
    if len(json.dumps(document).encode()) > 1048576:
        raise ValueError('Document exceeds 1 MiB')
    return dict(nodes=count, path_commands=commands, materials=len(document['materials']))


def generate(output):
    definitions = library(); output.mkdir(parents=True, exist_ok=True)
    catalog_document, catalog_report = catalog(definitions)
    budgets = {'element-catalog': check_budget(catalog_document)}
    tree.save(output/'element-catalog.json', catalog_document)
    reports = {}
    for path in sorted((ART/'scenes').glob('*.json')):
        recipe = load_json(path); habitat = habitat_for(definitions, recipe)
        placements, report = place_layers(definitions, recipe, habitat)
        reports[path.stem] = dict(recipe=recipe, **report)
        # Placement runs once; every attribute state uses the same individuals/anchors.
        for state in recipe['states']:
            context = Context(**{k: v for k, v in state.items() if k != 'name'})
            document = scene_document(definitions, recipe, context, placements)
            name = path.stem+'-'+state['name']
            budgets[name] = check_budget(document)
            tree.save(output/(name+'.json'), document)
    hashes = {str(path.relative_to(APP)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in [tree.DEFAULT_DEFINITION, *sorted((ART/'elements').glob('*.json')), *sorted((ART/'scenes').glob('*.json'))]}
    tree.save(output/'art-report.json', dict(definition_hashes=hashes, catalog=catalog_report,
                                           scenes=reports, budgets=budgets,
                                           scope='Native generative art studies. Aesthetic losses are artist-defined heuristics, not proof of beauty.'))
    print(f'Generated six element families and six scene states in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=APP.parents[1]/'output/paper-art')
    args = parser.parse_args()
    generate(args.output)

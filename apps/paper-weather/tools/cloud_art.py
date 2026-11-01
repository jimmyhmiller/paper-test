#!/usr/bin/env python3
"""WMO-informed procedural paper clouds, independent of landscape composition.

The taxonomy is data. Morphology is built from typed construction algorithms;
all output is native closed paths, backed cuts and shallow paper layers.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import argparse
import copy
import hashlib
import html
import json
import math
import tree_art as tree
from scene_art import smooth_path, check_budget

APP = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = APP/'art/clouds/taxonomy.json'
TAXONOMY = json.loads(TAXONOMY_PATH.read_text())


@dataclass(frozen=True)
class Cloud:
    genus: str
    species: str | None = None
    varieties: tuple[str, ...] = ()
    features: tuple[str, ...] = ()
    accessories: tuple[str, ...] = ()
    origin: str | None = None
    upper: str | None = None
    seed: int = 1729
    halo: bool = False

    @property
    def label(self):
        if self.upper:
            return {'nacreous': 'Nacreous clouds', 'nitric-acid-water-psc': 'Nitric acid / water PSC',
                    'noctilucent': 'Noctilucent clouds'}[self.upper]
        return ' '.join([self.genus.capitalize(), *([self.species] if self.species else []),
                         *self.varieties, *self.features, *self.accessories,
                         *([self.origin] if self.origin else []), *(['· halo example'] if self.halo else [])])


def validate(spec):
    if not isinstance(spec.seed, int) or isinstance(spec.seed, bool) or not 0 <= spec.seed < 2**53:
        raise ValueError('Cloud seed must be a bounded integer')
    if spec.halo and spec.genus != 'cirrostratus':
        raise ValueError('This atlas only associates its halo example with Cirrostratus')
    if spec.upper:
        if spec.upper not in TAXONOMY['upper'] or spec.genus != 'upper' or any((spec.species, spec.varieties, spec.features, spec.accessories, spec.origin)):
            raise ValueError('Upper-atmospheric cases have their own construction, not tropospheric modifiers')
        return
    genera = TAXONOMY['genera']
    if spec.genus not in genera:
        raise ValueError('Unknown cloud genus')
    if spec.species is not None and spec.species not in genera[spec.genus]['species']:
        raise ValueError(f'Invalid species {spec.species} for {spec.genus}')
    for field in ('varieties', 'features', 'accessories'):
        names = getattr(spec, field)
        if len(set(names)) != len(names):
            raise ValueError(f'Duplicate cloud {field}')
        for name in names:
            if spec.genus not in TAXONOMY[field].get(name, []):
                raise ValueError(f'{name} is outside the WMO common-association table for {spec.genus}')
    if {'opacus', 'translucidus'} <= set(spec.varieties):
        raise ValueError('Opacus and translucidus are mutually exclusive opacity choices')
    arrangements = set(spec.varieties) & set(TAXONOMY['grammar_limits']['arrangement_choices'])
    structural = set(spec.features) & set(TAXONOMY['grammar_limits']['structural_feature_choices'])
    if len(arrangements) > 1:
        raise ValueError('This art grammar supports one arrangement operator at a time')
    if structural and (arrangements or spec.origin):
        raise ValueError('Structural-layer features cannot yet be combined with an arrangement or origin recipe')
    if len(structural) > 1:
        raise ValueError('This art grammar supports one structural cloud-layer feature at a time')
    if 'cauda' in spec.features and 'murus' not in spec.features:
        raise ValueError('A cauda must attach to a murus')
    if spec.origin and spec.genus not in TAXONOMY['origins'].get(spec.origin, []):
        raise ValueError('Unsupported origin/genus association')


def from_mapping(data):
    if not isinstance(data, dict):
        raise ValueError('Cloud specification must be an object')
    allowed = set(Cloud.__dataclass_fields__)
    if set(data)-allowed or 'genus' not in data:
        raise ValueError('Unknown cloud fields or missing genus')
    values = dict(data)
    for name in ('genus', 'species', 'origin', 'upper'):
        if name in values and values[name] is not None and not isinstance(values[name], str):
            raise ValueError(f'{name} must be a name string')
    for name in ('varieties', 'features', 'accessories'):
        if name in values:
            if not isinstance(values[name], list) or not all(isinstance(v, str) for v in values[name]):
                raise ValueError(f'{name} must be an array of names')
            values[name] = tuple(values[name])
    if 'halo' in values and not isinstance(values['halo'], bool):
        raise ValueError('halo must be boolean')
    spec = Cloud(**values)
    validate(spec)
    return spec


def palette():
    colors = {
        'paper': 'f3ead9', 'sky': 'bfd9e1', 'sky-soft': 'cbdfe3', 'sky-storm': '9fb4bf',
        'sky-night': '243c59', 'white': 'f4efe2', 'ice': 'eef1e9', 'ice-soft': 'e0eae8',
        'veil': 'd4e3e5', 'veil-light': 'dfebe9', 'cloud': 'f0e9db', 'under': 'bbcbd0',
        'shade': '9db4c0', 'dark': '819baa', 'storm': '728b9f', 'rain': '839fac',
        'sun': 'e9dfbd', 'sun-muted': 'd7d9cb', 'halo': 'e8e8d7',
        'rose': 'd6c1c4', 'lilac': 'b7bed1', 'aqua': 'bedcd9', 'pearl': 'e0d6c2',
        'night-ice': 'c0dded', 'night-shadow': '789fb7', 'smoke': 'a9a69e'
    }
    return {key: dict(day=int(value, 16), night=int(value, 16), winter=int(value, 16))
            for key, value in colors.items()}


def ellipse(cx, cy, rx, ry):
    k = .5522847498
    return [['M', cx+rx, cy], ['C', cx+rx, cy+k*ry, cx+k*rx, cy+ry, cx, cy+ry],
            ['C', cx-k*rx, cy+ry, cx-rx, cy+k*ry, cx-rx, cy],
            ['C', cx-rx, cy-k*ry, cx-k*rx, cy-ry, cx, cy-ry],
            ['C', cx+k*rx, cy-ry, cx+rx, cy-k*ry, cx+rx, cy], ['Z']]


def translate(path, dx, dy):
    result = copy.deepcopy(path)
    for command in result:
        for i in range(1, len(command), 2):
            command[i] += dx; command[i+1] += dy
    return result


def ribbon(points, width, taper=True):
    left, right = [], []
    for i, (x, y) in enumerate(points):
        before, after = points[max(0, i-1)], points[min(len(points)-1, i+1)]
        dx, dy = after[0]-before[0], after[1]-before[1]
        length = math.hypot(dx, dy) or 1
        t = i/(len(points)-1)
        radius = width*.5*(max(.025, math.sin(math.pi*t)**.7) if taper else 1)
        left.append((x-dy/length*radius, y+dx/length*radius))
        right.append((x+dy/length*radius, y-dx/length*radius))
    return smooth_path([*left, *reversed(right)])


def cubic(p0, p1, p2, p3, count=30):
    return [tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
                  for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i/count for i in range(count+1))]


def puff_path(cx, base, width, height, seed, ragged=0):
    """A rounded union envelope, not a row of pointed interpolation peaks."""
    rng = tree.stream(seed, 'cloud-domes')
    lobes = [(cx+width*offset, width*rx, height*ry)
             for offset, rx, ry in [(-.29, .23, .62), (-.04, .31, 1), (.27, .25, .76)]]
    lobes = [(x+width*rng.uniform(-.025, .025), rx, ry*rng.uniform(.94, 1.05)) for x, rx, ry in lobes]
    points = []
    for i in range(41):
        x = cx-width*.52+width*1.04*i/40
        y = max((ry*math.sqrt(max(0, 1-((x-lx)/rx)**2)) for lx, rx, ry in lobes), default=0)
        points.append((x, base-y))
    for i in range(12, -1, -1):
        x = cx-width*.52+width*1.04*i/12
        y = base+ragged*(.5+.5*math.sin(i*2.7+seed))
        points.append((x, y))
    return smooth_path(points)


def sheet_path(y, thickness, wave=8, phase=0, x0=50, x1=950, rough=0):
    upper, lower = [], []
    for i in range(23):
        t = i/22; x = x0+(x1-x0)*t
        edge = math.sin(t*math.pi)**.4
        upper.append((x, y-thickness*.5*edge+wave*math.sin(t*math.pi*2+phase)))
        lower.append((x, y+thickness*.5*edge+rough*math.sin(t*math.pi*8+phase)))
    return smooth_path([*upper, *reversed(lower)])


def cloudlet_path(cx, cy, width, height, seed):
    phase = tree.stream(seed, 'cell-contour').uniform(-math.pi, math.pi)
    points = []
    for i in range(20):
        a = math.pi*2*i/20
        radius = 1+.075*math.cos(3*a+phase)+.035*math.sin(5*a-phase)
        points.append((cx+math.cos(a)*width*.5*radius, cy+math.sin(a)*height*.5*radius))
    return smooth_path(points)


def deck_path(top, bottom, wave=6, phase=0, ragged=0):
    # A sky-spanning sheet has lateral continuation, not a closed lens outline.
    points = [(0, top), (1000, top)]
    for i in range(30, -1, -1):
        t = i/30
        points.append((1000*t, bottom+wave*math.sin(t*math.pi*2+phase)+ragged*math.sin(t*math.pi*11)))
    return tree.poly(points)


def tower_edges(seed, deep):
    rng = tree.stream(seed, 'updraft-contour')
    lobes = [(500, 316, 195 if deep else 164, 45), (434, 250, 107, 105),
             (550, 215, 113, 118), (478, 143, 94, 112), (514, 87, 77, 72)]
    lobes = [(x+rng.uniform(-6, 6), y, rx, ry) for x, y, rx, ry in lobes]
    left, right = [], []
    for i in range(66):
        y = 18+(356-18)*i/65
        intervals = [(x-rx*math.sqrt(max(0, 1-((y-cy)/ry)**2)), x+rx*math.sqrt(max(0, 1-((y-cy)/ry)**2)))
                     for x, cy, rx, ry in lobes if abs(y-cy) <= ry]
        if intervals:
            left.append((min(a for a, b in intervals), y))
            right.append((max(b for a, b in intervals), y))
    return left, right


def tower_path(seed, deep):
    left, right = tower_edges(seed, deep)
    return smooth_path([*left, *reversed(right)])


class Builder:
    def __init__(self, spec):
        self.spec = spec; self.nodes = []; self.counter = 0
        self.rng = tree.stream(spec.seed, 'cloud-structure')
        self.metrics = {'cloudlet_widths': [], 'intrinsic_shading': False, 'construction': None, 'cloudlet_centers': [], 'fiber_directions': []}
        self.anchors = dict(base=(500, 310), top=(500, 160), width=650, height=160)
        self.traits = {} if spec.upper else {name: tree.stream(spec.seed, name).uniform(*bounds)
                          for name, bounds in TAXONOMY['genera'][spec.genus]['traits'].items()}

    def add(self, path, stock='white', z=.2, name='piece'):
        self.counter += 1
        result = dict(id=f'{name}-{self.counter}', path=path, material=stock, z=z)
        self.nodes.append(result)
        return result

    def fiber(self, points, width=4, stock='ice', z=.23, name='filament'):
        self.metrics['fiber_directions'].append(math.atan2(points[-1][1]-points[0][1], points[-1][0]-points[0][0]))
        return self.add(ribbon(points, width), stock, z, name)

    def puff(self, x, y, width, height, shade=True, seed=None, ragged=0, stock='white', z=.2):
        seed = self.spec.seed+self.counter if seed is None else seed
        path = puff_path(x, y, width, height, seed, ragged)
        if shade:
            self.add(translate(path, 0, 5), 'under' if self.spec.genus != 'stratocumulus' else 'shade', z, 'underside')
            self.metrics['intrinsic_shading'] = True
        self.add(path, stock, z+.045, 'dome')
        return path

    def filaments(self):
        self.metrics['construction'] = 'tapered-fibers'
        species = self.spec.species
        if 'vertebratus' in self.spec.varieties:
            self.fiber(cubic((120, 310), (380, 260), (620, 210), (875, 125)), 7)
            for i in range(11):
                t = (i+1)/13; x = 120+755*t; y = 310-185*t
                for sign in (-1, 1):
                    self.fiber(cubic((x-100, y+sign*65), (x-45, y+sign*70), (x+15, y+sign*10), (x+30, y-5)), 4)
            return
        if species == 'uncinus':
            for group in range(4):
                px = 210+group*160+self.rng.uniform(-15, 15)
                py = 200+self.rng.uniform(-35, 40)
                for strand in range(4):
                    offset = strand*5
                    points = cubic((px-140-strand*12, py+110+offset), (px-85, py+70+offset), (px+15, py+60), (px+48, py-10))
                    points += cubic(points[-1], (px+85, py-65), (px+8, py-78), (px+9, py-28), 16)[1:]
                    self.fiber(points, 12 if strand == 0 else 3.8, 'ice', .18+strand*.003)
            return
        dense = species == 'spissatus'
        for i in range((18 if dense else 12)+round(self.traits['density']*7)):
            group = i % 3
            y = 175+group*39+self.rng.uniform(-22, 22)
            start = 70+group*60+self.rng.uniform(0, 190)
            end = 770+self.rng.uniform(-70, 130)
            rise = self.rng.uniform(25, 65)+self.traits['curvature']*100
            if 'intortus' in self.spec.varieties:
                points = [(start+(end-start)*j/40, y+34*math.sin(j/40*math.pi*3+i*.17)-j/40*rise) for j in range(41)]
            else:
                points = cubic((start, y+45), (start+190, y-9), (end-160, y+8), (end, y-rise))
            self.fiber(points, self.rng.uniform(14, 25) if dense else self.rng.uniform(3, 9),
                       'ice-soft' if dense and i % 3 == 0 else 'ice', .18+i*.002)

    def cloudlets(self):
        genus = self.spec.genus
        self.metrics['construction'] = 'cloudlet-field'
        cols, rows, width, height = {'cirrocumulus': (14, 5, 43, 15),
                                    'altocumulus': (8, 4, 100, 39),
                                    'stratocumulus': (5, 3, 190, 87)}[genus]
        if genus == 'stratocumulus' or 'opacus' in self.spec.varieties:
            self.add(sheet_path(255, 145, 18, .7, 70, 940, 4), 'under', .1, 'connected-cloud-bank')
        if 'opacus' in self.spec.varieties: width *= 1.3
        if 'perlucidus' in self.spec.varieties: width *= .76
        for row in range(rows):
            perspective = .68+.32*row/max(1, rows-1)
            for col in range(cols):
                if self.rng.random() < .18-.14*self.traits['density'] and 0 < col < cols-1: continue
                x = 105+800*(col+.4*(row % 2))/cols+self.rng.uniform(-15, 15)
                y = 135+row*190/max(1, rows-1)+self.rng.uniform(-10, 10)
                y += 9*math.sin(col*.7+row*.5)
                if 'radiatus' in self.spec.varieties:
                    depth = .25+.75*row/max(1, rows-1)
                    x = 500+(x-500)*depth; y = 100+depth*245; perspective = depth
                if 'undulatus' in self.spec.varieties: y += 22*math.sin(col*.7+row*.4)
                w = width*perspective*self.traits['spread']*self.rng.uniform(.79, 1.18)
                h = height*perspective*self.rng.uniform(.8, 1.2)
                path = cloudlet_path(x, y, w, h, self.spec.seed+row*100+col)
                if genus != 'cirrocumulus':
                    self.add(translate(path, -1, 5), 'under' if genus == 'altocumulus' else 'shade', .15+row*.014, 'cell-underside')
                    self.metrics['intrinsic_shading'] = True
                self.add(path, 'ice' if genus == 'cirrocumulus' else 'cloud', .18+row*.014, 'rounded-cell')
                self.metrics['cloudlet_widths'].append(w)
                self.metrics['cloudlet_centers'].append((x, y))
        self.anchors.update(base=(500, 335), top=(500, 100), width=800, height=235)

    def lenticular(self):
        self.metrics['construction'] = 'tapered-lens'
        width, height = {'cirrocumulus': (560, 52), 'altocumulus': (680, 88), 'stratocumulus': (790, 115)}[self.spec.genus]
        width *= self.traits['spread']
        height *= .85+.25*self.traits['density']
        for i, factor in enumerate((1, .78, .48)):
            w = width*factor; y = 287-i*height*.29
            h = height*(.36 if i else .48)
            path = [['M', 500-w/2, y], ['C', 500-w*.31, y-h, 500+w*.29, y-h, 500+w/2, y],
                    ['C', 500+w*.27, y+h*.36, 500-w*.29, y+h*.36, 500-w/2, y], ['Z']]
            self.add(translate(path, 0, 5), 'ice-soft' if self.spec.genus == 'cirrocumulus' else 'under', .1+i*.035, 'lens-backing')
            self.add(path, 'ice' if self.spec.genus == 'cirrocumulus' else 'white', .12+i*.035, 'lens')
        self.anchors.update(base=(500, 300), top=(500, 200), width=width, height=height)

    def roll(self):
        self.metrics['construction'] = 'detached-cylinder'
        w = 730*self.traits['spread']; half = w*.5
        self.add(ellipse(500, 255, half, 57), 'under', .14, 'roll-body')
        upper = [['M', 500-half, 255], ['C', 500-w*.48, 190, 500+w*.48, 190, 500+half, 255],
                 ['C', 500+w*.42, 238, 500-w*.42, 238, 500-half, 255], ['Z']]
        self.add(upper, 'white', .19, 'roll-highlight')
        self.add(ribbon([(500-w*.47+i*w*.94/30, 280+4*math.sin(i/30*math.pi*3)) for i in range(31)], 13), 'shade', .2, 'roll-underside')
        self.anchors.update(base=(500, 310), top=(500, 198), width=w, height=112)

    def turrets(self):
        self.metrics['construction'] = 'common-base-turrets'
        high = self.spec.genus in ('cirrus', 'cirrocumulus')
        self.add(sheet_path(310, 30, 4, 0, 150, 850), 'ice' if high else 'under', .14, 'common-base')
        for i in range(6):
            x = 210+i*115+self.rng.uniform(-12, 12)
            height = self.rng.uniform(95, 170)*( .7 if high else 1)
            width = self.rng.uniform(62, 83)*( .8 if high else 1)
            self.puff(x, 305, width, height, not high, z=.18)
            if high:
                for j in range(2):
                    self.fiber(cubic((x, 300), (x-15, 330), (x+30, 330), (x+50, 345)), 2.5)
        self.anchors.update(base=(500, 315), top=(500, 135), width=700, height=180)

    def tufts(self):
        self.metrics['construction'] = 'ragged-separated-tufts'
        high = self.spec.genus in ('cirrus', 'cirrocumulus')
        for i in range(7):
            x = 175+i*100+self.rng.uniform(-10, 10)
            y = 220+(i % 2)*62+self.rng.uniform(-10, 10)
            w = self.rng.uniform(63, 95)*( .7 if high else 1)
            self.puff(x, y, w, w*.7, not high, ragged=8, z=.18)
            for j in range(3):
                self.fiber(cubic((x-15+j*11, y), (x-5+j*11, y+20), (x+30+j*11, y+27), (x+45+j*11, y+35)), 2.6, 'ice-soft', .17)

    def fragments(self, count=9, y=250):
        if self.spec.genus == 'cumulus' and count == 9: count = 7
        self.metrics['construction'] = 'torn-fragments'
        for i in range(count):
            x = 130+i*740/max(1, count-1)+self.rng.uniform(-16, 16)
            cy = y+self.rng.uniform(-38, 38)
            w = self.rng.uniform(52, 115); h = self.rng.uniform(20, 48)*(1.2 if self.spec.genus == 'cumulus' else .65)
            points = []
            for j in range(15):
                a = j*math.pi*2/15
                factor = 1+.25*math.sin(j*2.6+i)+self.rng.uniform(-.12, .12)
                points.append((x+math.cos(a)*w*.5*factor, cy+math.sin(a)*h*.5*factor))
            self.add(smooth_path(points), 'under' if self.spec.genus == 'stratus' else 'cloud', .2+i*.001, 'ragged-patch')

    def veil(self):
        genus = self.spec.genus
        self.metrics['construction'] = 'fibrous-veil' if genus == 'cirrostratus' else 'layer-sheet'
        if genus == 'cirrostratus':
            self.add(deck_path(0, 460, 2+self.traits['density']*2, self.traits['curvature']*8), 'veil', .12, 'extensive-thin-veil')
            if self.spec.species == 'fibratus':
                for i in range(15):
                    y = 85+i*20+self.rng.uniform(-7, 7)
                    self.fiber(cubic((25, y+20), (300, y-12), (690, y+18), (975, y-30)), self.rng.uniform(6, 12), 'ice-soft', .15)
            return
        if genus == 'altostratus':
            self.add(deck_path(0, 460, 2, .7), 'under', .12, 'extensive-midlevel-sheet')
            self.add(deck_path(0, 330+40*self.traits['density'], 12, 1.2+self.traits['curvature']*8), 'veil', .16, 'diffuse-upper-layer')
            for i in range(6):
                y = 120+i*39+self.rng.uniform(-9, 9)
                self.fiber(cubic((25, y), (300, y-15), (700, y+20), (975, y-5)), 4, 'ice-soft', .18)
            if 'opacus' not in self.spec.varieties:
                self.add(ellipse(670, 200, 27, 27), 'sun-muted', .2, 'diffuse-sun')
            return
        if genus == 'stratus':
            self.add(deck_path(0, 460, 2+self.traits['density']*2, self.traits['curvature']*8), 'under', .13, 'low-uniform-layer')
            self.add(deck_path(0, 310+35*self.traits['density'], 3, .8+self.traits['curvature']*8), 'veil', .16, 'feature-poor-layer')
            return
        self.add(deck_path(0, 275+25*self.traits['density'], 12, .7+self.traits['curvature']*8, 8), 'storm', .14, 'opaque-rain-deck')
        self.add(deck_path(0, 125, 15, 1.4), 'dark', .18, 'rain-deck-contour')
        self.anchors.update(base=(500, 295), top=(500, 8), width=1000, height=287)
        for i in range(4):
            self.add(cloudlet_path(170+i*220, 329+self.rng.uniform(-5, 5), 130, 37, self.spec.seed+i), 'shade', .2, 'scud')

    def cumulus(self, deep=False):
        self.metrics['construction'] = 'deep-convective-column' if deep else 'convective-domes'
        species = self.spec.species
        if not deep and species == 'humilis':
            self.puff(500, 318, 500*self.traits['spread'], 115, True, z=.18)
            self.anchors.update(base=(500, 320), top=(500, 203), width=500, height=117)
            return
        if not deep and species == 'mediocris':
            self.puff(500, 325, 430*self.traits['spread'], 207, True, z=.18)
            self.anchors.update(base=(500, 325), top=(500, 118), width=430, height=207)
            return
        base = 350; width = 390 if deep else 340
        path = tower_path(self.spec.seed, deep)
        self.add(translate(path, 0, 5), 'under', .15, 'convective-underside')
        self.add(path, 'white', .19, 'continuous-updraft-body')
        # A restrained side contour gives volume without breaking the tower into icons.
        _, edge = tower_edges(self.spec.seed, deep)
        segment = [(x, y) for x, y in edge if 155 <= y <= 348]
        side = smooth_path([*segment, (575, 345), (558, 280), (570, 215)])
        self.add(side, 'ice-soft', .22, 'column-side-contour')
        if deep:
            self.add(sheet_path(350, 27, 2, .2, 290, 710), 'storm', .3, 'dark-convective-base')
            if species == 'calvus':
                self.add(ellipse(500, 97, 90, 43), 'white', .3, 'smooth-glaciating-crown')
            else:
                self.add(sheet_path(100, 54, 7, .4, 330, 690), 'ice', .29, 'fibrous-ice-crown')
                for i in range(8):
                    y = 83+i*7
                    self.fiber(cubic((360, y+15), (480, y-5), (660, y+5), (750+i*5, y-12)), 4, 'ice', .31)
        self.anchors.update(base=(500, 350), top=(500, 20), width=width, height=330)

    def base(self):
        s, g = self.spec.species, self.spec.genus
        if s == 'lenticularis': return self.lenticular()
        if s == 'volutus': return self.roll()
        if s == 'castellanus': return self.turrets()
        if s == 'floccus': return self.tufts()
        if s == 'fractus': return self.fragments()
        if g == 'cirrus': return self.filaments()
        if g in ('cirrocumulus', 'altocumulus', 'stratocumulus'): return self.cloudlets()
        if g in ('cirrostratus', 'altostratus', 'stratus', 'nimbostratus'): return self.veil()
        return self.cumulus(g == 'cumulonimbus')

    def anvil(self):
        path = [['M', 350, 134], ['C', 315, 117, 255, 104, 180, 73],
                ['C', 340, 55, 640, 54, 850, 72], ['C', 785, 103, 660, 132, 610, 146],
                ['C', 525, 128, 430, 128, 350, 134], ['Z']]
        self.add(path, 'ice', .34, 'anvil')
        for i in range(9):
            y = 66+i*6
            self.fiber(cubic((300, y), (450, y-7), (700, y+12), (880, y-4)), 3.6, 'ice-soft', .35, 'anvil-fiber')

    def falling(self, ground=False):
        _, base = self.anchors['base']
        for i in range(17):
            base_x = self.anchors['base'][0]
            x = base_x-self.anchors['width']*.43+i*self.anchors['width']*.86/16+self.rng.uniform(-3, 3)
            length = self.rng.uniform(83, 125) if ground else self.rng.uniform(48, 87)
            end = 440 if ground else min(405, base+length)
            self.fiber(cubic((x, base-3), (x+5, base+length*.25), (x+15, end-20), (x+22, end)),
                       3.2 if ground else 4.4, 'rain', .12, 'rain-to-ground' if ground else 'evaporating-fallstreak')
        if ground:
            self.add(tree.box(120, 442, 760, 1.3), 'under', .12, 'ground-reference')

    def features(self, mode='all'):
        structural = [name for name in self.spec.features if name in ('cavum', 'asperitas', 'fluctus')]
        additive = [name for name in self.spec.features if name not in structural]
        selected = structural if mode == 'structural' else additive if mode == 'additive' else [*structural, *additive]
        for name in selected:
            x, y = self.anchors['base']
            if name == 'incus': self.anvil()
            elif name in ('virga', 'praecipitatio'): self.falling(name == 'praecipitatio')
            elif name == 'mamma':
                for i in range(9):
                    px = x-self.anchors['width']*.4+i*self.anchors['width']*.8/8; depth = self.rng.uniform(28, 61)
                    path = [['M', px-24, y-4], ['C', px-24, y+depth, px+22, y+depth, px+24, y-4], ['Z']]
                    stock = 'ice' if self.spec.genus == 'cirrocumulus' else 'under' if i % 3 else 'shade'
                    self.add(path, stock, .32+i*.001, 'pendant-pouch')
            elif name == 'arcus':
                self.add(sheet_path(y+17, 47, 12, 0, 160, 840, 5), 'shade', .33, 'attached-shelf')
                self.add(sheet_path(y+8, 17, 11, 0, 170, 830), 'under', .34, 'shelf-lip')
            elif name == 'tuba':
                path = [['M', 535, y-7], ['C', 535, y+22, 570, y+46, 582, 435],
                        ['C', 557, y+55, 500, y+33, 499, y-7], ['Z']]
                self.add(path, 'storm', .34, 'condensation-funnel')
            elif name == 'murus':
                path = [['M', 380, y-5], ['C', 395, y+22, 400, y+42, 425, y+45],
                        ['L', 515, y+38], ['C', 540, y+25, 550, y+7, 550, y-5], ['Z']]
                self.add(path, 'dark', .34, 'wall-lowering')
            elif name == 'cauda':
                self.add(ribbon(cubic((510, y+33), (570, y+24), (640, y+39), (715, y+12)), 26), 'under', .35, 'wall-tail')
            elif name == 'fluctus':
                self.nodes.clear()
                self.add(sheet_path(293, 49, 5, .2, 130, 885), 'under', .2, 'wave-supporting-layer')
                for i in range(5):
                    px = 235+i*120; py = 259
                    points = cubic((px-50, py+12), (px-10, py+10), (px+5, py-56), (px+30, py-60))
                    points += cubic(points[-1], (px+70, py-67), (px+73, py-20), (px+30, py-18), 18)[1:]
                    self.fiber(points, 20, 'white', .36, 'breaking-wave-crest')
            elif name == 'asperitas':
                self.nodes.clear()
                self.add(deck_path(65, 390, 20, .6, 12), 'under', .2, 'turbulent-layer')
                for i in range(5):
                    points = [(35+j*930/36, 150+i*43+24*math.sin(j/36*math.pi*3.7+i*.83)+11*math.sin(j/36*math.pi*7+i)) for j in range(37)]
                    self.add(ribbon(points, 40, False), ('shade', 'under', 'dark', 'under', 'shade')[i], .31+i*.012, 'turbulent-undulation')
            elif name == 'cavum':
                # Replace the local layer with one real cut aperture. No sky-coloured patch.
                self.nodes.clear()
                sheet = deck_path(55, 365, 10, .5)
                sheet += ellipse(525, 225, 145, 64)
                self.add(sheet, 'ice-soft', .2, 'perforated-cloud-layer')
                for i in range(10):
                    px = 460+i*13
                    self.fiber(cubic((px, 225), (px+5, 270), (px+17, 290), (px+34, 318)), 3, 'white', .24, 'hole-ice-fallstreak')

    def varieties(self):
        names = self.spec.varieties
        if 'lacunosus' in names:
            self.nodes.clear()
            sheet = deck_path(95, 360, 8, .7)
            for row in range(3):
                for col in range(7):
                    cx = 185+col*105+self.rng.uniform(-8, 8); cy = 178+row*53+self.rng.uniform(-5, 5)
                    sheet += ellipse(cx, cy, self.rng.uniform(27, 38), self.rng.uniform(13, 18))
            self.add(sheet, 'ice' if self.spec.genus == 'cirrocumulus' else 'under', .2, 'cellular-perforated-layer')
        if 'undulatus' in names and self.spec.genus not in ('cirrocumulus', 'altocumulus', 'stratocumulus'):
            self.nodes.clear()
            for i in range(6):
                points = [(90+j*820/35, 140+i*32+12*math.sin(j/35*math.pi*2.4+i*.25)) for j in range(36)]
                self.add(ribbon(points, 20, False), 'veil' if self.spec.genus == 'cirrostratus' else ('under' if i % 2 else 'veil'), .15+i*.007, 'parallel-wave-band')
        if 'radiatus' in names and self.spec.genus in ('cirrus', 'altostratus'):
            self.nodes.clear()
            for i in range(8):
                x = 150+i*100
                self.fiber(cubic((500+(x-500)*.12, 100), (500+(x-500)*.35, 170), (x, 280), (x, 365)),
                           4 if self.spec.genus == 'cirrus' else 23, 'ice' if self.spec.genus == 'cirrus' else 'veil', .2, 'converging-band')
        if 'radiatus' in names and self.spec.genus == 'cumulus':
            self.nodes.clear()
            for row in range(4):
                factor = .3+.7*row/3
                for col in range(3):
                    self.puff(500+(col-1)*250*factor, 120+row*75, 150*factor, 65*factor, True, z=.16+row*.01)
        if 'duplicatus' in names:
            previous = copy.deepcopy(self.nodes)
            for node in self.nodes:
                node['path'] = [[command[0], *[500+(v-500)*.88-12 if j%2==0 else 230+(v-230)*.7-40 for j, v in enumerate(command[1:])]] for command in node['path']]
                node['material'] = 'ice-soft' if self.spec.genus.startswith('cirro') else 'veil'
            for item in previous:
                second = [[command[0], *[500+(v-500)*.88+12 if j%2==0 else 230+(v-230)*.7+40 for j, v in enumerate(command[1:])]] for command in item['path']]
                self.add(second, item['material'], item['z']+.055, 'second-layer')
        if 'opacus' in names:
            for item in self.nodes:
                if item['material'] in ('white', 'veil', 'ice-soft'):
                    item['material'] = 'under'
        if 'translucidus' in names:
            for item in self.nodes:
                if item['material'] in ('under', 'shade'):
                    item['material'] = 'veil'
            if not any('sun' in item['id'] for item in self.nodes):
                self.add(ellipse(670, 205, 25, 25), 'sun-muted', .3, 'sun-through-thin-layer')

    def accessories(self):
        topx, topy = self.anchors['top']; x, y = self.anchors['base']
        for name in self.spec.accessories:
            if name == 'pileus':
                self.add(ellipse(topx+5, max(25, topy-12), 123, 14), 'ice-soft', .4, 'small-cap')
                self.add(ellipse(topx+5, max(23, topy-15), 115, 9), 'ice', .41, 'cap-face')
            elif name == 'velum':
                self.add(sheet_path(topy+22, 24, 7, 0, 195, 820), 'veil-light', .36, 'wide-accessory-veil')
            elif name == 'pannus':
                for i in range(5):
                    px = 230+i*130; py = y+24+self.rng.uniform(0, 18)
                    self.add(puff_path(px, py, self.rng.uniform(55, 100), 20, self.spec.seed+i, 12), 'shade', .38, 'ragged-scud')
            elif name == 'flumen':
                self.add(ribbon(cubic((875, y+45), (780, y+18), (640, y+38), (535, y+6)), 33), 'under', .38, 'inflow-band')

    def special(self):
        origin = self.spec.origin
        if not origin:
            return
        if origin == 'homogenitus' and self.spec.genus == 'cirrus':
            self.nodes.clear()
            for offset in (-5, 5):
                points = cubic((115, 300+offset), (360, 240+offset), (680, 200+offset), (905, 135+offset))
                self.fiber(points, 8, 'ice', .2, 'aircraft-condensation-trail')
            return
        if origin == 'homomutatus':
            self.nodes.clear()
            for i in range(16):
                y = 170+i*8
                self.fiber(cubic((120, y+35), (420, y-25), (680, y+35), (900, y-15)), self.rng.uniform(5, 14), 'ice-soft', .2+i*.001, 'spread-contrail-fiber')
            return
        if origin in ('flammagenitus', 'homogenitus'):
            for i in range(5):
                cy = 415-i*25
                self.puff(500+i*2, cy, 26+i*15, 35, False, ragged=5, stock='smoke' if origin == 'flammagenitus' else 'veil', z=.1+i*.005)
        elif origin in ('cataractagenitus', 'silvagenitus'):
            for i in range(7):
                px = 285+i*70
                self.fiber(cubic((px, 430), (px-13, 380), (px+25, 360), (px+40, 310)), 15, 'veil-light', .16, 'localized-source-mist')

    def upper(self):
        self.metrics['construction'] = self.spec.upper
        phase = tree.stream(self.spec.seed, 'upper-flow').uniform(-1, 1)
        if self.spec.upper == 'nacreous':
            for i, stock in enumerate(('lilac', 'aqua', 'rose', 'pearl', 'ice')):
                self.add(sheet_path(275-i*20, 52-i*3, 8, i*.3+phase, 150+i*30, 875-i*25), stock, .13+i*.018, 'pearly-lamina')
        elif self.spec.upper == 'nitric-acid-water-psc':
            self.add(sheet_path(230, 190, 9, .2+phase, 40, 960), 'veil', .13, 'pale-stratospheric-veil')
            self.add(sheet_path(210, 125, 7, .9+phase, 80, 930), 'veil-light', .15, 'smooth-stratospheric-layer')
        else:
            for row in range(9):
                points = [(70+j*860/40, 130+row*22+14*math.sin(j/40*math.pi*3+row*.21+phase)) for j in range(41)]
                self.add(ribbon(points, 4+row*.4), 'night-ice', .16+row*.003, 'mesospheric-silver-ripple')
            for i in range(8):
                y = 170+i*15
                self.fiber(cubic((130, y), (400, y-15), (680, y+40), (880, y-20)), 2.2, 'night-shadow', .2, 'fine-mesospheric-thread')

    def preference_diagnostics(self):
        # Measurable art heuristics, not a beauty or meteorological classifier.
        tiny = 0
        for item in self.nodes:
            points = [(c[i], c[i+1]) for c in item['path'] for i in range(1, len(c), 2)]
            if max(max(x for x, y in points)-min(x for x, y in points),
                   max(y for x, y in points)-min(y for x, y in points)) < 5:
                tiny += 1
        angles = self.metrics['fiber_directions']
        coherence = 0
        if len(angles) > 1:
            coherence = 1-abs(complex(sum(math.cos(2*a) for a in angles),
                                    sum(math.sin(2*a) for a in angles)))/len(angles)
        centers = self.metrics['cloudlet_centers']
        grid_loss = 0
        if len(centers) > 2:
            nearest = [min(math.dist(a, b) for j, b in enumerate(centers) if i != j)
                       for i, a in enumerate(centers)]
            mean = sum(nearest)/len(nearest)
            cv = math.sqrt(sum((d-mean)**2 for d in nearest)/len(nearest))/mean
            self.metrics['nearest_neighbor_cv'] = cv
            grid_loss = max(0, (.12-cv)/.12)**2
        span = max(n['z'] for n in self.nodes)-min(n['z'] for n in self.nodes)
        signature_loss = int(self.spec.genus == 'cirrocumulus' and self.metrics['intrinsic_shading'])
        losses = dict(silhouette_readability=tiny/len(self.nodes), coherent_flow=coherence,
                      limited_relief=max(0, span/TAXONOMY['paper_rules']['cloud_relief']-1)**2,
                      avoid_uniform_grid=grid_loss, retain_genus_signature=signature_loss)
        self.metrics['preference_losses'] = losses
        self.metrics['preference_cost'] = sum(losses[k]*weight for k, weight in TAXONOMY['aesthetic_preferences'].items())
        if signature_loss:
            raise ValueError('Cirrocumulus construction introduced intrinsic shaded parts')

    def build(self):
        validate(self.spec)
        if self.spec.upper:
            self.upper()
        else:
            self.base(); self.special(); self.features('structural'); self.varieties(); self.features('additive'); self.accessories()
            if self.spec.halo:
                self.add(ellipse(655, 205, 86, 86)+ellipse(655, 205, 83.5, 83.5), 'halo', .32, 'halo-example')
                self.add(ellipse(655, 205, 17, 17), 'sun-muted', .34, 'sun-through-veil')
        if not self.nodes:
            raise ValueError('Cloud construction produced no paper')
        if len(self.nodes) > TAXONOMY['paper_rules']['max_pieces']:
            raise ValueError('Cloud piece budget exceeded')
        if sum(len(n['path']) for n in self.nodes) > TAXONOMY['paper_rules']['max_commands']:
            raise ValueError('Cloud path budget exceeded')
        self.preference_diagnostics()
        coordinates = [(command[i], command[i+1]) for item in self.nodes for command in item['path'] for i in range(1, len(command), 2)]
        bounds = [min(x for x, y in coordinates), min(y for x, y in coordinates), max(x for x, y in coordinates), max(y for x, y in coordinates)]
        scale = min(1.0, 1000/(bounds[2]-bounds[0]), 450/(bounds[3]-bounds[1]))
        dx = max(-bounds[0]*scale, min(0, 1000-bounds[2]*scale))
        dy = max(5-bounds[1]*scale, min(0, 455-bounds[3]*scale))
        if scale < 1 or dx or dy:
            for item in self.nodes:
                for command in item['path']:
                    for i in range(1, len(command), 2):
                        command[i] = command[i]*scale+dx
                        command[i+1] = command[i+1]*scale+dy
        self.metrics['study_layout'] = dict(source_bounds=bounds, uniform_scale=scale, translate=[dx, dy])
        return self.nodes


def sky_for(spec):
    if spec.upper == 'noctilucent': return 'sky-night'
    if spec.upper == 'nacreous': return 'sky-soft'
    return {'cirrostratus': 'veil', 'altostratus': 'under', 'stratus': 'under', 'nimbostratus': 'storm', 'cumulonimbus': 'sky-storm'}.get(spec.genus, 'sky')


def transform_nodes(nodes, x, y, scale, low, high, prefix):
    result = copy.deepcopy(nodes)
    z0 = min(n['z'] for n in result); z1 = max(n['z'] for n in result)
    for item in result:
        item['id'] = prefix+'-'+item['id']
        item['z'] = low+(high-low)*((item['z']-z0)/(z1-z0) if z1 > z0 else .5)
        for command in item['path']:
            for i in range(1, len(command), 2):
                command[i] = round(x+command[i]*scale, 5)
                command[i+1] = round(y+command[i+1]*scale, 5)
    return result


def document(spec):
    builder = Builder(spec); nodes = builder.build()
    result = dict(version=1, title=spec.label, viewBox=[1200, 720], materials=palette(),
                  conditions=dict(night=0, winter=0, snow=0, rain=0, wind=.2, snowfall=0),
                  nodes=[dict(id='cloud-study-sky', path=tree.box(0, 0, 1200, 720), material=sky_for(spec), z=30)])
    body = dict(id='cloud-assembly', children=transform_nodes(nodes, 50, 100, 1.1, 30.06, 30.45, 'cloud'))
    body['motion'] = dict(kind='drift', amplitude=6, period=70, phase=0)
    result['nodes'].append(body)
    check_budget(result)
    return result, dict(spec=asdict(spec), label=spec.label, traits=builder.traits, metrics=builder.metrics,
                        pieces=len(nodes), commands=sum(len(n['path']) for n in nodes))


def presets():
    groups = {'genera': [], 'species': [], 'varieties': [], 'features': [], 'accessories': [], 'origins': [], 'upper': []}
    for genus, definition in TAXONOMY['genera'].items():
        features = ('incus',) if genus == 'cumulonimbus' else ('praecipitatio',) if genus == 'nimbostratus' else ()
        groups['genera'].append(Cloud(genus, definition['default_species'], features=features, halo=genus == 'cirrostratus'))
        for species in definition['species'] or [None]:
            groups['species'].append(Cloud(genus, species))
    representatives = {'intortus': ('cirrus', 'fibratus'), 'vertebratus': ('cirrus', 'fibratus'),
                       'undulatus': ('altocumulus', 'stratiformis'), 'radiatus': ('cumulus', 'mediocris'),
                       'lacunosus': ('cirrocumulus', 'stratiformis'), 'duplicatus': ('altostratus', None),
                       'translucidus': ('altostratus', None), 'perlucidus': ('altocumulus', 'stratiformis'),
                       'opacus': ('stratocumulus', 'stratiformis')}
    for name, (genus, species) in representatives.items():
        groups['varieties'].append(Cloud(genus, species, varieties=(name,)))
    for name in TAXONOMY['features']:
        if name in ('virga', 'cavum', 'asperitas'):
            genus, species = 'altocumulus', 'stratiformis'
        elif name == 'fluctus': genus, species = 'stratocumulus', 'stratiformis'
        else: genus, species = 'cumulonimbus', 'capillatus'
        features = ('murus', 'cauda') if name == 'cauda' else (name,)
        groups['features'].append(Cloud(genus, species, features=features))
    for name in TAXONOMY['accessories']:
        genus, species = ('nimbostratus', None) if name == 'pannus' else ('cumulonimbus', 'calvus')
        groups['accessories'].append(Cloud(genus, species, accessories=(name,)))
    for origin, genus, species in [('flammagenitus', 'cumulus', 'congestus'), ('homogenitus', 'cumulus', 'mediocris'),
                                   ('homogenitus', 'cirrus', 'fibratus'), ('homomutatus', 'cirrus', 'fibratus'),
                                   ('cataractagenitus', 'stratus', 'fractus'), ('silvagenitus', 'stratus', 'nebulosus')]:
        groups['origins'].append(Cloud(genus, species, origin=origin))
    groups['upper'] = [Cloud('upper', upper=name) for name in TAXONOMY['upper']]
    return groups


def slug(spec):
    parts = [spec.genus, spec.species, *spec.varieties, *spec.features, *spec.accessories, spec.origin, spec.upper, 'halo' if spec.halo else None]
    return '-'.join(p for p in parts if p)


def study_note(spec):
    aliases = {'mamma': 'Mammatus · pendant pouches', 'incus': 'Anvil-shaped ice crown',
               'virga': 'Fallstreaks ending before the ground', 'praecipitatio': 'Precipitation reaching the ground',
               'arcus': 'Attached shelf cloud', 'tuba': 'Condensation funnel',
               'asperitas': 'Irregular turbulent cloud underside', 'fluctus': 'Kelvin–Helmholtz wave crests',
               'cavum': 'Fallstreak hole · actual paper aperture', 'murus': 'Wall-cloud lowering',
               'cauda': 'Tail attached to the wall cloud', 'pileus': 'Small cap over a growing tower',
               'velum': 'Broad accessory veil', 'pannus': 'Ragged scud beneath the main layer',
               'flumen': 'Inflow band attached to the storm', 'lenticularis': 'Lenticular · tapered lens',
               'volutus': 'Detached horizontal roll cloud'}
    for name in [*reversed(spec.accessories), *reversed(spec.features), spec.species]:
        if name in aliases: return aliases[name]
    if spec.origin:
        return 'Source relationship is schematic; origin needs context'
    if spec.upper:
        return 'Upper atmosphere · interpreted in matte paper stocks'
    return {'cirrus': 'High · fine ice filaments', 'cirrocumulus': 'High · small unshaded cloudlets',
            'cirrostratus': 'High · thin veil', 'altocumulus': 'Middle · rounded shaded cells',
            'altostratus': 'Middle · broad layer and diffuse sun', 'nimbostratus': 'Deep layer · precipitation',
            'stratocumulus': 'Low · large shaded cells or rolls', 'stratus': 'Low · uniform layer or ragged scraps',
            'cumulus': 'Vertical · relatively flat base and crisp domes',
            'cumulonimbus': 'Deep convection · smooth or fibrous ice crown'}[spec.genus]


def board(title, samples, columns=3):
    rows = math.ceil(len(samples)/columns)
    cell_w = 1200/columns; cell_h = 250
    height = 100+rows*cell_h
    nodes = [dict(id='atlas-paper', path=tree.box(0, 0, 1200, height), material='paper', z=29)]
    labels = []
    for i, spec in enumerate(samples):
        col, row = i % columns, i // columns
        x = col*cell_w+16; y = 85+row*cell_h
        width = cell_w-32; art_h = 172
        nodes.append(dict(id=f'card-sky-{i}', path=tree.box(x, y, width, art_h), material=sky_for(spec), z=30))
        builder = Builder(spec); shapes = builder.build()
        scale = min((width-12)/1000, (art_h-10)/460)
        dx = x+(width-1000*scale)/2; dy = y+(art_h-460*scale)/2
        nodes += transform_nodes(shapes, dx, dy, scale, 30.025, 30.26, f'card-{i}')
        labels.append(dict(title=spec.label, x=x, y=y+art_h+11, width=width,
                           note=study_note(spec)))
    doc = dict(version=1, title=title, viewBox=[1200, height], materials=palette(),
               conditions=dict(night=0, winter=0, snow=0, rain=0, wind=0, snowfall=0), nodes=nodes)
    check_budget(doc)
    return doc, dict(title=title, width=1200, height=height, labels=labels)


def html_index(output, manifest):
    sections = []
    for category, entries in manifest['groups'].items():
        images = []
        for page in manifest['boards']:
            if page['category'] != category: continue
            images.append(f'<a href="{page["image"]}"><img loading="lazy" src="{page["image"]}" alt="{html.escape(page["title"])}"></a>')
        names = ''.join(f'<li><a href="{e["image"]}">{html.escape(e["label"])}</a> · <a href="{e["document"]}">native data</a></li>' for e in entries)
        sections.append(f'<section id="{category}"><h2>{category.capitalize()}</h2>{"".join(images)}<details><summary>Individual studies</summary><ul>{names}</ul></details></section>')
    nav = ' · '.join(f'<a href="#{name}">{name.capitalize()}</a>' for name in manifest['groups'])
    source_links = ' · '.join(f'<a href="{url}">{name}</a>' for name, url in TAXONOMY['sources'].items())
    html_text = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paper cloud atlas</title>
<style>body{{margin:0;background:#f3ead9;color:#23465b;font:17px/1.6 Georgia,serif}}main{{max-width:1160px;margin:auto;padding:48px 24px}}h1{{font-size:44px;line-height:1.1}}h2{{font-size:30px;margin-top:64px}}a{{color:#365e72}}nav{{position:sticky;top:0;background:#f3ead9;padding:12px 0;border-bottom:1px solid #d7cdbb}}img{{width:100%;height:auto;display:block;margin:24px 0}}p{{max-width:850px}}details{{margin:18px 0}}li{{margin:5px 0}}</style><main><h1>Paper cloud atlas</h1>
<p>Cloud-only studies built from native paper paths. Ten genera, fifteen species, nine varieties, eleven supplementary features and four accessory forms, with special-origin and upper-atmospheric examples. No image-generation backdrops.</p>
<p>These are art-directed interpretations of morphology, not a cloud-identification or forecasting model. Thin atmospheric veils use sky-coordinated opaque paper stocks; physical translucency is not simulated. Origin is provenance and cannot always be inferred from shape alone.</p><nav>{nav}</nav>{''.join(sections)}<h2>References and reproduction</h2><p>WMO International Cloud Atlas: {source_links}.</p><p>Definitions and compatibility rules: <code>apps/paper-weather/art/clouds/taxonomy.json</code>. Generator: <code>tools/cloud_art.py</code>. Every labeled study also has an editable native JSON document beside its PNG. Seeds, traits and construction metrics are recorded in <a href="manifest.json">manifest.json</a>.</p></main></html>'''
    (output/'index.html').write_text(html_text)


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    (output/'individuals').mkdir(exist_ok=True)
    (output/'boards').mkdir(exist_ok=True)
    groups = presets(); manifest = dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), taxonomy_sha256=hashlib.sha256(TAXONOMY_PATH.read_bytes()).hexdigest(),
                                       sources=TAXONOMY['sources'], groups={}, boards=[])
    seen = {}
    for category, samples in groups.items():
        manifest['groups'][category] = []
        for spec in samples:
            name = slug(spec)
            if name not in seen:
                doc, report = document(spec)
                path = Path('individuals')/(name+'.json')
                tree.save(output/path, doc, indent=None)
                seen[name] = dict(**report, document=str(path), image=str(path.with_suffix('.png')))
            manifest['groups'][category].append(seen[name])
        per_page = 6 if category in ('species', 'features') else 10 if category == 'genera' else 9
        for page_index, start in enumerate(range(0, len(samples), per_page)):
            page_samples = samples[start:start+per_page]
            name = f'{category}-{page_index+1:02}'
            title = 'Paper clouds · '+category.capitalize()+(f' {page_index+1}' if len(samples)>per_page else '')
            doc, labels = board(title, page_samples)
            path = Path('boards')/(name+'.json')
            tree.save(output/path, doc, indent=None); tree.save(output/'boards'/(name+'.labels.json'), labels)
            manifest['boards'].append(dict(category=category, title=title, document=str(path),
                                            labels=str(Path('boards')/(name+'.labels.json')), image=str(path.with_suffix('.png'))))
    tree.save(output/'manifest.json', manifest)
    html_index(output, manifest)
    print(f'Generated {len(seen)} unique cloud studies and {len(manifest["boards"])} labeled boards in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=APP.parents[1]/'output/cloud-atlas')
    parser.add_argument('--spec', type=Path, help='Generate one data-specified cloud instead of the atlas')
    args = parser.parse_args()
    if args.spec:
        try:
            if args.spec.stat().st_size > 65536:
                raise ValueError('Cloud specification exceeds 64 KiB')
            spec = from_mapping(json.loads(args.spec.read_text()))
            result, report = document(spec)
        except (ValueError, TypeError, KeyError, OSError) as error:
            parser.error(str(error))
        if args.spec.resolve() == (args.output/(slug(spec)+'.json')).resolve():
            parser.error('Choose a separate output path; the specification will not be overwritten')
        args.output.mkdir(parents=True, exist_ok=True)
        tree.save(args.output/(slug(spec)+'.json'), result, indent=None)
        tree.save(args.output/(slug(spec)+'.report.json'), report)
        print(args.output/(slug(spec)+'.json'))
    else:
        generate(args.output)

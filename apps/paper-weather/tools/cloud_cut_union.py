"""Exact boundary construction for overlapping circular lobes and a capsule base.

Intersections are analytic; exposed arcs are emitted as cubic Beziers. Circle
arcs use the standard tangent cubic approximation, split at <=90 degrees.
"""
import math

TAU=2*math.pi
EPS=1e-9


def arc_point(edge,t):
    x,y,r,_,_=edge
    return (x+r*math.cos(t),y+r*math.sin(t))


def circle_crossings(a,b):
    x,y,r,*_=a;u,v,s,*_=b
    dx=u-x;dy=v-y;d=math.hypot(dx,dy)
    if d<EPS or d>=r+s or d<=abs(r-s):return []
    h=(r*r-s*s+d*d)/(2*d)
    q=math.sqrt(max(0,r*r-h*h))
    return [(x+h*dx/d-sign*q*dy/d,y+h*dy/d+sign*q*dx/d) for sign in (-1,1)]


def line_crossings(line,circle):
    a,b=line;x,y,r,*_=circle
    dx=b[0]-a[0];dy=b[1]-a[1];ox=a[0]-x;oy=a[1]-y
    aa=dx*dx+dy*dy;bb=2*(ox*dx+oy*dy);cc=ox*ox+oy*oy-r*r
    disc=bb*bb-4*aa*cc
    if disc<=1e-14:return []
    return [(a[0]+t*dx,a[1]+t*dy) for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)) if 0<=t<=1]


def boundary(base,lobes):
    """Return one clockwise connected union boundary, or reject bad grammar."""
    half=base['half_length'];cy=base['y'];r=base['radius']
    lines=[((-half,cy-r),(half,cy-r)),((half,cy+r),(-half,cy+r))]
    arcs=[(half,cy,r,-math.pi/2,math.pi/2),(-half,cy,r,math.pi/2,3*math.pi/2)]
    arcs.extend((p['x'],p['y'],p['radius'],0,TAU) for p in lobes)
    def inside(p,owner):
        x,y=p
        if owner!='base':
            nearest=max(-half,min(half,x))
            if (x-nearest)**2+(y-cy)**2<=r*r+1e-12:return True
        return any(i!=owner and (x-l['x'])**2+(y-l['y'])**2<l['radius']**2-EPS for i,l in enumerate(lobes))
    exposed=[]
    for i,arc in enumerate(arcs):
        owner='base' if i<2 else i-2
        cuts=[arc[3],arc[4]]
        intersections=[]
        for other in arcs:intersections.extend(circle_crossings(arc,other))
        for line in lines:intersections.extend(line_crossings(line,arc))
        for x,y in intersections:
            t=math.atan2(y-arc[1],x-arc[0])
            for angle in (t-TAU,t,t+TAU):
                if arc[3]+EPS<angle<arc[4]-EPS:cuts.append(angle)
        cuts=sorted(set(round(t,13) for t in cuts))
        for a,b in zip(cuts,cuts[1:]):
            if b-a>EPS and not inside(arc_point(arc,(a+b)/2),owner):
                exposed.append(('arc',arc,a,b))
    for line in lines:
        a,b=line;dx=b[0]-a[0];dy=b[1]-a[1];length=dx*dx+dy*dy
        cuts=[0,1]
        for circle in arcs:
            for x,y in line_crossings(line,circle):cuts.append(((x-a[0])*dx+(y-a[1])*dy)/length)
        cuts=sorted(set(round(t,13) for t in cuts))
        for lo,hi in zip(cuts,cuts[1:]):
            if hi-lo>EPS and not inside((a[0]+(lo+hi)/2*dx,a[1]+(lo+hi)/2*dy),'base'):
                exposed.append(('line',line,lo,hi))
    def point(segment,t):
        kind,data,lo,hi=segment
        if kind=='arc':return arc_point(data,t)
        a,b=data;return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
    if not exposed:raise ValueError('Empty cloud cut')
    loops=[]
    while exposed:
        loop=[exposed.pop(0)]
        start=point(loop[0],loop[0][2])
        while math.dist(point(loop[-1],loop[-1][3]),start)>1e-7:
            end=point(loop[-1],loop[-1][3])
            matches=[i for i,e in enumerate(exposed) if math.dist(end,point(e,e[2]))<1e-7]
            if len(matches)!=1:raise ValueError('Cloud cut has an open or ambiguous boundary')
            loop.append(exposed.pop(matches[0]))
        # Silhouette construction fills enclosed pockets, not detached islands.
        # Clockwise outer loops have positive area in screen coordinates.
        samples=[point(e,e[2]+(e[3]-e[2])*t/8) for e in loop for t in range(8)]
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(samples,samples[1:]+samples[:1]))/2
        if area>EPS:loops.append(loop)
    if len(loops)!=1:raise ValueError('Cloud grammar produced disconnected masses')
    ordered=loops[0]
    result=[('start',['M',*point(ordered[0],ordered[0][2])])]
    for index,(kind,data,lo,hi) in enumerate(ordered):
        if kind=='line':result.append(('shared-base',['L',*point((kind,data,lo,hi),hi)]));continue
        x,y,r,_,_=data
        steps=math.ceil((hi-lo)/(math.pi/2))
        for step in range(steps):
            a=lo+(hi-lo)*step/steps;b=lo+(hi-lo)*(step+1)/steps
            k=4/3*math.tan((b-a)/4);p=arc_point(data,a);q=arc_point(data,b)
            result.append((f'exposed-lobe-{index}', ['C',p[0]-k*r*math.sin(a),p[1]+k*r*math.cos(a),
                                                   q[0]+k*r*math.sin(b),q[1]-k*r*math.cos(b),*q]))
    result.append(('close',['Z']))
    return result

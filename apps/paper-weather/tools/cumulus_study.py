#!/usr/bin/env python3
"""A deliberately narrow, relational Bezier grammar for one paper cloud family."""
import argparse
import json
import math
import subprocess
from pathlib import Path
import tree_art as tree
from cloud_cut_union import boundary

ROOT = Path(__file__).resolve().parents[3]
DEFINITION = Path(__file__).resolve().parents[1]/'art/clouds/cumulus-grammar.json'


def definition():
    return json.loads(DEFINITION.read_text())


def derive(growth=.48, lean=.15, breadth=.5):
    grammar = definition()
    traits = dict(growth=growth, lean=lean, breadth=breadth)
    for name, value in traits.items():
        lo, hi = grammar['traits'][name]['range']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'{name} must be finite and within [{lo}, {hi}]')
    base = dict(grammar['base'])
    base['half_length'] += grammar['breadth_spread']*(breadth-.5)
    lobes=[]
    events=[]
    for rule in grammar['lobes']:
        if 'parent' not in rule:
            lobe=dict(id=rule['id'],x=rule['x'],y=rule['y'],radius=rule['radius'])
            # Breadth moves shoulders outward; their circular cuts keep their size.
            if rule['id']!='root':lobe['x'] *= 1+grammar['breadth_spread']*(breadth-.5)*2
        else:
            parent=next((l for l in lobes if l['id']==rule['parent']),None)
            if parent is None:continue
            start,end=rule['activation']
            t=max(0,min(1,(growth-start)/(end-start)))
            t=t*t*(3-2*t)
            if t==0:continue
            lobe=dict(id=rule['id'],parent=parent['id'],
                      x=parent['x']+parent['radius']*rule['parent_offset'][0]+lean*rule['lean']*t,
                      y=parent['y']+parent['radius']*rule['parent_offset'][1]-rule['emergence']*t,
                      radius=rule['radius']*t)
            events.append(dict(production=rule['id'],parent=parent['id'],development=t))
        lobes.append(lobe)
    productions=boundary(base,lobes)
    form=dict(base=base,lobes=lobes,events=events,
              height=max(l['radius']-l['y'] for l in lobes)+base['y']+base['radius'])
    return traits, form, productions


def document(growth=.48, lean=.15, breadth=.5, width=560, center=(600,375)):
    grammar=definition(); traits,form,productions=derive(growth,lean,breadth)
    # Both coordinates use the same fixed scale at every growth value.
    # center.y is a permanent base datum, never the changing shape's midpoint.
    x=center[0]; y=center[1]+70
    def cut(dx=0,dy=0):
        path=[]
        for _,command in productions:
            path.append([command[0], *[v*width+(x+dx if i%2==0 else y+dy)
                                      for i,v in enumerate(command[1:])]])
        return path
    stock=lambda color:dict(day=int(color,16),night=int(color,16),winter=int(color,16))
    build=grammar['construction']; dx,dy=build['backing_offset']
    return dict(version=1,title='Cumulus · first paper study',viewBox=[1200,720],
                materials={k:stock(v) for k,v in grammar['stocks'].items()},
                conditions=dict(night=0,winter=0,snow=0,rain=0,wind=0),nodes=[
                    tree.path_node('sky',tree.box(0,0,1200,720),'sky',30),
                    tree.path_node('backing',cut(dx,dy),'backing',build['backing_height']),
                    tree.path_node('face',cut(),'face',build['face_height'])]), dict(traits=traits,form=form,productions=productions)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--growth',type=float,default=.48)
    parser.add_argument('--lean',type=float,default=.15)
    parser.add_argument('--breadth',type=float,default=.5)
    parser.add_argument('--output',type=Path,default=ROOT/'output/cumulus-study')
    parser.add_argument('--review',action='store_true',help='Render this cloud and two controlled growth comparisons natively')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    doc,derivation=document(args.growth,args.lean,args.breadth)
    tree.save(args.output/'cumulus.json',doc)
    tree.save(args.output/'derivation.json',derivation)
    if args.review:
        render=ROOT/'build/paper-cloud-render'
        subprocess.run(['coil','build','tools/cloud_atlas_render.coil','-o',str(render)],cwd=DEFINITION.parents[2],check=True)
        studies=[('cumulus',args.growth,'Study'),('lower',0,'Resting mass'),('rising',1,'Developed crown')]
        for name,growth,label in studies:
            native,trace=document(growth,args.lean,args.breadth)
            tree.save(args.output/(name+'.json'),native)
            tree.save(args.output/(name+'-derivation.json'),trace)
            subprocess.run([str(render),str((args.output/(name+'.json')).resolve()),'-',str((args.output/(name+'.png')).resolve())],check=True)
        buttons=''.join(f'<button type="button" data-image="{name}.png" data-name="{name}" aria-pressed="{str(i==0).lower()}">{label}</button>' for i,(name,_,label) in enumerate(studies))
        page="""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cumulus — a paper grammar</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3eee3;color:#294b5f;font:16px/1.65 Georgia,serif}main{max-width:1100px;margin:55px auto;padding:0 28px}h1{font-weight:normal;font-size:38px;margin:0}p{max-width:720px}nav{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}button{font:inherit;border:1px solid #b6c1bc;background:transparent;color:inherit;padding:8px 19px;cursor:pointer;border-radius:2px}button[aria-pressed=true]{background:#294b5f;color:#f3eee3}button:focus-visible{outline:3px solid #b06e4a;outline-offset:3px}img{display:block;width:100%;height:auto}code{font-size:13px}details{margin-top:25px}a{color:inherit}footer{margin:32px 0;color:#65766f}
</style><main><h1>Cumulus</h1><p>A steady base with new lobes budding, expanding and merging above it. Three stages share the same scale, base and original shoulders.</p><nav aria-label="Growth comparison">BUTTONS</nav><img id="study" src="cumulus.png" width="1200" height="720" alt="Native paper cumulus study"><details><summary>Construction and variation</summary><p>Cloud → fixed base and shoulders → primary bud → flank buds → summit bud → merged boundary → backing + face.</p><p>Each new lobe attaches to a named parent. It expands locally and emerges from that parent; later buds build on earlier ones. Overlapping pieces merge into one continuous cut. Existing lobes retain their radii and positions as growth changes. Lean guides new buds and breadth sets shoulder spacing. There is no vertical scale transform.</p><p>These are native Paper renders. The buttons select rendered comparisons; they do not simulate a live renderer.</p><p><a id="scene-link" href="cumulus.json">Native scene</a> · <a id="trace-link" href="cumulus-derivation.json">Exact derivation</a></p></details><footer>First family study · visual review pending</footer></main><script>
for(const b of document.querySelectorAll('button'))b.addEventListener('click',()=>{document.getElementById('study').src=b.dataset.image;document.getElementById('scene-link').href=b.dataset.name+'.json';document.getElementById('trace-link').href=b.dataset.name+'-derivation.json';document.getElementById('study').alt='Native paper cumulus: '+b.textContent;for(const other of document.querySelectorAll('button'))other.setAttribute('aria-pressed',String(other===b))});
</script></html>""".replace('BUTTONS',buttons)
        (args.output/'index.html').write_text(page)
    print(args.output/'cumulus.json')

if __name__=='__main__':main()

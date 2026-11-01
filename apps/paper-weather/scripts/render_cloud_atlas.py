#!/usr/bin/env python3
"""Render every atlas study through the native Paper executable, never imagegen."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import subprocess
import time
APP=Path(__file__).resolve().parents[1]
ROOT=APP.parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output/cloud-atlas')
    parser.add_argument('--boards-only',action='store_true')
    args=parser.parse_args();output=args.output.resolve()
    binary=ROOT/'build/paper-cloud-render'
    subprocess.run(['coil','build','tools/cloud_atlas_render.coil','-o',str(binary)],cwd=APP,check=True)
    manifest=json.loads((output/'manifest.json').read_text())
    jobs=[dict(document=page['document'],labels=page['labels'],image=page['image'])for page in manifest['boards']]
    if not args.boards_only:
        seen=set()
        for entries in manifest['groups'].values():
            for item in entries:
                if item['document'] not in seen:
                    jobs.append(dict(document=item['document'],labels='-',image=item['image']))
                    seen.add(item['document'])
    def render(job):
        began=time.monotonic()
        labels=str(output/job['labels'])if job['labels']!='-' else '-'
        result=subprocess.run([str(binary),str(output/job['document']),labels,str(output/job['image'])],capture_output=True,text=True)
        if result.returncode:
            raise RuntimeError(f'{job["document"]}: native validation/render failed\n{result.stdout}\n{result.stderr}')
        return dict(**job,seconds=time.monotonic()-began,bytes=(output/job['image']).stat().st_size)
    reports=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i,result in enumerate(pool.map(render,jobs),1):
            reports.append(result)
            if i%10==0 or i==len(jobs):print(f'Rendered {i}/{len(jobs)} native studies',flush=True)
    report_path=output/'render-report.json'
    existing=json.loads(report_path.read_text()) if args.boards_only and report_path.exists() else []
    by_document={entry['document']:entry for entry in existing}
    by_document.update({entry['document']:entry for entry in reports})
    report_path.write_text(json.dumps(list(by_document.values()),indent=2)+'\n')

if __name__=='__main__':main()

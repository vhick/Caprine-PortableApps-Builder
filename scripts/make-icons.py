"""Convert Caprine's real upstream branding into PortableApps icon assets."""
from pathlib import Path
from PIL import Image
import argparse
p=argparse.ArgumentParser()
p.add_argument('--source',required=True)
p.add_argument('--out',required=True)
p.add_argument('--launcher',required=True)
a=p.parse_args()
src=Path(a.source)
if not src.is_file():raise SystemExit(f'Missing authentic Caprine icon: {src}')
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
with Image.open(src) as im:
    im=im.convert('RGBA')
    if min(im.size)<64:raise SystemExit(f'Upstream icon unexpectedly small: {im.size}')
    for size in (16,32,75,128):
        im.resize((size,size),Image.Resampling.LANCZOS).save(out/f'appicon_{size}.png')
    for target in (out/'appicon.ico',Path(a.launcher)):
        target.parent.mkdir(parents=True,exist_ok=True)
        im.save(target,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Created PortableApps icons from',src)

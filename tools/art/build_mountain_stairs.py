"""Cut a south-facing flight into the current cliff, with two legacy map footprints."""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/tiles"


def materials():
    with Image.open(ROOT / "art/source/mountain_meadow_reference.webp") as ref:
        ref = ref.convert("RGB").resize((2048,752),Image.Resampling.LANCZOS)
        rock = np.array(ref.crop((242,536,570,648)).resize((134,48),Image.Resampling.LANCZOS),float)
        turf = np.array(ref.crop((300,424,455,499)).resize((71,30),Image.Resampling.LANCZOS),float)
    with Image.open(ROOT / "art/source/dirt_clearing_reference.webp") as ref:
        earth = np.array(ref.convert("RGB").crop((180,180,420,315)).resize((109,66),Image.Resampling.LANCZOS),float)
    return rock,turf,earth


def flight(rock,turf,earth,turn=0):
    y,x = np.indices((96,96))
    center = np.interp(y,[8,19,31,44,57,71,82,90],
                       [59,59,57,52,43,34,29,27]) + turn*np.sin(np.pi*y/90)
    half = np.interp(y,[8,31,57,82,90],[14,16,19,23,24])
    lateral = x-center
    rough = 0.8*np.sin(x*0.33+0.12*y)+0.45*np.sin(x*0.78-y*0.18)
    # The treads stay almost level across the slope as the flight turns left.
    height = y+0.068*lateral+rough
    lips = np.array([9,16,23,31,40,50,61,73,89])
    step = np.clip(np.searchsorted(lips,height,side="right")-1,0,len(lips)-2)
    start,end = lips[step],lips[step+1]
    front = (height-start)/(end-start)
    side = half-np.abs(lateral)+0.85*np.sin(0.31*y)+0.65*np.cos(0.72*y)
    rx = ((x+step*17)%rock.shape[1]).astype(int)
    grain = rock[(step*6+np.floor(front*4).astype(int))%len(rock),rx]
    soil = earth[(y+step*9)%len(earth),(x+13)%earth.shape[1]]
    tread = 0.31*grain+0.30*soil+0.39*np.array([165,136,91])
    # Carved risers start with a worn sunlit nose, immediately above their shadow.
    nose = np.clip(1-np.abs(front-0.62)/0.14,0,1)[...,None]
    tread += nose*np.array([46,36,19])
    riser = rock[(step*6+np.floor(12*front).astype(int))%len(rock),rx]*0.48+np.array([28,21,14])
    riser *= (0.83+0.17*np.clip((1-front)/0.28,0,1))[...,None]
    color = np.where((front>0.71)[...,None],riser,tread)
    # The last landing is soil with grit and plants, flush with the lower lawn.
    foot = np.clip((height-75)/8,0,1)[...,None]
    color = color*(1-foot)+soil*foot
    buttress = rock[(y*2//3)%len(rock), (x+31)%rock.shape[1]]
    side_mix = np.clip((2.0-side)/3,0,1)[...,None]
    color = color*(1-side_mix)+buttress*side_mix
    foliage = turf[(y+3*np.sin(0.3*x)).astype(int)%len(turf),x%turf.shape[1]]
    # Small irregular pockets of moss in the joints, plus grass at the landings.
    moss = np.clip((4-side)/6+0.55*np.sin(0.26*y+1.4*np.sign(lateral)),0,1)
    moss += 0.33*((front>0.88)&(np.sin(0.28*x+step*2.6)>0.78))
    moss = np.clip(moss,0,1)*(0.76+0.24*np.sin(x*0.8+y*0.3))
    crown = np.clip((13-height)/6,0,1)*np.clip((np.abs(lateral)-5)/8,0,1)
    moss = np.maximum(moss,crown)[...,None]
    color = color*(1-moss)+foliage*moss
    margin = 3+1.2*np.sin(y*0.33)+1.1*np.sin(y*0.59+x*0.31)
    alpha = np.clip(side+margin,0,1)*np.clip(height-7,0,1)
    alpha *= np.clip((88-height-2.5*np.cos(lateral*0.17))/5,0,1)
    rgba = np.zeros((96,96,4),np.uint8)
    rgba[...,:3] = np.rint(np.clip(color,0,255))
    rgba[...,3] = np.rint(255*alpha)
    rgba[rgba[...,3]==0] = 0
    return Image.fromarray(rgba)


def build():
    surfaces = materials()
    main = flight(*surfaces)
    main.save(OUT/"mountain_stairs.png")
    details = Image.new("RGBA",(224,96))
    # Preserve the cell coverage of the two previously placed 3-by-3 stamps.
    details.paste(main,(0,0))
    details.paste(flight(*surfaces,turn=7).resize((93,91)),(99,1))
    with Image.open(OUT/"mini_mountain_source_a.png") as sheet:
        details.paste(sheet.crop((104,104,128,128)),(196,4))
    details.save(OUT/"mini_mountain_details.png")


if __name__ == "__main__":
    build()

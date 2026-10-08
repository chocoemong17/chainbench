"""Shared film drawing: restrained colors, readable numbers and directional motion."""
import functools
import math

from PIL import Image, ImageDraw, ImageFont

SIZE = (1200, 760)
BG, PANEL = '#172127', '#223138'
INK, GRAY, LINE = '#edf0e5', '#b7c8bf', '#3a494e'
BLUE, GREEN, ORANGE = '#8bb9ff', '#68c7bb', '#eea083'


@functools.lru_cache(maxsize=96)
def font(size, ko):
    path = ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc' if ko else
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(path, size)


class Board:
    def text(self, value, x, y, size=24, width=1128, color=INK, center=False):
        ko = any(ord(c)>0x3000 for c in str(value))
        value = str(value)
        for actual in range(size, 17, -1):
            f = font(actual, ko)
            if self.d.textlength(value, font=f) <= width:
                break
        else:
            raise ValueError('Text does not fit: '+value)
        missing = f.getmask(chr(0x10FFFF))
        for c in set(value):
            if ord(c)>127 and not c.isspace():
                g=f.getmask(c)
                if g.size==missing.size and bytes(g)==bytes(missing):
                    raise ValueError('Missing glyph: '+c)
        anchor='mt' if center else 'lt'
        bounds=self.d.textbbox((x,y),value,font=f,anchor=anchor)
        if not (0<=bounds[0]<=bounds[2]<=SIZE[0] and 0<=bounds[1]<=bounds[3]<=SIZE[1]):
            raise ValueError('Text outside frame: '+value)
        self.d.text((x,y),value,font=f,fill=color,anchor=anchor)

    def box(self, bounds, fill=PANEL, outline=LINE):
        self.d.rounded_rectangle(bounds, radius=12, fill=fill, outline=outline, width=2)

    def arrow(self, points, color=BLUE, width=4):
        self.d.line(points, fill=color, width=width, joint='curve')
        (x0,y0),(x,y)=points[-2:]
        angle=math.atan2(y-y0,x-x0)
        self.d.polygon([(x,y),*[(x-11*math.cos(angle+s*.45),y-11*math.sin(angle+s*.45))
                               for s in (-1,1)]],fill=color)
        if color!=LINE:
            self.paths.append((points,color))

    def grid(self, data, x, y, cell=36, max_value=1, numbers=False):
        for r,row in enumerate(data):
            for c,value in enumerate(row):
                strength=min(1,abs(value)/max_value)
                color=ORANGE if value<0 else BLUE
                base=tuple(int(PANEL[k:k+2],16) for k in (1,3,5))
                rgb=tuple(int(color[k:k+2],16) for k in (1,3,5))
                fill=tuple(round(a+strength*(z-a)) for a,z in zip(base,rgb))
                left,top=x+c*cell,y+r*cell
                self.d.rectangle((left,top,left+cell-1,top+cell-1),fill=fill,outline=LINE)
                if numbers and value!=0:
                    label=f'{value:g}' if float(value).is_integer() else f'{value:.1f}'
                    self.text(label,left+cell/2,top+8,22,width=cell-2,
                              color=BG if strength>.5 else INK,center=True)

    def note(self,en,ko):
        self.text(ko if self.ko else en,36,709,19,color=GRAY)

    def banner(self,en,ko,y=600):
        self.box((36,y,1164,y+76))
        self.d.rounded_rectangle((36,y+16,40,y+60),2,fill=GREEN)
        self.text(ko if self.ko else en,58,y+25,24,width=1084)


class Scene(Board):
    last=None

    def __init__(self,lang,title,chapter,total,caption):
        self.ko=lang=='ko'
        self.image=Image.new('RGB',SIZE,BG)
        self.d=ImageDraw.Draw(self.image)
        self.paths=[]
        self.text('CHAINBENCH / PAPERS IN MOTION',36,22,18,color=GRAY)
        self.text(f'{chapter:02d} / {total:02d}',1080,22,18,width=96,color=GRAY)
        self.text(title,36,63,36)
        self.text(caption,36,122,25)
        self.d.line((36,165,1164,165),fill=LINE,width=1)
        width=(1128-5*(total-1))/total
        for i in range(total):
            x=36+i*(width+5)
            self.d.rounded_rectangle((x,746,x+width,749),1,fill=BLUE if i<chapter else LINE)
        Scene.last=self

    def say(self,en,ko,*args,**kwargs):
        self.text(ko if self.ko else en,*args,**kwargs)

    def grid(self,data,x,y,cell=36,max_value=1,numbers=False):
        super().grid(data,x,y,cell,max_value,cell>=30)


def pulses(image,paths,phase):
    d=ImageDraw.Draw(image)
    for points,color in paths:
        lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
        distance=(phase%1)*sum(lengths)
        for a,b,length in zip(points,points[1:],lengths):
            if distance<=length:
                u=distance/length if length else 0
                x,y=a[0]+u*(b[0]-a[0]),a[1]+u*(b[1]-a[1])
                d.ellipse((x-5,y-5,x+5,y+5),fill=color,outline=INK,width=1)
                break
            distance-=length
    return image

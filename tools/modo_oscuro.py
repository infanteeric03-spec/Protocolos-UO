# Regenera el bloque de modo oscuro de index.html a partir de su CSS.
# Uso: python3 tools/modo_oscuro.py index.html tools/modo_oscuro_base.css  (requiere: pip install tinycss2)
import re,sys,colorsys,tinycss2
src=sys.argv[1]
s=open(src,encoding='utf8').read()
m=re.search(r'(<style[^>]*>)(.*?)(</style>)',s,re.S)
css=m.group(2)
# strip previous generated block
css=re.sub(r'/\* ==== MODO OSCURO \(auto\) ==== \*/.*?/\* ==== FIN MODO OSCURO ==== \*/\n?','',css,flags=re.S)
def parse_col(t):
    t=t.strip().lower()
    mm=re.fullmatch(r'#([0-9a-f]{3}|[0-9a-f]{6})',t)
    if mm:
        h=mm.group(1)
        if len(h)==3:h=''.join(c*2 for c in h)
        return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1.0,)
    mm=re.fullmatch(r'rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)',t)
    if mm:
        return (float(mm.group(1))/255,float(mm.group(2))/255,float(mm.group(3))/255,float(mm.group(4)) if mm.group(4) else 1.0)
    if t in('white',):return (1,1,1,1)
    if t in('black',):return (0,0,0,1)
    return None
def lum(c):
    def f(x):return x/12.92 if x<=0.03928 else ((x+0.055)/1.055)**2.4
    r,g,b=c[:3];return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def fmt(r,g,b,a=1.0):
    if a>=0.999:return '#%02x%02x%02x'%tuple(int(round(max(0,min(1,x))*255)) for x in (r,g,b))
    return 'rgba(%d,%d,%d,%.2f)'%(round(r*255),round(g*255),round(b*255),a)
def hls(c):return colorsys.rgb_to_hls(*c[:3])
def bg_dark(c):
    h,l,sat=hls(c);a=c[3]
    if lum(c)<0.45: return None
    if a<0.5 and sat<0.2: return None
    if sat<0.12: 
        if l>0.97 and a>=0.999: return 'var(--paper-raised)'
        nl=0.13+ (1-l)*0.35
        r,g,b=colorsys.hls_to_rgb(h,nl,sat*0.6);return fmt(r,g,b,max(a,0.85) if a<1 else 1)
    nl=0.15+(1-l)*0.25; ns=min(sat,0.5)
    r,g,b=colorsys.hls_to_rgb(h,nl,ns);return fmt(r,g,b,a if a>=0.5 else a*2)
def fg_dark(c):
    h,l,sat=hls(c)
    if lum(c)>0.18: return None
    if sat<0.25: return 'var(--ink)'
    nl=0.74; r,g,b=colorsys.hls_to_rgb(h,nl,max(min(sat,0.75),0.45));return fmt(r,g,b,c[3])
def border_dark(c):
    h,l,sat=hls(c)
    if lum(c)<0.45: return None
    if sat<0.15: return 'var(--line)'
    r,g,b=colorsys.hls_to_rgb(h,0.32,min(sat,0.4));return fmt(r,g,b,c[3])
COLRE=re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)|\bwhite\b')
def conv_value(prop,val):
    p=prop.lower();v=val
    out=v
    if p in('background','background-color','background-image'):
        out=out.replace('var(--ink)','#0f1c29').replace('var(--teal-dark)','#2f7a78')
        for k,v in {'var(--low)':'#3f8f5f','var(--high)':'#b7472a','var(--mid)':'#a8741f','var(--vhigh)':'#6a4c93'}.items(): out=out.replace(k,v)
        out=COLRE.sub(lambda mm:(bg_dark(parse_col(mm.group(0))) or mm.group(0)) if parse_col(mm.group(0)) else mm.group(0),out)
    elif p in('color','fill','stroke','-webkit-text-fill-color','text-decoration-color','caret-color'):
        out=out.replace('var(--paper-raised)','#ffffff').replace('var(--paper)','#f7f5f0')
        out=COLRE.sub(lambda mm:(fg_dark(parse_col(mm.group(0))) or mm.group(0)) if parse_col(mm.group(0)) else mm.group(0),out)
    elif p.startswith('border') or p.startswith('outline'):
        out=out.replace('var(--ink)','#0f1c29')
        out=COLRE.sub(lambda mm:(border_dark(parse_col(mm.group(0))) or mm.group(0)) if parse_col(mm.group(0)) else mm.group(0),out)
    return out if out!=v else None
SKIP=re.compile(r'\.tour-|\.gl-|\.risk-gradient-bar|@media print')
def walk(rules,ctx):
    res=[]
    for r in rules:
        if r.type=='qualified-rule':
            sel=tinycss2.serialize(r.prelude).strip()
            if SKIP.search(sel):continue
            decls=tinycss2.parse_declaration_list(r.content,skip_whitespace=True,skip_comments=True)
            outs=[]
            for d in decls:
                if d.type!='declaration':continue
                val=tinycss2.serialize(d.value).strip()
                nv=conv_value(d.lower_name,val)
                if nv:outs.append('%s:%s%s'%(d.lower_name,nv,' !important' if d.important else ''))
            if outs:res.append((ctx,sel+'{'+';'.join(outs)+';}'))
        elif r.type=='at-rule' and r.lower_at_keyword=='media':
            q=tinycss2.serialize(r.prelude).strip()
            if 'print' in q:continue
            res+=walk(tinycss2.parse_rule_list(r.content,skip_whitespace=True,skip_comments=True),ctx+[q])
    return res
rules=tinycss2.parse_stylesheet(css,skip_whitespace=True,skip_comments=True)
out=walk(rules,[])
blocks=[]
for ctx,rule in out:
    q='screen and (prefers-color-scheme: dark)'+''.join(' and '+c for c in ctx)
    blocks.append('@media %s{%s}'%(q,rule))
manual=open(sys.argv[2],encoding='utf8').read()
gen='/* ==== MODO OSCURO (auto) ==== */\n'+manual+'\n'+'\n'.join(blocks)+'\n/* ==== FIN MODO OSCURO ==== */\n'
css=css.rstrip()+'\n'+gen
s=s[:m.start(2)]+css+s[m.end(2):]
open(src,'w',encoding='utf8').write(s)
print(len(blocks),'reglas generadas')

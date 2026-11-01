"""Comprueba que las cifras con unidades de la web (dosis, umbrales, tiempos)
aparecen en el texto del PDF original de cada protocolo.
Uso: python3 tests/cifras.py   (requiere playwright y pdftotext)
"""
import re,subprocess,json,unicodedata,pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
from playwright.sync_api import sync_playwright
PDF={'torax':'dolor-toracico','fa':'fibrilacion-auricular','ic':'insuficiencia-cardiaca','epoc':'epoc','asma':'asma','neumonia':'neumonia','hematuria':'hematuria','pielonefritis':'pielonefritis','gea':'gastroenteritis','hda':'hemorragia-digestiva-alta','celulitis':'celulitis','absceso':'absceso-periamigdalino','policontusionado':'policontusionado','suboclusion':'suboclusion','intox':'intoxicaciones'}
def norm(t):
    t=unicodedata.normalize('NFKC',t)
    t=t.replace('–','-').replace('—','-').replace('−','-').replace(',', '.').replace('≥','>=').replace('≤','<=')
    return re.sub(r'\s+','',t).lower()
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page()
    pg.goto((ROOT/'index.html').as_uri())
    texts=pg.evaluate("""()=>{const o={};document.querySelectorAll('section.section[data-protocol]').forEach(s=>{if(s.id.startsWith('sec-pdf'))return;const k=s.dataset.protocol;s.style.display='block';o[k]=(o[k]||'')+'\\n'+s.innerText;s.style.display='';});return o}""")
rep={}
for k,f in PDF.items():
    pdft=subprocess.run(['pdftotext','-layout',str(ROOT/'pdf'/(f+'.pdf')),'-'],capture_output=True,text=True).stdout
    np_=norm(pdft)
    web=texts.get(k,'')
    miss=[]
    for line in web.split('\n'):
        for m in re.finditer(r'(?:[<>≥≤]\s*)?\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?\s*(?:%|mmHg|lpm|rpm|mg/kg|mEq/kg|mg/dL|mg/dl|mmol/L|ng/L|g/dL|g/dl|mg|g|ml/kg|mL/kg|ml|mL|h|horas|min|días|años|°C|ºC|ms|kg|L/min|mcg|UI)\b',line):
            tok=m.group(0)
            nt=norm(tok)
            core=re.sub(r'[<>=]','',nt)
            if core in np_ or nt in np_: continue
            # try number alone with unit variations
            num=re.match(r'[\d.\-]+',core).group(0)
            miss.append((tok.strip(),line.strip()[:140]))
    rep[k]=miss
for k,v in rep.items():
    for t,l in v: print(f'{k:<15} {t:<14} {l}')
print(sum(len(v) for v in rep.values()),'cifra(s) de la web no encontradas como texto en el PDF (revisar; pueden venir de imágenes del PDF)')

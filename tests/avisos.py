"""Prueba automática de los avisos de color de todos los protocolos.

Uso:  python3 tests/avisos.py [ruta/a/index.html]
Requiere: pip install playwright (con Chromium disponible).

Para cada aviso (banner) de cada protocolo simula tres situaciones:
  0) nada marcado                   -> espera aviso neutro
  1) marcados todos los criterios de las listas "de inclusión/alta" -> espera verde
  2) además, un criterio de una lista "de exclusión/ingreso"        -> espera rojo
Las listas se clasifican por el color de su etiqueta (verde = inclusión, rojo = exclusión).
Los avisos de calculadoras (CHA2DS2-VA, HAS-BLED, DECAF, PaFi, EDACS) se omiten.
Sale con código 1 si algún aviso no se comporta como se espera.
"""
import sys, pathlib
from playwright.sync_api import sync_playwright

html = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent.parent / 'index.html').resolve()
SKIP = {'chadsva-interpret', 'hasbled-interpret', 'decaf-interpret', 'pafiCalcResult', 'adp-status'}

JS_SCAN = r"""
() => {
  const out = [];
  document.querySelectorAll('section.section[data-protocol]').forEach(sec => {
    sec.querySelectorAll('.status-banner').forEach((b, bi) => {
      if (b.id && %s.includes(b.id)) return;
      if (!b.classList.contains('status-neutral')) return;            // avisos fijos
      const scope = b.classList.contains('status-banner-criteria') ? sec : (b.closest('.card') || sec);
      const gi = (b.dataset.inc || b.dataset.dInc || '').split(/[ ,]+/).filter(Boolean), ge = (b.dataset.exc || b.dataset.dExc || '').split(/[ ,]+/).filter(Boolean);
      let lists = [...scope.querySelectorAll('ul.checklist')];
      if (gi.length || ge.length) lists = [...sec.querySelectorAll('ul.checklist')].filter(l => gi.includes(l.dataset.group) || ge.includes(l.dataset.group));
      if (!lists.length) return;
      const kinds = lists.map(l => {
        if (gi.includes(l.dataset.group)) return 'inc';
        if (ge.includes(l.dataset.group)) return 'exc';
        let p = l.previousElementSibling;
        while (p && (!p.matches('.group-title,ul.checklist,strong,h4') || p.matches('.group-title.sub-gt'))) p = p.previousElementSibling;
        if (p && p.matches('strong,h4')) return 'inc';
        if (!p || !p.matches('.group-title')) { const c = l.closest('.card'); p = c && c.querySelector('.group-title'); }
        if (!p) return 'inc';
        return (p.classList.contains('exclude') || p.classList.contains('warn')) ? 'exc' : 'inc';
      });
      out.push({proto: sec.dataset.protocol, sec: sec.id, bi, id: b.id || '', kinds});
    });
  });
  return out;
}
""" % repr(sorted(SKIP))

def run():
    fails = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1200, 'height': 900})
        pg.add_init_script("try{localStorage.setItem('uoGuideSeen','1')}catch(e){}")
        pg.goto(html.as_uri()); pg.wait_for_timeout(400)
        items = pg.evaluate(JS_SCAN)
        for it in items:
            pg.evaluate(f"enterApp('{it['proto']}')"); pg.wait_for_timeout(50)
            pg.evaluate("s=>{const b=document.querySelector('button[data-protocol][data-section=\"'+s.replace(/^sec-/,'')+'\"]'); if(b) b.click();}", it['sec'])
            pg.wait_for_timeout(80)
            res = pg.evaluate(r"""
            (it) => {
              const sec = document.getElementById(it.sec);
              const b = sec.querySelectorAll('.status-banner')[it.bi];
              const scope = b.classList.contains('status-banner-criteria') ? sec : (b.closest('.card') || sec);
              const gi = (b.dataset.inc || b.dataset.dInc || '').split(/[ ,]+/).filter(Boolean), ge = (b.dataset.exc || b.dataset.dExc || '').split(/[ ,]+/).filter(Boolean);
              let lists = [...scope.querySelectorAll('ul.checklist')];
              if (gi.length || ge.length) lists = [...sec.querySelectorAll('ul.checklist')].filter(l => gi.includes(l.dataset.group) || ge.includes(l.dataset.group));
              const set = (cb, v) => { if (cb.checked !== v) cb.click(); };
              const cls = () => (b.className.match(/status-(neutral|low|mid|high|partial)/) || [,'?'])[1];
              lists.forEach(l => l.querySelectorAll('input[type=checkbox]').forEach(c => set(c, false)));
              const r0 = cls();
              const inc = lists.filter((l,i) => it.kinds[i] === 'inc'), exc = lists.filter((l,i) => it.kinds[i] === 'exc');
              inc.forEach(l => l.querySelectorAll('input[type=checkbox]').forEach(c => set(c, true)));
              const r1 = inc.length ? cls() : '-';
              let r2 = '-';
              if (exc.length) { set(exc[0].querySelector('input[type=checkbox]'), true); r2 = cls(); }
              lists.forEach(l => l.querySelectorAll('input[type=checkbox]').forEach(c => set(c, false)));
              return {r0, r1, r2, text: b.textContent.trim().slice(0, 70)};
            }""", it)
            ok = res['r0'] == 'neutral' and res['r1'] in ('low', '-', 'mid') and res['r2'] in ('high', '-')
            if res['r1'] == 'mid' and res['r2'] == '-': ok = True
            line = f"{'OK ' if ok else 'REV'} {it['proto']:<14} {it['sec']:<30} {it['id']:<26} vacío={res['r0']:<7} inclusión={res['r1']:<7} +exclusión={res['r2']:<7}"
            print(line)
            if not ok: fails.append(line)
        b.close()
    print(f"\n{len(fails)} aviso(s) para revisar")
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(run())

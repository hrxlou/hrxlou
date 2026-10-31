"""Generate the profile's ASCII artwork deterministically; no image service."""
from pathlib import Path
from math import sin, cos, pi, sqrt
from html import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
COLS, ROWS = 92, 39
CHARS = '.,:;=+*oO#@'

def rotate(p):
    x, y, z = p
    a, b, c = .87, -.27, -.45
    y, z = y*cos(a)-z*sin(a), y*sin(a)+z*cos(a)
    x, z = x*cos(b)+z*sin(b), -x*sin(b)+z*cos(b)
    return x*cos(c)-y*sin(c), x*sin(c)+y*cos(c), z

def surface(u, v):
    return ((1+v*cos(u/2))*cos(u), (1+v*cos(u/2))*sin(u), v*sin(u/2))

depth = [[-999.0]*COLS for _ in range(ROWS)]
pixels = [[None]*COLS for _ in range(ROWS)]
for i in range(1550):
    u = 2*pi*i/1550
    for j in range(140):
        v = -.52 + 1.04*j/139
        p = surface(u,v)
        pu, pv = surface(u+.001,v), surface(u,v+.001)
        du = [pu[k]-p[k] for k in range(3)]
        dv = [pv[k]-p[k] for k in range(3)]
        n = (du[1]*dv[2]-du[2]*dv[1], du[2]*dv[0]-du[0]*dv[2], du[0]*dv[1]-du[1]*dv[0])
        nx, ny, nz = rotate(n)
        norm = sqrt(nx*nx+ny*ny+nz*nz)
        x,y,z = rotate(p)
        scale = 1/(1-z*.13)
        px, py = round(COLS/2+x*27*scale), round(ROWS/2-y*14*scale)
        if 0 <= px < COLS and 0 <= py < ROWS and z > depth[py][px]:
            depth[py][px] = z
            shade = .2 + .8*abs((nx*.2-ny*.55+nz*.81)/norm)
            pixels[py][px] = (CHARS[min(len(CHARS)-1,int(shade*(len(CHARS)-1)))], shade)

letters = {
 'h':['10000','10000','10110','11001','10001','10001','10001'],
 'r':['00000','00000','10110','11001','10000','10000','10000'],
 'x':['00000','00000','10001','01010','00100','01010','10001'],
 'l':['01100','00100','00100','00100','00100','00100','01110'],
 'o':['00000','00000','01110','10001','10001','10001','01110'],
 'u':['00000','00000','10001','10001','10001','10011','01101'],
}

for theme, bg, fg, muted, accent, line in [
    ('dark','#0d1117','#e6edf3','#8b949e','#79c0ff','#30363d'),
    ('light','#ffffff','#1f2328','#656d76','#0969da','#d8dee4'),
]:
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">',
           '<title id="title">hrxlou · Hyun Kim</title>',
           '<desc id="desc">Dot-matrix lettering and a Möbius ribbon drawn entirely with ASCII characters.</desc>',
           f'<rect width="1200" height="360" fill="{bg}"/>']
    svg.append('<g id="identity">')
    for li, ch in enumerate('hrxlou'):
        for row, pattern in enumerate(letters[ch]):
            for col, on in enumerate(pattern):
                if on == '1':
                    cx,cy = 52+li*44+col*6.3, 115+row*6.3
                    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.05" fill="{fg}"/>')
    svg.append(f'<text x="50" y="220" fill="{muted}" font-family="Menlo,Consolas,monospace" font-size="26">Hyun Kim</text>')
    svg.append('</g><g id="artwork">')
    for row in range(ROWS):
        for col in range(COLS):
            entry = pixels[row][col]
            if entry is None:
                continue
            char, shade = entry
            color = accent if shade > .94 else fg if shade > .68 else muted
            x,y = 480+col*7.1, 23+row*8.2
            svg.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Menlo,Consolas,monospace" font-size="11.5">{escape(char)}</text>')
    svg.append(f'</g><path d="M50 339H1150" stroke="{line}"/>')
    svg.append('</svg>')
    rendered = '\n'.join(svg)+'\n'
    (OUT/f'header-ascii-{theme}.svg').write_text(rendered)
    mobile = rendered.replace('width="1200" height="360" viewBox="0 0 1200 360"', 'width="600" height="500" viewBox="0 0 600 500"')
    mobile = mobile.replace('<rect width="1200" height="360"', '<rect width="600" height="500"')
    mobile = mobile.replace('<g id="identity">', '<g id="identity" transform="translate(0 -70)">')
    mobile = mobile.replace('<g id="artwork">', '<g id="artwork" transform="translate(-385 195) scale(.85)">')
    mobile = mobile.replace('M50 339H1150', 'M50 490H550')
    (OUT/f'header-ascii-mobile-{theme}.svg').write_text(mobile)
print('Generated light and dark ASCII headers.')

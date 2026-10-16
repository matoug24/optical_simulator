"""Offline local Optics Workbench browser application."""
import argparse
import json
import secrets
import socket
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from model import CATALOG, default_config, folded_config, analysis_config, spectral_focus_config, checked, simulate
from products import list_products, save_product
from diagnostics import solve_grating, sensitivity, convergence
from waveoptics import compute_field, field_convergence
from pulses import pulse_analysis, pulse_convergence
from materials import list_materials, save_material
from focus import focus_analysis

ROOT=Path(__file__).resolve().parent
TOKEN=secrets.token_urlsafe(24)
LEARNING_EXAMPLES=('complex_dispersion','complex_telescope','complex_3d_alignment')


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=False

    def server_bind(self):
        # Windows otherwise permits two HTTP servers to bind the same address,
        # which can silently serve an older running app instead of this version.
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def reply(self,status,payload,ctype='application/json'):
        data=(json.dumps(payload,allow_nan=False) if ctype=='application/json' else payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',ctype+'; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            boot=json.dumps(dict(token=TOKEN,defaults=checked(default_config()),example=checked(folded_config()),analysis_example=analysis_config(),focus_example=spectral_focus_config(),catalog=CATALOG)).replace('<','\\u003c')
            self.reply(200,(ROOT/'index.html').read_text(encoding='utf-8').replace('/*BOOTSTRAP*/','window.BOOT='+boot+';'),'text/html')
        elif path in ('/visualization.js','/lens_geometry.js','/lens_visuals.js','/pointer_tools.js','/workspace.css','/learning_examples.js','/layout_geometry.js','/layout_tools.js','/workbench.js','/products.js','/spectral.js','/pulseviz.js','/analyses.js','/lens_editor.js','/focusviz.js','/style.css','/product-style.css','/analysis-style.css'):
            self.reply(200,(ROOT/path[1:]).read_text(encoding='utf-8'),'text/javascript' if path.endswith('.js') else 'text/css')
        elif path=='/api/health': self.reply(200,dict(status='ok',app='Optics Workbench'))
        elif path=='/api/products':
            try: self.reply(200,dict(products=list_products()))
            except (ValueError,OSError) as e: self.reply(400,dict(error=str(e)))
        elif path=='/api/materials':
            try: self.reply(200,dict(materials=list_materials()))
            except (ValueError,OSError) as e: self.reply(400,dict(error=str(e)))
        elif path.startswith('/api/examples/') and path.removeprefix('/api/examples/') in LEARNING_EXAMPLES:
            try:
                key=path.removeprefix('/api/examples/')
                config=checked(json.loads((ROOT/'examples'/(key+'.json')).read_text(encoding='utf-8')))
                self.reply(200,dict(config=config))
            except (ValueError,OSError) as e: self.reply(400,dict(error=str(e)))
        else: self.reply(404,dict(error='Not found'))

    def do_POST(self):
        if self.headers.get('X-Optics-Token')!=TOKEN: return self.reply(403,dict(error='Reload the local app to authorize this request.'))
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=200000: raise ValueError('Invalid request size.')
            body=json.loads(self.rfile.read(size))
            if self.path=='/api/simulate':
                start=time.perf_counter(); data=simulate(body['config']); data['elapsed_seconds']=time.perf_counter()-start
            elif self.path=='/api/validate': data=dict(config=checked(body['config']))
            elif self.path=='/api/products/save': data=save_product(body['product'])
            elif self.path=='/api/materials/save': data=save_material(body['material'])
            elif self.path in ('/api/grating','/api/sensitivity','/api/convergence','/api/field','/api/pulse','/api/focus','/api/field-convergence','/api/pulse-convergence'):
                config=body['config']; source=body['source_id']; target=body['target_id']; visit=body.get('visit',1)
                if isinstance(visit,bool) or not isinstance(visit,int) or not 1<=visit<=128: raise ValueError('Visit must be an integer between 1 and 128.')
                if self.path=='/api/focus': data=focus_analysis(config,source,target,visit,body.get('max_distance_mm',200.))
                elif self.path=='/api/grating': data=solve_grating(config,source,target,body['deviation_deg'],visit)
                elif self.path=='/api/sensitivity': data=sensitivity(config,source,target,visit,body.get('element_id'),body.get('tilt_step_mrad',.02),body.get('shift_step_mm',.01))
                elif self.path=='/api/convergence': data=convergence(config,source,target,visit,body.get('tolerance_percent',1.),body.get('levels',3))
                elif self.path=='/api/field': data=compute_field(config,source,target,visit)
                elif self.path=='/api/pulse': data=pulse_analysis(config,source,target,visit)
                elif self.path=='/api/field-convergence': data=field_convergence(config,source,target,visit)
                else: data=pulse_convergence(config,source,target,visit)
            else: return self.reply(404,dict(error='Not found'))
            self.reply(200,data)
        except (ValueError,TypeError,KeyError,AttributeError) as e: self.reply(400,dict(error=str(e)))
        except Exception:
            import traceback
            traceback.print_exc(); self.reply(500,dict(error='Simulation failed. See the application console for details.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--product-library',type=Path,help='Optional alternate local product library file')
    parser.add_argument('--material-library',type=Path,help='Optional alternate local material library file')
    args=parser.parse_args(); server=None
    if args.product_library:
        import products
        products.PRODUCT_FILE=args.product_library.resolve()
    if args.material_library:
        import materials
        materials.MATERIAL_FILE=args.material_library.resolve()
    for port in ([args.port] if args.port else range(8787,8808)):
        try: server=LocalServer(('127.0.0.1',port),Handler); break
        except OSError as e:
            if args.port: raise SystemExit(str(e))
    if server is None: raise SystemExit('No available local port between 8787 and 8807.')
    url=f'http://127.0.0.1:{server.server_address[1]}'
    print(f'Optics Workbench: {url}\nKeep this console open. Ctrl+C stops the app.',flush=True)
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=='__main__': main()

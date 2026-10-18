"""Targeted real-plugin regression for Pedalboard float32 duration rounding.

Requires installed assets. Does not run the full instrument acceptance suite.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import json
import numpy as np
from music.backend import run_backend
from music.resources import catalog


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    instruments=catalog(args.config.resolve())

    def check(case):
        instrument_id,rate,frames=case
        directory=args.output/f'{instrument_id}-{rate}-{frames}'
        events=[{'frame':0,'data':[0x90,72,100]},
                {'frame':rate//4,'data':[0x80,72,0]}]
        audio,details=run_backend(instruments[instrument_id],events,rate,frames,directory)
        assert audio.shape==(2,frames),audio.shape
        assert np.isfinite(audio).all() and np.max(np.abs(audio))>1e-6
        assert details['full_render_attempts']==1
        return dict(instrument=instrument_id,sample_rate=rate,frames=frames,passed=True)

    cases=[(instrument,rate,frames) for instrument in ['surge-init','vsco-flute-sustain']
           for rate,frames in [(44100,22051),(48000,24014)]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(check,cases))
    summary={'status':'passed','checks':results}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
